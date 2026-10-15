"""环境变量配置（DB_URL、JWT_SECRET、UPLOAD_DIR）"""
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录：基于本文件位置解析，保证从任意工作目录启动都能正确定位
# 不再依赖当前工作目录（CWD），换机器/换启动方式都不会找错文件
BACKEND_DIR = Path(__file__).resolve().parent.parent
# 项目根 data/ 目录：本地运行与 Docker 容器共用的统一数据位置（V1.4.18）
DATA_DIR = BACKEND_DIR.parent / "data"


class Settings(BaseSettings):
    # env_file 用绝对路径：从任何目录启动都读取 backend/.env，而不是当前工作目录下的 .env
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # 数据库连接（V1.4.18 起默认 SQLite，统一落在项目根 data/linkoa.db，与 Docker 容器共用一套数据）
    #   - SQLite: 默认 data/linkoa.db；也可用 sqlite:///相对路径或绝对路径覆盖（相对写法自动转成绝对路径）
    #   - MySQL:  mysql+pymysql://root:pwd@localhost:3306/linkoa?charset=utf8mb4
    DB_URL: str = f"sqlite:///{(DATA_DIR / 'linkoa.db').as_posix()}"

    # JWT（密钥长度建议 >= 32 字节，满足 HS256 RFC 7518 推荐值）
    # 生产环境必须通过环境变量 JWT_SECRET 覆盖，启动时若仍为默认值将直接拒绝启动。
    JWT_SECRET: str = "linkoa-dev-secret-0123456789abcdef-change-me"
    JWT_EXPIRE_HOURS: int = 8
    JWT_ALGORITHM: str = "HS256"

    # 内部标记：是否允许使用默认 JWT_SECRET（仅本地开发用）
    # 生产部署必须显式设置环境变量 JWT_SECRET，否则启动失败。
    ALLOW_DEFAULT_JWT_SECRET: bool = False

    # 附件存储根目录（相对 backend/ 目录，main.py / file_service.py 会拼接成绝对路径）
    # V1.4.18：默认 ../data/uploads → 项目根 data/uploads，与 Docker 挂载的 /app/data/uploads 对应同一份数据
    UPLOAD_DIR: str = "../data/uploads"

    # CORS 放行来源，逗号分隔
    CORS_ORIGINS: str = "http://localhost:5173"

    # 登录防暴力破解（V1.4.6）：连续失败达上限即锁定账号，锁定期间拒绝登录
    LOGIN_MAX_FAIL: int = 5          # 连续失败几次后锁定
    LOGIN_LOCK_MINUTES: int = 10     # 锁定多少分钟

    # AI 助手默认配置（V1.4.8）：仅作为 ai_config 表首次初始化的默认值，
    # 运行时以数据库 ai_config 表为准，管理员面板可改，无需重启。
    AI_API_KEY: str = ""                       # DeepSeek 等模型的 API Key
    AI_BASE_URL: str = "https://api.deepseek.com"  # 接口地址（兼容 OpenAI 风格）
    AI_MODEL: str = "deepseek-v4-flash"         # 默认模型名（deepseek-chat/reasoner 已于 2026/07 弃用）

    @model_validator(mode="after")
    def _normalize_sqlite_path(self) -> "Settings":
        """SQLite 相对路径规范化：sqlite:///./../data/linkoa.db → 项目根 data/linkoa.db 的绝对路径。

        原因：相对路径是相对进程启动时的工作目录（CWD）解析的。若有人未先 cd backend
        就以项目根目录启动 uvicorn，会在根目录新建一个空 linkoa.db，导致拷贝到新机器后
        历史数据"凭空消失"。转成绝对路径后，无论从哪个目录启动都读写随项目走的同一份库。
        """
        url = self.DB_URL
        if url.startswith("sqlite:///"):
            path_part = url[len("sqlite:///"):]
            if path_part and path_part != ":memory:" and not Path(path_part).is_absolute():
                self.DB_URL = f"sqlite:///{(BACKEND_DIR / path_part).as_posix()}"
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # 启动安全校验：JWT_SECRET 仍是默认值时打印警告（不阻止本地开发）。
    # 生产部署必须在 backend/.env 配置 JWT_SECRET=<随机 32 字节以上字符串>。
    if s.JWT_SECRET.startswith("linkoa-dev-secret") and not s.ALLOW_DEFAULT_JWT_SECRET:
        import warnings
        warnings.warn(
            "【安全警告】JWT_SECRET 仍是开发默认值，任何人都能伪造管理员 token。"
            "生产环境必须在 backend/.env 中配置 JWT_SECRET=<随机 32 字节以上字符串>。",
            stacklevel=2,
        )
    return s


settings = get_settings()
