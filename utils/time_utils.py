"""Time utilities for Beijing timezone.

提供统一的北京时区时间获取与格式化，避免各模块重复实现。
"""

from datetime import datetime

import pytz

# 北京时区常量
BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def beijing_now() -> datetime:
    """返回当前北京时区的 datetime 对象。"""
    return datetime.now(BEIJING_TZ)


def beijing_strftime(fmt: str) -> str:
    """按给定格式返回北京时区的时间字符串。"""
    return beijing_now().strftime(fmt)

