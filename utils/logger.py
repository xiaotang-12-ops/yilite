# -*- coding: utf-8 -*-
"""
统一的日志输出工具
解决Windows控制台中文显示问题
"""

import sys
import io
from typing import Optional
from collections import deque

# 设置标准输出为UTF-8编码
if sys.platform == 'win32':
    # Windows平台：重定向stdout到UTF-8编码的TextIOWrapper
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ✅ 全局日志缓冲区（用于SSE传输）
# 每个任务一个日志队列，最多保留1000条日志
_log_buffers = {}
_current_task_id = None


def set_current_task(task_id: Optional[str]):
    """设置当前任务ID，用于日志路由"""
    global _current_task_id
    _current_task_id = task_id
    if task_id and task_id not in _log_buffers:
        _log_buffers[task_id] = deque(maxlen=1000)


def get_task_logs(task_id: str, clear: bool = False) -> list:
    """获取任务的日志"""
    if task_id not in _log_buffers:
        return []
    logs = list(_log_buffers[task_id])
    if clear:
        _log_buffers[task_id].clear()
    return logs


def _append_to_buffer(message: str):
    """将日志添加到当前任务的缓冲区"""
    if _current_task_id and _current_task_id in _log_buffers:
        _log_buffers[_current_task_id].append(message)


def safe_print(*args, **kwargs):
    """
    安全的打印函数，自动处理编码问题

    Args:
        *args: 要打印的内容
        **kwargs: print函数的其他参数
    """
    try:
        # 构建消息字符串
        message = ' '.join(str(arg) for arg in args)

        # 打印到控制台
        print(*args, **kwargs)

        # ✅ 同时添加到日志缓冲区
        _append_to_buffer(message)

    except UnicodeEncodeError:
        # 如果还是有编码错误，使用ASCII安全模式
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode('ascii', 'replace').decode('ascii'))
            else:
                safe_args.append(str(arg))
        message = ' '.join(safe_args)
        print(*safe_args, **kwargs)
        _append_to_buffer(message)


def print_section(title: str, char: str = "=", width: int = 80):
    """
    打印章节标题
    
    Args:
        title: 标题文本
        char: 分隔符字符
        width: 总宽度
    """
    safe_print()
    safe_print(char * width)
    safe_print(title)
    safe_print(char * width)


def print_step(step_name: str):
    """
    打印步骤标题
    
    Args:
        step_name: 步骤名称
    """
    safe_print()
    safe_print("=" * 80)
    safe_print(step_name)
    safe_print("=" * 80)


def print_substep(substep_name: str):
    """
    打印子步骤标题
    
    Args:
        substep_name: 子步骤名称
    """
    safe_print()
    safe_print("-" * 80)
    safe_print(substep_name)
    safe_print("-" * 80)


def print_info(message: str, indent: int = 0):
    """
    打印信息
    
    Args:
        message: 信息内容
        indent: 缩进级别
    """
    prefix = "  " * indent
    safe_print(f"{prefix}{message}")


def print_success(message: str, indent: int = 0):
    """
    打印成功信息
    
    Args:
        message: 信息内容
        indent: 缩进级别
    """
    prefix = "  " * indent
    safe_print(f"{prefix}[成功] {message}")


def print_error(message: str, indent: int = 0):
    """
    打印错误信息
    
    Args:
        message: 信息内容
        indent: 缩进级别
    """
    prefix = "  " * indent
    safe_print(f"{prefix}[错误] {message}")


def print_warning(message: str, indent: int = 0):
    """
    打印警告信息
    
    Args:
        message: 信息内容
        indent: 缩进级别
    """
    prefix = "  " * indent
    safe_print(f"{prefix}[警告] {message}")

