"""Time utilities for Beijing timezone.

提供统一的北京时区时间获取与格式化，避免各模块重复实现。
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Optional

import os
import pytz

# 北京时区常量
BEIJING_TZ = pytz.timezone("Asia/Shanghai")

# ✅ 调试输出目录缓存：保证同一次任务运行中所有模块复用同一个 debug_output/<timestamp_task> 目录
# 背景：多个模块/Agent 会在不同时间点写调试文件，如果每次都用当前时间生成目录，会把同一任务拆成多个文件夹。
_DEBUG_OUTPUT_DIR_CACHE: Dict[str, str] = {}
_DEBUG_OUTPUT_DIR_LOCK = Lock()


def beijing_now() -> datetime:
    """返回当前北京时区的 datetime 对象。"""
    return datetime.now(BEIJING_TZ)


def beijing_strftime(fmt: str) -> str:
    """按给定格式返回北京时区的时间字符串。"""
    return beijing_now().strftime(fmt)


def init_debug_output_dir(
    task_name: Optional[str] = None,
    now: Optional[datetime] = None,
    override: bool = True,
) -> str:
    """
    初始化并固定当前任务的调试输出目录（同一次任务运行复用同一目录）。

    Args:
        task_name: 任务名（保持原始中文/英文）；若为空，尝试环境变量 TASK_ID，再退回 'unknown_task'
        now: 可选的时间（便于复用同一时间戳）
        override: True 时覆盖同 task_name 的历史缓存（用于同 task_name 的重新生成场景）

    Returns:
        相对路径字符串
    """
    raw_task = task_name or os.getenv("TASK_ID") or "unknown_task"
    # 避免路径分隔符破坏目录结构，同时保留中文可读性
    safe_task = str(raw_task).replace("/", "_").replace("\\", "_")

    current = now or beijing_now()
    date_part = current.strftime("%Y年%m月%d日")
    time_part = current.strftime("%H时%M分%S秒")
    debug_dir = f"debug_output/{date_part}_{time_part}_{safe_task}"

    with _DEBUG_OUTPUT_DIR_LOCK:
        if not override and safe_task in _DEBUG_OUTPUT_DIR_CACHE:
            return _DEBUG_OUTPUT_DIR_CACHE[safe_task]
        _DEBUG_OUTPUT_DIR_CACHE[safe_task] = debug_dir
        return debug_dir


def build_debug_output_dir(task_name: Optional[str] = None, now: Optional[datetime] = None) -> str:
    """
    生成调试输出目录：debug_output/<yyyy年MM月dd日_HH时mm分ss秒_任务名>

    Args:
        task_name: 任务名（保持原始中文/英文）；若为空，尝试环境变量 TASK_ID，再退回 'unknown_task'
        now: 可选的时间（便于复用同一时间戳）

    Returns:
        相对路径字符串
    """
    raw_task = task_name or os.getenv("TASK_ID") or "unknown_task"
    # 避免路径分隔符破坏目录结构，同时保留中文可读性
    safe_task = str(raw_task).replace("/", "_").replace("\\", "_")

    # ✅ 已初始化则直接复用，避免同任务在不同时间点写出多个目录
    with _DEBUG_OUTPUT_DIR_LOCK:
        cached = _DEBUG_OUTPUT_DIR_CACHE.get(safe_task)
        if cached:
            return cached

        current = now or beijing_now()
        date_part = current.strftime("%Y年%m月%d日")
        time_part = current.strftime("%H时%M分%S秒")
        debug_dir = f"debug_output/{date_part}_{time_part}_{safe_task}"
        _DEBUG_OUTPUT_DIR_CACHE[safe_task] = debug_dir
        return debug_dir

