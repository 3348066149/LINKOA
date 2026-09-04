"""SQLAlchemy 2.0 engine / SessionLocal / Declarative Base"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

if settings.DB_URL.startswith("sqlite"):
    # SQLite：文件数据库，跨平台随项目走；check_same_thread 支持 FastAPI 多线程访问
    # 首次启动前确保数据库所在目录存在（SQLite 不会自动创建父目录，缺目录会报 unable to open database file）
    _db_path = settings.DB_URL[len("sqlite:///"):]
    if _db_path and _db_path != ":memory:":
        Path(_db_path).resolve().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.DB_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    engine = create_engine(
        settings.DB_URL,
        pool_pre_ping=True,      # 自动检测断开的连接
        pool_recycle=3600,       # MySQL wait_timeout 兜底
        echo=False,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """全部 ORM 模型的基类（SQLAlchemy 2.0 Declarative Base 风格）"""
    pass


def prepare_sqlite_indexes() -> None:
    """SQLite 索引名需全库唯一（MySQL 仅表内唯一），给索引名加表名前缀

    须在全部模型 import 之后、create_all 之前调用。
    """
    for tname, table in Base.metadata.tables.items():
        for idx in table.indexes:
            if not idx.name.startswith(f"{tname}_"):
                idx.name = f"{tname}_{idx.name}"


def auto_add_missing_columns() -> None:
    """模型新增列自动补齐（幂等，V1.4.4）。

    背景：Base.metadata.create_all 只会新建表，不会给已有表补列。
    老库（如 V1.4.2 及以前）升级到新代码后，一旦模型加了新列（如
    node_template.icon / project_node.icon），查询即报
    "no such column: xxx" / "Unknown column 'xxx'"（前端表现为服务器内部错误）。

    此函数在启动时逐表比对模型与实际库结构，对缺失的列执行
    ALTER TABLE ... ADD COLUMN，让老库无感升级。限制：
      - 只处理"新增列"（要求可空、或有服务端默认值、或有 Python 侧标量默认值，三者居其一）；
      - 删除列/改类型/改名等复杂迁移仍需手写迁移脚本。
    须在 create_all 之后、业务请求进来之前调用。
    """
    from sqlalchemy import inspect, text

    def _server_default_literal(col) -> str | None:
        """推导可用于 DDL 的字面默认值；无法安全推导时返回 None。

        覆盖三种情况：
          1. 显式 server_default（如 text("0")）；
          2. Python 侧 default 为标量（int/str/bool/float）；
          3. Python 侧 default 为无参可调用对象（如 default=0 被包装成 lambda/函数）。
        """
        if col.server_default is not None:
            arg = col.server_default.arg
            return str(getattr(arg, "text", arg))

        d = col.default
        if d is None:
            return None
        val = d.arg
        if callable(val):
            try:
                val = val(None)  # SQLAlchemy 的 default 可调用对象接收 ExecutionContext
            except TypeError:
                return None
        if isinstance(val, bool):
            return "1" if val else "0"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            return "'" + val.replace("'", "''") + "'"
        return None

    insp = inspect(engine)
    with engine.begin() as conn:
        for tname, table in Base.metadata.tables.items():
            if not insp.has_table(tname):
                continue  # create_all 已新建，无需比对
            db_cols = {c["name"] for c in insp.get_columns(tname)}
            for col in table.columns:
                if col.name in db_cols:
                    continue
                default_literal = _server_default_literal(col)
                if col.nullable is False and default_literal is None:
                    print(f"[migrate] 跳过 {tname}.{col.name}：非空且无可用默认值，需手写迁移")
                    continue
                coltype = col.type.compile(engine.dialect)
                ddl = f"ALTER TABLE {tname} ADD COLUMN {col.name} {coltype}"
                if default_literal is not None:
                    ddl += f" DEFAULT {default_literal}"
                conn.execute(text(ddl))
                print(f"[migrate] 已补列 {tname}.{col.name}")
