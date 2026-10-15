"""密码哈希校验（bcrypt）+ 老明文密码平滑升级。

历史数据里密码是明文（内网约定）。首次登录时若哈希校验失败，回退到明文比对，
成功后自动把明文升级成 bcrypt 哈希。新写密码一律走哈希。
"""
import bcrypt

# bcrypt 有 72 字节密码长度限制，超出截断
_MAX_PWD = 72


def hash_password(plain: str) -> str:
    """生成 bcrypt 哈希（$2b$... 前缀）。"""
    return bcrypt.hashpw(plain[:_MAX_PWD].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, stored: str) -> bool:
    """校验密码。stored 是 bcrypt 哈希（$2b$ 开头）；兼容老明文密码。"""
    if not stored:
        return False
    if stored.startswith(("$2b$", "$2a$", "$2y$")):
        try:
            return bcrypt.checkpw(plain[:_MAX_PWD].encode("utf-8"), stored.encode("utf-8"))
        except ValueError:
            return False
    # 老明文密码：直接比对
    return plain == stored


def is_hashed(stored: str) -> bool:
    """是否已经是 bcrypt 哈希。"""
    return bool(stored) and stored.startswith(("$2b$", "$2a$", "$2y$"))
