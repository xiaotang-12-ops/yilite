#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket管理器 - 实时进度推送
支持并行处理的三个通道：GLB转换、PDF解析、AI分析
"""

import asyncio
import json
from typing import Dict, Set, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储所有活跃的WebSocket连接
        # 格式: {task_id: Set[WebSocket]}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # 存储任务的实时进度数据
        # 格式: {task_id: {stage: data}}
        self.task_progress: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """接受新的WebSocket连接"""
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        
        self.active_connections[task_id].add(websocket)
        
        # 发送当前进度（如果有）
        if task_id in self.task_progress:
            await websocket.send_json({
                "type": "initial_state",
                "data": self.task_progress[task_id],
                "timestamp": datetime.now().isoformat()
            })
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开WebSocket连接"""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            
            # 如果没有连接了，清理
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
    
    async def send_progress(
        self, 
        task_id: str, 
        stage: str, 
        progress: int, 
        message: str,
        data: Dict[str, Any] = None
    ):
        """发送进度更新到所有连接的客户端"""
        
        # 更新存储的进度
        if task_id not in self.task_progress:
            self.task_progress[task_id] = {}
        
        self.task_progress[task_id][stage] = {
            "progress": progress,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 广播给所有连接的客户端
        if task_id in self.active_connections:
            message_data = {
                "type": "progress_update",
                "task_id": task_id,
                "stage": stage,
                "progress": progress,
                "message": message,
                "data": data or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # 并发发送给所有连接
            disconnected = set()
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message_data)
                except Exception:
                    disconnected.add(connection)
            
            # 清理断开的连接
            for conn in disconnected:
                self.disconnect(conn, task_id)
    
    async def send_parallel_progress(
        self,
        task_id: str,
        parallel_data: Dict[str, Any]
    ):
        """发送并行处理的进度更新
        
        Args:
            task_id: 任务ID
            parallel_data: 并行处理数据，格式:
                {
                    "glb": {"progress": 50, "message": "...", "current_file": "..."},
                    "pdf": {"progress": 30, "message": "...", "bom_items": 10},
                    "vision": {"progress": 40, "message": "...", "results": [...]}
                }
        """
        if task_id not in self.task_progress:
            self.task_progress[task_id] = {}
        
        self.task_progress[task_id]["parallel"] = parallel_data
        
        if task_id in self.active_connections:
            message_data = {
                "type": "parallel_progress",
                "task_id": task_id,
                "parallel_data": parallel_data,
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected = set()
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message_data)
                except Exception:
                    disconnected.add(connection)
            
            for conn in disconnected:
                self.disconnect(conn, task_id)
    
    async def send_log(
        self,
        task_id: str,
        message: str,
        level: str = "info"
    ):
        """发送日志消息
        
        Args:
            task_id: 任务ID
            message: 日志消息
            level: 日志级别 (info, success, warning, error)
        """
        if task_id in self.active_connections:
            log_data = {
                "type": "log",
                "task_id": task_id,
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected = set()
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(log_data)
                except Exception:
                    disconnected.add(connection)
            
            for conn in disconnected:
                self.disconnect(conn, task_id)
    
    async def send_completion(
        self,
        task_id: str,
        success: bool,
        result: Dict[str, Any] = None,
        error: str = None
    ):
        """发送任务完成消息"""
        if task_id in self.active_connections:
            completion_data = {
                "type": "completion",
                "task_id": task_id,
                "success": success,
                "result": result,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected = set()
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(completion_data)
                except Exception:
                    disconnected.add(connection)
            
            for conn in disconnected:
                self.disconnect(conn, task_id)
        
        # 清理进度数据
        if task_id in self.task_progress:
            del self.task_progress[task_id]
    
    def get_connection_count(self, task_id: str) -> int:
        """获取指定任务的连接数"""
        return len(self.active_connections.get(task_id, set()))
    
    def cleanup_task(self, task_id: str):
        """清理任务相关的所有数据"""
        if task_id in self.active_connections:
            del self.active_connections[task_id]
        if task_id in self.task_progress:
            del self.task_progress[task_id]


# 全局WebSocket管理器实例
ws_manager = ConnectionManager()


class ProgressReporter:
    """进度报告器 - 用于在处理流程中报告进度"""

    def __init__(self, task_id: str, manager: ConnectionManager, loop=None):
        self.task_id = task_id
        self.manager = manager
        # 保存主事件循环的引用（在创建时传入）
        self._loop = loop or asyncio.get_event_loop()
    
    def report_progress(
        self,
        stage: str,
        progress: int,
        message: str,
        data: Dict[str, Any] = None
    ):
        """报告进度（同步方法，可在处理流程中调用）"""
        try:
            # 使用保存的主事件循环引用
            asyncio.run_coroutine_threadsafe(
                self.manager.send_progress(self.task_id, stage, progress, message, data),
                self._loop
            )
        except Exception as e:
            print(f"[WARNING] 无法发送进度: {message}, 错误: {e}")
    
    def report_parallel(self, parallel_data: Dict[str, Any]):
        """报告并行处理进度"""
        try:
            asyncio.run_coroutine_threadsafe(
                self.manager.send_parallel_progress(self.task_id, parallel_data),
                self._loop
            )
        except Exception as e:
            print(f"[WARNING] 无法发送并行进度, 错误: {e}")
    
    def log(self, message: str, level: str = "info"):
        """记录日志"""
        try:
            asyncio.run_coroutine_threadsafe(
                self.manager.send_log(self.task_id, message, level),
                self._loop
            )
        except Exception as e:
            print(f"[WARNING] 无法发送日志: {message}, 错误: {e}")

