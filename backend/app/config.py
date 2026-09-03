"""环境变量配置（DB_URL、JWT_SECRET、UPLOAD_DIR）"""
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ 目录：基于本文件位置解析，保证从任意工作目录启动都能正确定位
# 不再依赖当前工作目录（CWD），换机器/换启动方式都不会找错文件
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # env_file 用绝对路径：从任何目录启动都读取 backend/.env，而不是当前工作目录下的 .env
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # 数据库连接（V1.4 默认 SQLite，数据库文件随项目走，复制文件夹即可移植）
    #   - SQLite: sqlite:///./linkoa.db 或 sqlite:///绝对路径（相对写法会自动转成 backend/ 下的绝对路径）
    #   - MySQL:  mysql+pymysql://root:pwd@localhost:3306/linkoa?charset=utf8mb4
    DB_URL: str = f"sqlite:///{(BACKEND_DIR / 'linkoa.db').as_posix()}"

    # JWT（密钥长度建议 >= 32 字节，满足 HS256 RFC 7518 推荐值）
    JWT_SECRET: str = "linkoa-dev-secret-0123456789abcdef-change-me"
    JWT_EXPIRE_HOURS: int = 24
    JWT_ALGORITHM: str = "HS256"

    # 附件存储根目录（相对 backend/ 目录，main.py / file_service.py 会拼接成绝对路径）
    UPLOAD_DIR: str = "uploads"

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
        """SQLite 相对路径规范化：sqlite:///./linkoa.db → sqlite:///backend/linkoa.db 的绝对路径。

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
    return Settings()


settings = get_settings()
