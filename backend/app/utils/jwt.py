"""JWT 签发与校验（PyJWT，HS256）"""
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.utils.exceptions import BusinessException


def create_token(user_id: int, token_version: int = 1) -> str:
    """签发 token，payload 携带用户ID、token版本号与过期时间。"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tv": token_version,
        "iat": now,
        "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> tuple[int, int]:
    """校验 token 并返回 (user_id, token_version)；失败统一抛 401。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"]), int(payload.get("tv", 1))
    except jwt.ExpiredSignatureError:
        raise BusinessException(401, "登录已过期，请重新登录")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise BusinessException(401, "未登录或登录状态无效")
