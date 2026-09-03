# -*- coding: utf-8 -*-
"""图片内容校验（V1.4.4）

上传接口的 Content-Type / 扩展名由客户端声明，可伪造；仅凭它放行会把
任意文件（甚至截断损坏的文件）存进 uploads/ 被当作图片展示。
这里按文件头魔数（magic bytes）校验真实内容，覆盖 jpg / png / webp。
"""
from __future__ import annotations

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"


def is_valid_image(head: bytes) -> bool:
    """校验文件头是否为 jpg / png / webp 三种格式之一。

    :param head: 文件前若干字节（建议 >= 16 字节，webp 需要读到第 12 字节）
    """
    if head.startswith(PNG_MAGIC):
        return True
    if head.startswith(JPEG_MAGIC):
        return True
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return True
    return False


def read_image_head(file) -> bytes:
    """读取上传文件头部并回卷，供魔数校验；不改变后续读取行为。"""
    head = file.file.read(16)
    try:
        file.file.seek(0)
    except (OSError, ValueError):  # 某些流不支持 seek，只能继续
        pass
    return head
