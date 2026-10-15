"""北京时间工具：全系统统一用 Asia/Shanghai 落库，避免 SQLite CURRENT_TIMESTAMP 存 UTC"""
from datetime import datetime, timedelta, timezone

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """返回 naive datetime（北京时间），直接写入 DateTime 列。

    保持 naive（不带 tzinfo）是为了与历史数据兼容：老库全是 naive 字符串。
    前端按 'YYYY-MM-DD HH:mm' 切片展示，不做时区转换。
    """
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)
