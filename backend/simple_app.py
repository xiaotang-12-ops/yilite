# -*- coding: utf-8 -*-
"""
简化版后端测试
"""

import os
import sys
import json
import uuid
import traceback
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ✅ 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ✅ 定义output目录的绝对路径（确保无论从哪里启动都能找到正确的目录）
OUTPUT_DIR = project_root / "output"
OUTPUT_DIR.mkdir(exist_ok=True)  # 确保目录存在
OUTPUT_ARCHIVE_DIR = project_root / "output_archive"
OUTPUT_ARCHIVE_DIR.mkdir(exist_ok=True)  # 归档目录，覆盖时用于备份

from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response, JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import asyncio
from fastapi import Query

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 存储管理
from core.storage import ManualStorage
from utils.time_utils import beijing_now, BEIJING_TZ

# 创建FastAPI应用
app = FastAPI(
    title="智能装配说明书生成系统",
    description="基于AI的装配说明书自动生成系统",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 健康检查端点 ============
@app.get("/api/health")
async def health_check():
    """
    健康检查端点
    用于Docker健康检查和负载均衡器探测
    """
    return {
        "status": "healthy",
        "service": "assembly-manual-backend",
        "version": "1.0.0",
        "timestamp": beijing_now().isoformat()
    }

@app.get("/")
async def root():
    """根路径重定向到API文档"""
    return {
        "message": "智能装配说明书生成系统 API",
        "docs": "/api/docs",
        "health": "/api/health"
    }

# 数据模型
class GenerationConfig(BaseModel):
    projectName: str

class GenerationRequest(BaseModel):
    config: GenerationConfig
    pdf_files: List[str]
    model_files: List[str]
    conflict_strategy: Optional[str] = "prompt"  # prompt | overwrite | duplicate

# 版本管理请求模型
class SaveDraftRequest(BaseModel):
    manual_data: Dict[str, Any]

class PublishRequest(BaseModel):
    changelog: str
    manual_data: Optional[Dict[str, Any]] = None

class RollbackRequest(BaseModel):
    changelog: Optional[str] = None


class InsertStepRequest(BaseModel):
    chapter_type: str  # component_assembly | product_assembly
    component_code: Optional[str] = None  # 组件装配时必填
    after_step_id: Optional[str] = None  # 在此步骤后插入，None 表示开头
    new_step: Dict[str, Any]
    edit_version: Optional[int] = None  # 乐观锁版本号


class MoveStepRequest(BaseModel):
    step_id: str
    after_step_id: Optional[str] = None  # 移动到目标步骤之后，None 表示开头
    edit_version: Optional[int] = None  # 乐观锁版本号

# 全局变量
tasks = {}
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)


def _cancel_task_thread(task_id: str) -> str:
    """尝试中断后台线程，标记任务为已取消。"""
    task = tasks.get(task_id)
    if not task:
        return "task_not_found"
    task["cancelled"] = True
    thread = task.get("thread")
    if thread and thread.is_alive():
        try:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_long(thread.ident),
                ctypes.py_object(SystemExit)
            )
            if res > 1:
                # 恢复，避免影响其他线程
                ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), 0)
                return "cancel_failed"
            else:
                return "cancelled"
        except Exception as e:
            print(f"⚠️ 取消任务线程失败: {e}")
            return "cancel_failed"
    return "no_thread"

def _json_safe(obj, seen=None):
    """将对象转换为可JSON序列化的安全结构，避免循环引用/线程对象等问题。"""
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return "[circular]"
    seen.add(obj_id)

    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, dict):
        safe_dict = {}
        for k, v in obj.items():
            if k == "thread":
                continue
            safe_dict[k] = _json_safe(v, seen)
        return safe_dict
    if isinstance(obj, list):
        return [_json_safe(item, seen) for item in obj]
    if isinstance(obj, tuple):
        return [_json_safe(item, seen) for item in obj]
    return str(obj)

def _sanitize_task_for_persist(task: Dict[str, Any]) -> Dict[str, Any]:
    """去除不可序列化字段，避免 task_status.json 写入失败。"""
    safe_task = _json_safe(task or {})
    if isinstance(safe_task, dict):
        safe_task.pop("thread", None)
    return safe_task if isinstance(safe_task, dict) else {}

def _persist_task_status(task_id: str) -> None:
    """将内存任务状态持久化到 task_status.json，便于刷新后恢复/列出失败任务。"""
    task = tasks.get(task_id)
    if not task:
        return

    status_file = OUTPUT_DIR / task_id / "task_status.json"
    status_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(_sanitize_task_for_persist(task), f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ 持久化任务状态失败: {e}")


def _load_task_status_from_file(task_id: str) -> Optional[Dict[str, Any]]:
    """从 task_status.json 读取任务状态，供刷新后恢复或列出失败任务。"""
    status_file = OUTPUT_DIR / task_id / "task_status.json"
    if not status_file.exists():
        return None
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"⚠️ 读取任务状态失败: {e}")
        return None

def _count_manual_steps(manual: Dict[str, Any]) -> int:
    component_steps = 0
    for chapter in manual.get("component_assembly", []) or []:
        steps = chapter.get("steps") or []
        if isinstance(steps, list):
            component_steps += len(steps)
    product = manual.get("product_assembly") or {}
    product_steps = len(product.get("steps") or []) if isinstance(product, dict) else 0
    return component_steps + product_steps

def _validate_manual_json(task_dir: Path) -> Dict[str, Any]:
    """
    校验 assembly_manual.json 和关键中间文件是否存在且可解析。
    
    用于检测镜像重启后任务数据是否损坏，避免用户浪费时间在无法恢复的任务上。
    """
    manual_path = task_dir / "assembly_manual.json"
    if not manual_path.exists():
        return {"exists": False, "valid": False, "error": None}
    
    try:
        with open(manual_path, "r", encoding="utf-8") as f:
            manual = json.load(f)
        if _count_manual_steps(manual) <= 0:
            return {"exists": True, "valid": False, "error": "manual_empty"}
    except Exception as e:
        return {"exists": True, "valid": False, "error": str(e)}
    
    # ✅ 新增：检查关键中间文件（用于恢复任务）
    # 这些文件是断点续跑的关键依赖，损坏会导致恢复失败
    critical_files = [
        "step1_bom.json",           # BOM提取结果
        "step2_bom_matched.json",   # BOM匹配结果
        "step4_assembly_steps.json" # 装配步骤（Agent4输出）
    ]
    
    for filename in critical_files:
        file_path = task_dir / filename
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 基本结构检查：确保不是空对象或空数组
                    if data is None or (isinstance(data, (dict, list)) and len(data) == 0):
                        print(f"⚠️ 中间文件为空: {filename}")
                        return {"exists": True, "valid": False, "error": "resume_corrupt"}
            except Exception as e:
                # 中间文件损坏（JSON解析失败），标记为不可恢复
                print(f"⚠️ 中间文件损坏: {filename}, 错误: {e}")
                return {"exists": True, "valid": False, "error": "resume_corrupt"}
    
    return {"exists": True, "valid": True, "error": None}

def _classify_failure(error_message: Optional[str]) -> Dict[str, Any]:
    """识别失败类型（余额不足 / 权限 / Key缺失 / 其他）。"""
    message = (error_message or "").strip()
    lower = message.lower()

    # 余额不足优先识别（可能也是403）
    if "accountoverdue" in lower or "insufficient_quota" in lower or "余额不足" in message or "quota" in lower:
        return {
            "failure_type": "insufficient_balance",
            "failure_hint": "余额不足，请充值后继续生成。"
        }

    # 权限/白名单/资源限制
    if "accessdenied" in lower or "forbidden" in lower or "403" in lower or "无权限" in message or "白名单" in message or "权限" in message:
        return {
            "failure_type": "access_denied",
            "failure_hint": "无权限/未开通服务，请联系管理员。"
        }

    # Key缺失/无效
    if "api key" in lower or "apikey" in lower or "未设置" in message or "invalid api key" in lower:
        return {
            "failure_type": "missing_key",
            "failure_hint": "未配置或无效的 AI-Key，请联系管理员添加 AI-Key。"
        }

    # 源文件缺失
    if "缺少源文件" in message or "source file" in lower or "missing source" in lower or "no product images" in lower:
        return {
            "failure_type": "missing_source",
            "failure_hint": "源文件缺失，请删除任务后重新上传。"
        }

    # 内容为空/校验失败
    if "validation_failed" in lower or "manual_empty" in lower or "content empty" in lower or "steps empty" in lower:
        return {
            "failure_type": "validation_failed",
            "failure_hint": "生成内容为空，请删除后重试。"
        }

    return {
        "failure_type": "unknown",
        "failure_hint": "文件错误，请删除后重试。"
    }

def _start_pipeline_thread(
    task_id: str,
    task_dir: Path,
    pdf_dir: Path,
    step_dir: Path,
    effective_project_name: str,
    resume: bool = False
):
    """启动流水线后台线程（支持断点续跑）。"""
    import threading

    def run_pipeline():
        ResumeDataError = None
        try:
            # 导入并运行pipeline
            import sys
            import os
            sys.path.append(str(Path(__file__).parent.parent))
            from core.gemini_pipeline import GeminiAssemblyPipeline, ResumeDataError
            from utils.logger import set_current_task  # ✅ 导入日志任务设置函数

            # ✅ 设置当前任务ID，让logger知道日志应该路由到哪个任务
            set_current_task(task_id)

            call_points = _resolve_call_points(None, None)
            active_providers = {cfg.get("provider") for cfg in call_points.values()}

            # 从保存的设置中读取API密钥，如果没有则从环境变量读取
            openrouter_key = app_settings.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
            deepseek_key = app_settings.get("deepseek_api_key") or os.getenv("DEEPSEEK_API_KEY")
            doubao_key = app_settings.get("doubao_api_key") or os.getenv("ARK_API_KEY")

            if "openrouter" in active_providers and not openrouter_key:
                raise ValueError("未设置 OpenRouter API Key，请在设置页面配置")
            if "deepseek" in active_providers and not deepseek_key:
                raise ValueError("未设置 DeepSeek API Key，请在设置页面配置")
            if "doubao" in active_providers and not doubao_key:
                raise ValueError("未设置 豆包(ARK) API Key，请在设置页面配置")

            def _progress_callback(step: int, progress: int, message: str = ""):
                task = tasks.get(task_id)
                if not task:
                    return
                task["progress"] = progress
                if message:
                    task["progress_message"] = message
                task["updated_at"] = beijing_now()
                _persist_task_status(task_id)

            pipeline = GeminiAssemblyPipeline(
                api_key=openrouter_key,
                deepseek_api_key=deepseek_key,
                doubao_api_key=doubao_key,
                output_dir=str(task_dir),
                product_name=effective_project_name,  # ✅ 传入产品名称
                call_point_settings=call_points,
                progress_callback=_progress_callback
            )

            # 运行pipeline
            result = pipeline.run(
                pdf_dir=str(pdf_dir),
                step_dir=str(step_dir),
                resume=resume
            )

            # 更新任务状态（区分成功/失败）
            if result.get("success"):
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["progress"] = 100
            else:
                tasks[task_id]["status"] = "failed"
                failure_reason = result.get("error") or result.get("message") or ""
                classified = _classify_failure(failure_reason)
                tasks[task_id]["failure_type"] = classified.get("failure_type")
                tasks[task_id]["failure_hint"] = classified.get("failure_hint")
                tasks[task_id]["error"] = failure_reason
            tasks[task_id]["result"] = result
            tasks[task_id]["updated_at"] = beijing_now()
            _persist_task_status(task_id)

        except Exception as e:
            print(f"Pipeline执行错误: {e}")
            # 允许外部取消：SystemExit 归类为 cancelled
            if isinstance(e, SystemExit) or tasks.get(task_id, {}).get("cancelled"):
                tasks[task_id]["status"] = "cancelled"
                tasks[task_id]["error"] = "cancelled"
            else:
                tasks[task_id]["status"] = "failed"
                if ResumeDataError and isinstance(e, ResumeDataError):
                    tasks[task_id]["failure_type"] = "resume_corrupt"
                    tasks[task_id]["failure_hint"] = "旧任务数据损坏，请删除后重试。"
                failure_reason = str(e)
                if not tasks[task_id].get("failure_type"):
                    classified = _classify_failure(failure_reason)
                    tasks[task_id]["failure_type"] = classified.get("failure_type")
                    tasks[task_id]["failure_hint"] = classified.get("failure_hint")
                tasks[task_id]["error"] = failure_reason
            tasks[task_id]["updated_at"] = beijing_now()
            _persist_task_status(task_id)

    # 在后台线程中运行
    thread = threading.Thread(target=run_pipeline, name=f"pipeline-{task_id}")
    tasks[task_id]["thread"] = thread
    thread.start()
    return thread

def get_storage(task_id: str) -> ManualStorage:
    """获取指定任务的存储管理器"""
    return ManualStorage(base_dir=OUTPUT_DIR, task_id=task_id)


def _load_manual_for_edit(storage: ManualStorage, expected_version: Optional[int] = None) -> Dict[str, Any]:
    """
    加载草稿（优先）或已发布版本，并校验乐观锁。
    """
    manual = storage.load_draft() or storage.load_published()
    if manual is None:
        raise HTTPException(status_code=404, detail="装配说明书不存在")

    # 单管理员场景：不阻塞操作，即使版本号不一致也直接返回
    current_version = manual.get("_edit_version", 0)
    manual["_edit_version"] = current_version
    return manual


def _calculate_insert_order(steps: List[Dict[str, Any]], after_step_id: Optional[str]) -> int:
    """计算插入位置的 display_order，采用 1000 步进，支持头插/中插/尾插。"""
    if not steps:
        return 1000

    def _order_val(item: Dict[str, Any], idx: int) -> float:
        return item.get("display_order", (idx + 1) * 1000)

    sorted_steps = sorted(
        enumerate(steps),
        key=lambda pair: _order_val(pair[1], pair[0])
    )

    if after_step_id is None:
        first_order = _order_val(sorted_steps[0][1], sorted_steps[0][0])
        return int(first_order / 2) if first_order > 1 else 500

    for i, (original_idx, step) in enumerate(sorted_steps):
        if step.get("step_id") == after_step_id:
            current_order = _order_val(step, original_idx)
            if i + 1 < len(sorted_steps):
                next_order = _order_val(sorted_steps[i + 1][1], sorted_steps[i + 1][0])
                if current_order == next_order:
                    return int(current_order) + 1
                return int((current_order + next_order) / 2)
            return int(current_order) + 1000

    raise HTTPException(status_code=404, detail="after_step_id 未找到")


def _get_steps_by_chapter(manual: Dict[str, Any], chapter_type: str, component_code: Optional[str] = None):
    """根据章节类型获取步骤列表及所属章节引用。"""
    if chapter_type == "component_assembly":
        for chapter in manual.get("component_assembly", []):
            if chapter.get("component_code") == component_code:
                steps = chapter.setdefault("steps", [])
                return chapter, steps
        raise HTTPException(status_code=404, detail="未找到对应的组件装配章节")

    if chapter_type == "product_assembly":
        product = manual.get("product_assembly")
        if not isinstance(product, dict):
            raise HTTPException(status_code=404, detail="未找到产品装配章节")
        steps = product.setdefault("steps", [])
        return product, steps

    raise HTTPException(status_code=400, detail="chapter_type 无效")


def _find_step_location(manual: Dict[str, Any], step_id: str):
    """查找步骤所在章节与位置。"""
    for chapter in manual.get("component_assembly", []):
        steps = chapter.get("steps", [])
        for idx, step in enumerate(steps):
            if step.get("step_id") == step_id:
                return "component_assembly", chapter, steps, idx

    product = manual.get("product_assembly")
    if isinstance(product, dict):
        steps = product.get("steps", [])
        for idx, step in enumerate(steps):
            if step.get("step_id") == step_id:
                return "product_assembly", product, steps, idx

    raise HTTPException(status_code=404, detail="step_id 未找到")


def _resort_steps(steps: List[Dict[str, Any]]) -> None:
    steps.sort(key=lambda s: s.get("display_order", 0))


def _normalize_time(val: Any) -> Optional[str]:
    """将 datetime/字符串 统一为 ISO 字符串，其他类型返回 None。"""
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, str):
        return val
    return None


def _next_duplicate_task_id(base_task_id: str) -> str:
    """
    生成下一个可用的 _v_n task_id，扫描 output 下已存在的目录。
    例如 base=foo，已有 foo_v_1/foo_v_2，则返回 foo_v_3。
    """
    max_idx = 0
    prefix = f"{base_task_id}_v_"
    if OUTPUT_DIR.exists():
        for child in OUTPUT_DIR.iterdir():
            if not child.is_dir():
                continue
            name = child.name
            if name.startswith(prefix):
                try:
                    num = int(name[len(prefix):])
                    max_idx = max(max_idx, num)
                except ValueError:
                    continue
    return f"{base_task_id}_v_{max_idx + 1}"


def _build_conflict_payload(
    task_id: str,
    task_dir: Path,
    status: Optional[Dict[str, Any]],
    manual_info: Dict[str, Any],
    code: str
) -> Dict[str, Any]:
    """构造冲突响应 payload，便于前端展示与决策。"""
    manual_path = task_dir / "assembly_manual.json"
    manual_mtime = None
    if manual_path.exists():
        manual_mtime = datetime.fromtimestamp(manual_path.stat().st_mtime, tz=BEIJING_TZ).isoformat()

    created_at = None
    updated_at = None
    task_status = status or {}
    if task_status:
        created_at = _normalize_time(task_status.get("created_at"))
        updated_at = _normalize_time(task_status.get("updated_at"))

    manual_exists = bool(manual_info.get("exists"))
    manual_valid = bool(manual_info.get("valid"))
    manual_error = manual_info.get("error")
    is_processing = bool(task_status.get("status") == "processing")
    is_failed = (not manual_valid) and (not is_processing)

    failure_type = task_status.get("failure_type") if isinstance(task_status, dict) else None
    failure_hint = task_status.get("failure_hint") if isinstance(task_status, dict) else None
    failure_reason = task_status.get("error") if isinstance(task_status, dict) else None

    if manual_error:
        if manual_error == "manual_empty":
            failure_type = "validation_failed"
            failure_hint = "生成内容为空，请删除后重试。"
        else:
            failure_type = "manual_corrupt"
            failure_hint = "旧任务数据损坏，请删除后重试。"
        failure_reason = manual_error
    elif failure_reason and not failure_type:
        classified = _classify_failure(failure_reason)
        failure_type = classified.get("failure_type")
        failure_hint = classified.get("failure_hint")

    return {
        "success": False,
        "code": code,
        "message": f"任务 {task_id} 已存在",
        "task_id": task_id,
        "is_processing": is_processing,
        "manual_exists": manual_exists,
        "manual_valid": manual_valid,
        "manual_error": manual_error,
        "is_failed": is_failed,
        "failure_type": failure_type,
        "failure_hint": failure_hint,
        "failure_reason": failure_reason,
        "created_at": created_at,
        "updated_at": updated_at,
        "manual_mtime": manual_mtime,
        "suggested_duplicate_id": _next_duplicate_task_id(task_id)
    }


def _find_running_task() -> Optional[Dict[str, Any]]:
    """查找当前运行中的任务（内存优先，其次检查持久化状态）。"""
    for task in tasks.values():
        if task.get("status") == "processing":
            return task

    if not OUTPUT_DIR.exists():
        return None

    try:
        for task_dir in OUTPUT_DIR.iterdir():
            if not task_dir.is_dir():
                continue
            persisted = _load_task_status_from_file(task_dir.name)
            if persisted and persisted.get("status") == "processing":
                return persisted
    except Exception as e:
        print(f"⚠️  扫描运行中任务失败: {e}")

    return None


def _build_busy_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    """构造全局忙碌提示 payload。"""
    task_id = task.get("task_id") or task.get("taskId") or ""
    config = task.get("config") or {}
    project_name = config.get("projectName") or task.get("project_name") or ""
    created_at = _normalize_time(task.get("created_at"))
    updated_at = _normalize_time(task.get("updated_at"))

    return {
        "success": False,
        "code": "TASK_BUSY",
        "message": "当前已有任务正在运行，请等待完成后再上传/生成。",
        "task_id": task_id,
        "project_name": project_name,
        "status": task.get("status"),
        "is_processing": True,
        "created_at": created_at,
        "updated_at": updated_at
    }


def _archive_task_dir(task_id: str, task_dir: Path, reason: str = "overwrite") -> Path:
    """
    将现有任务目录移动到归档目录，并写入 archive_meta.json。
    返回归档后的目录路径。
    """
    import shutil

    timestamp = beijing_now().strftime("%Y%m%d_%H%M%S")
    archive_dir = OUTPUT_ARCHIVE_DIR / task_id / timestamp
    archive_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(task_dir), str(archive_dir))

    meta = {
        "task_id": task_id,
        "archived_at": beijing_now().isoformat(),
        "reason": reason,
        "archive_dir": str(archive_dir),
        "source_dir": str(task_dir)
    }
    with open(archive_dir / "archive_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return archive_dir

@app.get("/")
async def root():
    return {"message": "智能装配说明书生成系统 API"}

@app.post("/api/upload")
async def upload_files(
    pdf_files: List[UploadFile] = File(default=[]),
    model_files: List[UploadFile] = File(default=[])
):
    """上传文件接口 - 支持PDF和3D模型文件"""

    # ✅ 限制一次只允许 1 个 PDF + 1 个 STEP
    pdf_count = len([f for f in pdf_files if f and f.filename])
    model_count = len([f for f in model_files if f and f.filename])
    if pdf_count != 1 or model_count != 1:
        raise HTTPException(status_code=400, detail="一次仅支持上传 1 个 PDF 和 1 个 STEP 文件")

    running_task = _find_running_task()
    if running_task:
        return JSONResponse(status_code=409, content=_build_busy_payload(running_task))

    # ✅ Bug修复：上传前清空uploads目录，防止旧文件累积
    import shutil
    try:
        if upload_dir.exists():
            # 先删除目录中的所有文件
            for item in upload_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            print(f"🗑️  已清空uploads目录")
    except Exception as e:
        print(f"⚠️  清空uploads目录时出错: {e}")

    upload_dir.mkdir(exist_ok=True)

    uploaded_files = {
        "pdf_files": [],
        "model_files": []
    }

    # 处理PDF文件
    for file in pdf_files:
        if file.filename:
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            uploaded_files["pdf_files"].append({
                "filename": file.filename,
                "size": len(content),
                "path": str(file_path)
            })

    # 处理3D模型文件
    for file in model_files:
        if file.filename:
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            uploaded_files["model_files"].append({
                "filename": file.filename,
                "size": len(content),
                "path": str(file_path)
            })

    return {
        "success": True,
        "message": "文件上传成功",
        "data": uploaded_files
    }

@app.post("/api/generate")
async def generate_manual(request: GenerationRequest):
    """生成装配说明书接口 - 直接调用gemini_pipeline"""
    # ✅ 限制生成时也只允许 1 个 PDF + 1 个 STEP
    if len(request.pdf_files) != 1 or len(request.model_files) != 1:
        raise HTTPException(status_code=400, detail="一次仅支持 1 个 PDF 和 1 个 STEP 文件")

    running_task = _find_running_task()
    if running_task:
        return JSONResponse(status_code=409, content=_build_busy_payload(running_task))

    # ✅ 以 PDF 文件名作为 task_id，并校验 STEP 文件名匹配
    pdf_filename = request.pdf_files[0]
    step_filename = request.model_files[0]

    pdf_suffix = Path(pdf_filename).suffix.lower()
    step_suffix = Path(step_filename).suffix.lower()
    pdf_base = Path(pdf_filename).stem or pdf_filename

    conflict_strategy = (request.conflict_strategy or "prompt").lower()
    if conflict_strategy not in {"prompt", "overwrite", "duplicate"}:
        raise HTTPException(status_code=400, detail="conflict_strategy 只能是 prompt/overwrite/duplicate")

    # 若 STEP 与 PDF 基名不一致，则强制对齐（生成阶段重命名）
    task_id = pdf_base
    task_dir = OUTPUT_DIR / task_id

    # 冲突检测：存在同名任务目录时，按策略处理
    if task_dir.exists():
        manual_info = _validate_manual_json(task_dir)
        manual_exists = bool(manual_info.get("exists"))
        manual_valid = bool(manual_info.get("valid"))
        status = tasks.get(task_id) or _load_task_status_from_file(task_id)
        is_processing = bool(status and status.get("status") == "processing")
        is_failed = (not manual_valid) and (not is_processing)

        conflict_code = "TASK_RUNNING" if is_processing else ("TASK_FAILED" if is_failed else "TASK_EXISTS")
        conflict_payload = _build_conflict_payload(task_id, task_dir, status, manual_info, conflict_code)

        # prompt 模式：直接返回冲突信息，不启动任务
        if conflict_strategy == "prompt":
            return JSONResponse(status_code=409, content=conflict_payload)

        # 运行中禁止覆盖
        if is_processing and conflict_strategy == "overwrite":
            return JSONResponse(status_code=409, content=conflict_payload)

        if conflict_strategy == "overwrite":
            if manual_valid:
                _archive_task_dir(task_id, task_dir, reason="overwrite")
            else:
                # 失败任务不备份，直接删除目录
                import shutil
                shutil.rmtree(task_dir)
            if task_id in tasks:
                _cancel_task_thread(task_id)
                del tasks[task_id]
            status = None
            manual_exists = False
            manual_valid = False
            task_dir = OUTPUT_DIR / task_id  # 归档/删除后路径已被移走

        elif conflict_strategy == "duplicate":
            # 生成新的 task_id/_v_n
            new_task_id = _next_duplicate_task_id(task_id)
            task_id = pdf_base = new_task_id
            task_dir = OUTPUT_DIR / task_id

    # 依据最终 task_id 重新计算目标文件名
    step_target_name = f"{pdf_base}{step_suffix or ''}"
    pdf_target_name = f"{pdf_base}{pdf_suffix or ''}"

    try:
        # 创建任务目录
        task_dir.mkdir(parents=True, exist_ok=True)

        # ✅ Bug修复：优化文件复制逻辑
        # 方案：直接使用uploads目录，避免大文件复制
        # 注意：由于uploads目录在每次上传时会清空，所以这里仍需复制以保留历史任务数据
        import shutil

        pdf_dir = task_dir / "pdf_files"
        step_dir = task_dir / "step_files"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        step_dir.mkdir(parents=True, exist_ok=True)

        # 复制文件（保留历史任务数据）
        src_pdf = upload_dir / pdf_filename
        dst_pdf = pdf_dir / pdf_target_name
        if src_pdf.exists():
            shutil.copy2(src_pdf, dst_pdf)
            print(f"📄 已复制PDF并设置 task_id: {pdf_target_name} -> {task_id}")

        src_step = upload_dir / step_filename
        dst_step = step_dir / step_target_name
        if src_step.exists():
            shutil.copy2(src_step, dst_step)
            if step_filename != step_target_name:
                print(f"🎯 STEP 文件名已对齐 task_id: {step_filename} -> {step_target_name}")
            else:
                print(f"🎯 已复制STEP: {step_filename}")

        # 创建任务记录
        effective_project_name = pdf_base  # 项目名与 task_id 对齐
        tasks[task_id] = {
            "task_id": task_id,
            "status": "processing",
            "progress": 0,
            "config": {"projectName": effective_project_name},
            "pdf_files": [pdf_target_name],
            "model_files": [step_target_name],
            "created_at": beijing_now(),
            "updated_at": beijing_now()
        }
        _persist_task_status(task_id)

        # 直接调用gemini_pipeline（在后台线程中）
        _start_pipeline_thread(
            task_id=task_id,
            task_dir=task_dir,
            pdf_dir=pdf_dir,
            step_dir=step_dir,
            effective_project_name=effective_project_name,
            resume=False
        )

        return {
            "success": True,
            "task_id": task_id,
            "status": "processing",
            "message": "任务已启动"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    """获取任务状态"""
    if task_id not in tasks:
        persisted = _load_task_status_from_file(task_id)
        if persisted:
            status = dict(persisted)
            task_dir = OUTPUT_DIR / task_id
            manual_info = _validate_manual_json(task_dir)
            if status.get("status") == "completed" and not manual_info.get("valid"):
                status["status"] = "failed"
                status["failure_type"] = "validation_failed"
                status["failure_hint"] = "生成内容为空，请删除后重试。"
                status["error"] = manual_info.get("error") or "manual_empty"
            return _sanitize_task_for_persist(status)
        raise HTTPException(status_code=404, detail="任务不存在")

    status = tasks[task_id]
    task_dir = OUTPUT_DIR / task_id
    manual_info = _validate_manual_json(task_dir)
    if status.get("status") == "completed" and not manual_info.get("valid"):
        status["status"] = "failed"
        status["failure_type"] = "validation_failed"
        status["failure_hint"] = "生成内容为空，请删除后重试。"
        status["error"] = manual_info.get("error") or "manual_empty"
        _persist_task_status(task_id)
    return _sanitize_task_for_persist(status)

@app.post("/api/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """停止任务但保留中间结果。"""
    output_dir = OUTPUT_DIR / task_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    cancel_status = _cancel_task_thread(task_id)

    task = tasks.get(task_id) or _load_task_status_from_file(task_id) or {}
    task["task_id"] = task.get("task_id") or task_id
    task["status"] = "cancelled"
    task["failure_type"] = "cancelled"
    task["failure_hint"] = "任务已停止，可继续生成。"
    task["error"] = "cancelled"
    task["updated_at"] = beijing_now()
    tasks[task_id] = task
    _persist_task_status(task_id)

    return {"success": True, "message": "任务已停止，已保留中间结果", "cancel_status": cancel_status}

@app.post("/api/task/{task_id}/resume")
async def resume_task(task_id: str):
    """继续上一次失败/中断的任务（不重新上传）。"""
    running_task = _find_running_task()
    if running_task:
        return JSONResponse(status_code=409, content=_build_busy_payload(running_task))

    task_dir = OUTPUT_DIR / task_id
    if not task_dir.exists():
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    manual_info = _validate_manual_json(task_dir)
    if manual_info.get("valid"):
        payload = _build_conflict_payload(task_id, task_dir, tasks.get(task_id), manual_info, "TASK_COMPLETED")
        return JSONResponse(status_code=409, content=payload)

    status = tasks.get(task_id) or _load_task_status_from_file(task_id)
    is_processing = bool(status and status.get("status") == "processing")
    if is_processing:
        payload = _build_conflict_payload(task_id, task_dir, status, manual_info, "TASK_RUNNING")
        return JSONResponse(status_code=409, content=payload)

    pdf_dir = task_dir / "pdf_files"
    step_dir = task_dir / "step_files"
    if not pdf_dir.exists() or not step_dir.exists():
        raise HTTPException(status_code=400, detail="缺少源文件，请删除失败任务后重新上传")

    pdf_files = [p.name for p in pdf_dir.glob("*.pdf")] + [p.name for p in pdf_dir.glob("*.PDF")]
    model_files = [p.name for p in step_dir.iterdir() if p.is_file()]
    if not pdf_files or not model_files:
        raise HTTPException(status_code=400, detail="缺少源文件，请删除失败任务后重新上传")

    effective_project_name = (status or {}).get("config", {}).get("projectName") or task_id

    # 创建/恢复任务记录
    task = dict(status or {})
    task.pop("thread", None)
    task.update({
        "task_id": task_id,
        "status": "processing",
        "progress": task.get("progress", 0),
        "config": task.get("config") or {"projectName": effective_project_name},
        "pdf_files": task.get("pdf_files") or pdf_files,
        "model_files": task.get("model_files") or model_files,
        "updated_at": beijing_now(),
        "resume": True,
        "failure_type": None,
        "failure_hint": None,
        "error": None
    })
    tasks[task_id] = task
    _persist_task_status(task_id)

    _start_pipeline_thread(
        task_id=task_id,
        task_dir=task_dir,
        pdf_dir=pdf_dir,
        step_dir=step_dir,
        effective_project_name=effective_project_name,
        resume=True
    )

    return {"success": True, "task_id": task_id, "status": "processing", "message": "任务已恢复"}

@app.get("/api/stream/{task_id}")
async def stream_task_logs(task_id: str):
    """使用 Server-Sent Events 流式传输任务日志"""
    async def event_generator():
        """生成 SSE 事件"""
        try:
            # ✅ 导入日志获取函数
            from utils.logger import get_task_logs

            # 发送初始连接消息
            yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id, 'message': '已连接到任务流'})}\n\n"

            last_status = None
            last_log_count = 0

            while True:
                if task_id in tasks:
                    task = tasks[task_id]
                    current_status = task.get("status")

                    # ✅ 获取新的日志并发送
                    logs = get_task_logs(task_id)
                    if len(logs) > last_log_count:
                        new_logs = logs[last_log_count:]
                        for log in new_logs:
                            yield f"data: {json.dumps({'type': 'log', 'task_id': task_id, 'message': log})}\n\n"
                        last_log_count = len(logs)

                    # 发送进度更新
                    yield f"data: {json.dumps({'type': 'progress', 'task_id': task_id, 'progress': task.get('progress', 0), 'status': current_status, 'message': task.get('progress_message', '')})}\n\n"

                    # 如果状态变化，发送状态更新
                    if current_status != last_status:
                        yield f"data: {json.dumps({'type': 'status_change', 'task_id': task_id, 'status': current_status})}\n\n"
                        last_status = current_status

                    # 如果任务完成/失败/取消，发送最终消息并结束
                    if current_status in ["completed", "failed", "cancelled"]:
                        yield f"data: {json.dumps({'type': 'complete', 'task_id': task_id, 'status': current_status, 'result': task.get('result'), 'error': task.get('error'), 'failure_type': task.get('failure_type'), 'failure_hint': task.get('failure_hint')})}\n\n"
                        break

                # 等待0.5秒再检查（更频繁地检查日志）
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            print(f"SSE 连接已取消: {task_id}")
        except Exception as e:
            print(f"SSE 错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.websocket("/ws/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket连接"""
    try:
        await websocket.accept()
        print(f"✅ WebSocket连接已建立: {task_id}")

        # 发送欢迎消息
        await websocket.send_json({
            "type": "log",
            "task_id": task_id,
            "message": "👷 文件管理员AI员工加入工作，他开始分析上传的文件...",
            "level": "info",
            "timestamp": beijing_now().isoformat()
        })

        # 保持连接并监听任务状态变化
        while True:
            try:
                # 检查任务状态
                if task_id in tasks:
                    task = tasks[task_id]

                    # 发送进度更新
                    await websocket.send_json({
                        "type": "progress",
                        "task_id": task_id,
                        "progress": task.get("progress", 0),
                        "status": task.get("status", "processing"),
                        "message": task.get("progress_message", ""),
                        "timestamp": beijing_now().isoformat()
                    })

                    # 如果任务完成或失败，发送最终消息
                    if task["status"] in ["completed", "failed", "cancelled"]:
                        await websocket.send_json({
                            "type": "complete",
                            "task_id": task_id,
                            "status": task["status"],
                            "result": task.get("result"),
                            "error": task.get("error"),
                            "failure_type": task.get("failure_type"),
                            "failure_hint": task.get("failure_hint"),
                            "timestamp": beijing_now().isoformat()
                        })
                        break

                # 等待1秒再检查
                import asyncio
                await asyncio.sleep(1)

            except Exception as e:
                print(f"WebSocket发送消息错误: {e}")
                break

    except WebSocketDisconnect:
        print(f"❌ WebSocket连接断开: {task_id}")
    except Exception as e:
        print(f"❌ WebSocket错误: {e}")

@app.get("/api/manuals")
async def list_manuals(include_failed: bool = Query(False, description="是否包含失败/未完成的任务")):
    """
    获取所有已生成的装配说明书列表
    ✅ 扫描output目录，返回所有包含assembly_manual.json的任务
    """
    try:
        output_base = Path("output")
        if not output_base.exists():
            return {"manuals": [], "total": 0}

        manuals = []

        # 遍历output目录下的所有子目录
        for task_dir in output_base.iterdir():
            if not task_dir.is_dir():
                continue

            manual_path = task_dir / "assembly_manual.json"
            manual_info = _validate_manual_json(task_dir)
            if manual_info.get("valid"):
                try:
                    # 读取说明书元数据
                    with open(manual_path, 'r', encoding='utf-8') as f:
                        manual_data = json.load(f)

                    # 获取文件修改时间（北京时区）
                    mtime = manual_path.stat().st_mtime
                    timestamp = datetime.fromtimestamp(mtime, tz=BEIJING_TZ).isoformat()

                    # 提取关键信息
                    metadata = manual_data.get('metadata', {})
                    product_name = metadata.get('product_name', '未命名产品')

                    # 统计信息
                    assembly_steps = manual_data.get('assembly_steps', [])
                    step_count = len(assembly_steps)

                    manuals.append({
                        'taskId': task_dir.name,
                        'productName': product_name,
                        'timestamp': timestamp,
                        'stepCount': step_count,
                        'status': 'completed'
                    })
                except Exception as e:
                    print(f"⚠️ 读取任务 {task_dir.name} 失败: {e}")
                    continue
            elif include_failed:
                # 失败/未完成的任务，尝试读取持久化状态
                persisted = _load_task_status_from_file(task_dir.name) or {}
                status = persisted.get("status", "failed")
                product_name = (
                    (persisted.get("config") or {}).get("projectName")
                    or persisted.get("task_id")
                    or task_dir.name
                )
                timestamp = persisted.get("updated_at") or datetime.fromtimestamp(
                    task_dir.stat().st_mtime, tz=BEIJING_TZ
                ).isoformat()
                manuals.append({
                    'taskId': task_dir.name,
                    'productName': product_name,
                    'timestamp': timestamp,
                    'stepCount': 0,
                    'status': status if status in ["processing", "failed"] else "failed"
                })

        # 按时间倒序排序
        manuals.sort(key=lambda x: x['timestamp'], reverse=True)

        return {
            "manuals": manuals,
            "total": len(manuals)
        }

    except Exception as e:
        print(f"❌ 获取说明书列表失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取说明书列表失败: {str(e)}")

@app.get("/api/manual/{task_id}/glb/{glb_filename}")
async def get_glb_file(task_id: str, glb_filename: str):
    """
    获取任务的GLB 3D模型文件
    """
    try:
        output_dir = Path("output") / task_id

        # ✅ 尝试多个可能的路径
        possible_paths = [
            output_dir / "glb_files" / glb_filename,  # 新版本：glb_files子目录
            output_dir / glb_filename,                 # 旧版本：直接在任务目录
        ]

        glb_path = None
        for path in possible_paths:
            if path.exists():
                glb_path = path
                break

        if not glb_path:
            raise HTTPException(status_code=404, detail=f"GLB文件不存在: {glb_filename}")

        print(f"✅ 找到GLB文件: {glb_path}")
        return FileResponse(
            path=str(glb_path),
            media_type="model/gltf-binary",
            filename=glb_filename
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取GLB文件失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取GLB文件失败: {str(e)}")

@app.get("/api/manual/{task_id}/glb-inventory")
async def get_glb_inventory(task_id: str):
    """
    获取任务的 step3_glb_inventory.json 文件
    ✅ 用于获取3D零件的实际名称（node_to_geometry 映射）
    """
    try:
        inventory_path = Path("output") / task_id / "step3_glb_inventory.json"

        if not inventory_path.exists():
            raise HTTPException(status_code=404, detail="step3_glb_inventory.json 不存在")

        with open(inventory_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✅ 加载 step3_glb_inventory.json 成功: {task_id}")
        return data

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取 glb-inventory 失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取 glb-inventory 失败: {str(e)}")

@app.get("/api/manual/{task_id}/pdf_images/{image_path:path}")
async def get_pdf_image(task_id: str, image_path: str):
    """
    获取任务的PDF图片文件（统一目录结构）

    ✅ 新版本路径: /api/manual/{task_id}/pdf_images/{pdf_name}/page_001.png
    例如：
    - /api/manual/{task_id}/pdf_images/产品总图/page_001.png
    - /api/manual/{task_id}/pdf_images/组件1/page_001.png
    """
    try:
        output_dir = Path("output") / task_id

        # ✅ Bug修复：统一使用 pdf_images/{pdf_name}/page_xxx.png 结构
        full_image_path = output_dir / "pdf_images" / image_path

        if not full_image_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF图片不存在: {image_path}")

        print(f"✅ 找到PDF图片: {full_image_path}")

        # 提取文件名用于下载
        filename = Path(image_path).name

        return FileResponse(
            path=str(full_image_path),
            media_type="image/png",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取PDF图片失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取PDF图片失败: {str(e)}")

@app.get("/api/manual/{task_id}")
async def get_manual(task_id: str):
    """
    获取生成的装配说明书数据
    ✅ 修改：直接检查文件是否存在，不依赖内存中的任务记录
    这样即使后端重启，只要文件存在就能查看
    """
    try:
        # ✅ 可选：如果任务在内存中，检查状态
        if task_id in tasks:
            task = tasks[task_id]
            if task["status"] == "processing":
                raise HTTPException(status_code=400, detail="任务正在处理中，请稍后再试")
            elif task["status"] == "failed":
                raise HTTPException(status_code=400, detail=f"任务失败: {task.get('error', '未知错误')}")

        manual_info = _validate_manual_json(OUTPUT_DIR / task_id)
        if not manual_info.get("valid"):
            if manual_info.get("error") == "manual_empty":
                raise HTTPException(status_code=400, detail="生成内容为空，请删除后重试")
            raise HTTPException(status_code=400, detail="说明书文件损坏，请删除后重试")

        storage = get_storage(task_id)
        storage.ensure_migration()
        manual_data = storage.load_published()

        # ✅ 替换所有的{task_id}占位符为实际的task_id
        manual_json_str = json.dumps(manual_data, ensure_ascii=False)
        manual_json_str = manual_json_str.replace("{task_id}", task_id)
        manual_data = json.loads(manual_json_str)

        print(f"✅ 成功加载说明书: {task_id}")
        return manual_data

    except FileNotFoundError:
        # ✅ 手册文件不存在，返回友好提示
        raise HTTPException(status_code=404, detail="装配说明书生成失败，请重试")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取说明书失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取说明书失败: {str(e)}")

@app.put("/api/manual/{task_id}")
async def update_manual(task_id: str, manual_data: dict):
    """
    兼容旧接口：直接发布新版本（不经过草稿）
    - 建议新前端使用 /api/manual/{task_id}/save-draft + /publish
    """
    try:
        storage = get_storage(task_id)
        storage.ensure_migration()
        published = storage.publish_draft(
            changelog="旧接口直接发布",
            manual_data=manual_data
        )

        print(f"✅ 成功更新说明书: {task_id}, 版本: {published.get('version')}")
        return {"success": True, "version": published.get("version"), "message": "已发布（兼容旧接口）"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 更新说明书失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@app.delete("/api/manual/{task_id}")
async def delete_manual(task_id: str):
    """
    删除装配说明书（管理员功能）
    - 删除整个任务目录(output/{task_id}/)
    - 包括JSON、PDF图片、3D模型等所有文件
    - 从内存中删除任务记录
    """
    try:
        output_dir = OUTPUT_DIR / task_id

        if not output_dir.exists():
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        # 若任务正在处理，尝试中断后台线程
        cancel_status = _cancel_task_thread(task_id)
        if cancel_status in {"cancelled", "cancel_failed"}:
            print(f"🛑 已请求中断任务 {task_id}，状态: {cancel_status}")

        # 删除整个目录
        import shutil
        shutil.rmtree(output_dir)

        # 从内存中删除任务记录
        if task_id in tasks:
            del tasks[task_id]

        print(f"✅ 成功删除说明书: {task_id}")
        return {"success": True, "message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 删除说明书失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.head("/api/manual/{task_id}/version")
async def get_manual_version(task_id: str):
    """
    快速获取版本号和更新时间（用于前端缓存检查）
    - 返回版本号和lastUpdated，不返回完整数据
    - 用于前端检查数据是否需要更新
    - 前端需同时比较version和lastUpdated来判断缓存有效性
    """
    try:
        storage = get_storage(task_id)
        storage.ensure_migration()
        manual = storage.load_published()
        version = manual.get('version', 'v1')
        last_updated = manual.get('lastUpdated', '')

        # 使用Response返回，在header中包含版本号和更新时间
        return Response(headers={
            "X-Manual-Version": version,
            "X-Manual-LastUpdated": last_updated
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本号失败: {str(e)}")


# ============ 草稿/发布/历史 ============ #
@app.post("/api/manual/{task_id}/save-draft")
async def save_manual_draft(task_id: str, request: SaveDraftRequest):
    """
    保存草稿，不影响已发布版本
    """
    try:
        storage = get_storage(task_id)
        storage.ensure_migration()
        current = storage.load_draft() or storage.load_published() or {}
        current_version = current.get("_edit_version", 0)
        manual_to_save = dict(request.manual_data)
        manual_to_save["_edit_version"] = current_version + 1

        draft = storage.save_draft(manual_to_save)
        return {"success": True, "lastUpdated": draft.get("lastUpdated"), "message": "草稿保存成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 保存草稿失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"保存草稿失败: {str(e)}")


@app.post("/api/manual/{task_id}/publish")
async def publish_manual(task_id: str, request: PublishRequest):
    """
    将草稿发布为新版本，归档历史版本
    """
    try:
        storage = get_storage(task_id)
        storage.ensure_migration()
        published = storage.publish_draft(
            changelog=request.changelog,
            manual_data=request.manual_data
        )
        return {"success": True, "version": published.get("version"), "message": "发布成功"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ 发布失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


@app.get("/api/manual/{task_id}/history")
async def get_manual_history(task_id: str):
    """
    获取版本历史列表
    """
    try:
        storage = get_storage(task_id)
        history = storage.list_history()
        return history
    except Exception as e:
        print(f"❌ 获取历史版本失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取历史版本失败: {str(e)}")


@app.get("/api/manual/{task_id}/draft")
async def get_manual_draft(task_id: str):
    """
    获取草稿内容（如果存在）
    """
    try:
        storage = get_storage(task_id)
        draft = storage.load_draft()
        if draft is None:
            raise HTTPException(status_code=404, detail="草稿不存在")
        return draft
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取草稿失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取草稿失败: {str(e)}")


@app.delete("/api/manual/{task_id}/draft")
async def discard_draft(task_id: str):
    """
    丢弃草稿，删除 draft.json 文件
    """
    try:
        storage = get_storage(task_id)
        draft_path = storage.task_dir / "draft.json"
        if not draft_path.exists():
            raise HTTPException(status_code=404, detail="草稿不存在")
        draft_path.unlink()
        return {"success": True, "message": "草稿已丢弃"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 丢弃草稿失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"丢弃草稿失败: {str(e)}")


@app.get("/api/manual/{task_id}/version/{version}")
async def get_manual_version_detail(task_id: str, version: str):
    """
    获取指定版本内容
    """
    try:
        storage = get_storage(task_id)
        storage.ensure_version_file(version)
        manual = storage.load_version(version)
        return manual
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 获取指定版本失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取指定版本失败: {str(e)}")


@app.post("/api/manual/{task_id}/rollback/{version}")
async def rollback_manual(task_id: str, version: str, request: RollbackRequest):
    """
    回滚到指定版本，并以新版本发布
    """
    try:
        storage = get_storage(task_id)
        storage.ensure_migration()
        published = storage.rollback_to_version(version, request.changelog)
        return {"success": True, "version": published.get("version"), "message": "回滚成功并已发布"}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 回滚失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"回滚失败: {str(e)}")


@app.delete("/api/manual/{task_id}/version/{version}")
async def delete_manual_version(task_id: str, version: str):
    """
    删除指定历史版本（不能删除当前版本）
    - 删除 versions/{version}.json 文件
    - 从 version_history.json 中移除该版本记录
    """
    try:
        storage = get_storage(task_id)
        result = storage.delete_version(version)
        print(f"✅ 成功删除版本: {task_id}/{version}")
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"❌ 删除版本失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除版本失败: {str(e)}")


# ============ 步骤插入 / 删除 / 移动 ============ #
@app.post("/api/manual/{task_id}/steps/insert")
async def insert_step(task_id: str, request: InsertStepRequest):
    """
    在指定步骤之后插入新步骤（不改动旧的 step_id）。
    """
    storage = get_storage(task_id)
    storage.ensure_migration()

    manual = _load_manual_for_edit(storage, request.edit_version)
    current_version = manual.get("_edit_version", 0)

    _, steps = _get_steps_by_chapter(manual, request.chapter_type, request.component_code)
    new_order = _calculate_insert_order(steps, request.after_step_id)
    new_step_id = f"step_{uuid.uuid4().hex[:12]}"

    new_step = dict(request.new_step)
    new_step["step_id"] = new_step_id
    new_step["display_order"] = new_order
    new_step.setdefault("step_number", len(steps) + 1)  # 兼容旧前端显示
    if "step_number" in new_step and "_legacy_step_number" not in new_step:
        new_step["_legacy_step_number"] = new_step["step_number"]

    steps.append(new_step)
    _resort_steps(steps)

    manual["_edit_version"] = current_version + 1
    storage.save_draft(manual)

    return {
        "success": True,
        "step_id": new_step_id,
        "display_order": new_order,
        "edit_version": manual["_edit_version"]
    }


@app.delete("/api/manual/{task_id}/steps/{step_id}")
async def delete_step(task_id: str, step_id: str, edit_version: Optional[int] = None):
    """
    删除指定步骤。
    """
    storage = get_storage(task_id)
    storage.ensure_migration()

    manual = _load_manual_for_edit(storage, edit_version)
    current_version = manual.get("_edit_version", 0)

    chapter_type, _, steps, idx = _find_step_location(manual, step_id)
    removed_step = steps.pop(idx)

    manual["_edit_version"] = current_version + 1
    storage.save_draft(manual)

    # 返回被删除步骤的零件信息，方便前端提示
    affected_parts = removed_step.get("parts_used") or removed_step.get("components") or []

    return {
        "success": True,
        "deleted_step_id": step_id,
        "chapter_type": chapter_type,
        "affected_parts": affected_parts,
        "edit_version": manual["_edit_version"]
    }


@app.post("/api/manual/{task_id}/steps/move")
async def move_step(task_id: str, request: MoveStepRequest):
    """
    通过 step_id 重新定位步骤（调整 display_order）。
    """
    storage = get_storage(task_id)
    storage.ensure_migration()

    manual = _load_manual_for_edit(storage, request.edit_version)
    current_version = manual.get("_edit_version", 0)

    if request.after_step_id == request.step_id:
        raise HTTPException(status_code=400, detail="after_step_id 不能等于 step_id")

    chapter_type, _, steps, idx = _find_step_location(manual, request.step_id)
    moving_step = steps.pop(idx)

    new_order = _calculate_insert_order(steps, request.after_step_id)
    moving_step["display_order"] = new_order

    steps.append(moving_step)
    _resort_steps(steps)

    manual["_edit_version"] = current_version + 1
    storage.save_draft(manual)

    return {
        "success": True,
        "step_id": request.step_id,
        "new_display_order": new_order,
        "chapter_type": chapter_type,
        "edit_version": manual["_edit_version"]
    }

# ============ 设置管理端点 ============
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.5-flash-preview-09-2025"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEFAULT_DOUBAO_MODEL = "doubao-seed-1-8-251228"
DEFAULT_PROVIDER = "openrouter"
DOUBAO_BASE_URL = (
    os.getenv("DOUBAO_BASE_URL")
    or os.getenv("ARK_BASE_URL")
    or "http://111.230.37.43:3000/v1"
)

AI_PROVIDER_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com",
    "doubao": DOUBAO_BASE_URL,
}

AI_CALL_POINT_DEFS = {
    "matching": {
        "label": "匹配",
        "requires_images": False,
        "allowed_providers": ["openrouter", "deepseek", "doubao"]
    },
    "assembly": {
        "label": "组件/产品",
        "requires_images": True,
        "allowed_providers": ["openrouter", "doubao"]
    },
    "welding": {
        "label": "焊接",
        "requires_images": True,
        "allowed_providers": ["openrouter", "doubao"]
    },
    "safety": {
        "label": "安全",
        "requires_images": False,
        "allowed_providers": ["openrouter", "deepseek", "doubao"]
    },
    "bom_vision": {
        "label": "BOM视觉提取",
        "requires_images": True,
        "allowed_providers": ["openrouter", "doubao"]
    }
}

def _default_model_for_provider(provider: str) -> str:
    if provider == "deepseek":
        return DEFAULT_DEEPSEEK_MODEL
    if provider == "doubao":
        return DEFAULT_DOUBAO_MODEL
    return DEFAULT_OPENROUTER_MODEL

def _build_default_call_points() -> Dict[str, Dict[str, str]]:
    return {
        call_point_id: {
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_OPENROUTER_MODEL
        }
        for call_point_id in AI_CALL_POINT_DEFS.keys()
    }

def _mask_key(value: str) -> str:
    if not value:
        return ""
    return value[:10] + "..."

def _resolve_call_points(
    incoming: Optional[Dict[str, "CallPointConfig"]],
    fallback_model: Optional[str] = None
) -> Dict[str, Dict[str, str]]:
    resolved: Dict[str, Dict[str, str]] = {}
    apply_fallback_model = bool(fallback_model) and not incoming
    existing = app_settings.get("call_points", {})

    for call_point_id, definition in AI_CALL_POINT_DEFS.items():
        incoming_point = incoming.get(call_point_id) if incoming else None
        existing_point = existing.get(call_point_id, {})

        provider = (incoming_point.provider if incoming_point else None) or existing_point.get("provider") or DEFAULT_PROVIDER
        if provider not in definition["allowed_providers"]:
            raise ValueError(f"调用点 {call_point_id} 不支持提供方 {provider}")

        model = (incoming_point.model if incoming_point else None) or existing_point.get("model") or ""
        if apply_fallback_model and provider == "openrouter":
            model = fallback_model or model
        if not model:
            model = _default_model_for_provider(provider)

        # 新增：保存独立Key
        custom_key = (incoming_point.custom_key if incoming_point else None) or existing_point.get("custom_key") or ""

        resolved[call_point_id] = {
            "provider": provider,
            "model": model,
            "custom_key": custom_key  # 新增
        }

    return resolved

def _build_call_point_payload() -> Dict[str, Dict[str, Any]]:
    payload: Dict[str, Dict[str, Any]] = {}
    current = app_settings.get("call_points", {})
    for call_point_id, definition in AI_CALL_POINT_DEFS.items():
        current_point = current.get(call_point_id, {})
        provider = current_point.get("provider", DEFAULT_PROVIDER)
        model = current_point.get("model") or _default_model_for_provider(provider)
        custom_key = current_point.get("custom_key", "")  # 新增：读取独立Key

        payload[call_point_id] = {
            "label": definition["label"],
            "provider": provider,
            "model": model,
            "custom_key": custom_key,  # 新增：返回独立Key
            "allowed_providers": definition["allowed_providers"],
            "requires_images": definition["requires_images"]
        }
    return payload

class CallPointConfig(BaseModel):
    provider: str
    model: str
    custom_key: Optional[str] = None  # 新增：调用点独立的API Key

class SettingsModel(BaseModel):
    openrouter_api_key: str = ""
    deepseek_api_key: str = ""
    doubao_api_key: str = ""
    call_points: Dict[str, CallPointConfig] = Field(default_factory=dict)
    default_model: Optional[str] = None  # 兼容旧字段

# 全局设置存储（内存中）
app_settings = {
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
    "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "doubao_api_key": os.getenv("ARK_API_KEY", ""),
    "call_points": _build_default_call_points()
}

@app.post("/api/settings")
async def save_settings(settings: SettingsModel):
    """保存系统设置"""
    try:
        app_settings["openrouter_api_key"] = settings.openrouter_api_key
        app_settings["deepseek_api_key"] = settings.deepseek_api_key
        app_settings["doubao_api_key"] = settings.doubao_api_key

        # 更新环境变量
        os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key
        os.environ["DEEPSEEK_API_KEY"] = settings.deepseek_api_key
        os.environ["ARK_API_KEY"] = settings.doubao_api_key

        resolved_call_points = _resolve_call_points(settings.call_points, settings.default_model)
        app_settings["call_points"] = resolved_call_points

        return {
            "success": True,
            "message": "设置保存成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")

@app.get("/api/settings")
async def get_settings():
    """获取当前设置（脱敏）"""
    return {
        "openrouter_api_key": _mask_key(app_settings["openrouter_api_key"]),
        "deepseek_api_key": _mask_key(app_settings["deepseek_api_key"]),
        "doubao_api_key": _mask_key(app_settings["doubao_api_key"]),
        "has_openrouter_key": bool(app_settings["openrouter_api_key"]),
        "has_deepseek_key": bool(app_settings["deepseek_api_key"]),
        "has_doubao_key": bool(app_settings["doubao_api_key"]),
        "call_points": _build_call_point_payload()
    }

class TestModelRequest(BaseModel):
    provider: str = DEFAULT_PROVIDER
    model: str
    openrouter_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    doubao_api_key: Optional[str] = None
    api_key: Optional[str] = None
    custom_key: Optional[str] = None  # 新增：调用点独立Key

@app.post("/api/test-model")
async def test_model(request: TestModelRequest):
    """测试模型连接"""
    try:
        from openai import OpenAI

        provider = request.provider or DEFAULT_PROVIDER
        base_url = AI_PROVIDER_BASE_URLS.get(provider)
        if not base_url:
            raise HTTPException(status_code=400, detail=f"不支持的提供方: {provider}")

        # 优先使用独立Key
        api_key = request.custom_key or request.api_key
        if not api_key:
            if provider == "deepseek":
                api_key = request.deepseek_api_key or app_settings.get("deepseek_api_key")
            elif provider == "doubao":
                api_key = request.doubao_api_key or app_settings.get("doubao_api_key")
            else:
                api_key = request.openrouter_api_key or app_settings.get("openrouter_api_key")

        if not api_key:
            raise HTTPException(status_code=400, detail=f"{provider} API Key 未配置")

        # 创建OpenAI客户端
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )

        # 发送测试请求
        request_payload = {
            "model": request.model,
            "messages": [
                {"role": "user", "content": "Hello, this is a test message. Please respond with 'OK'."}
            ]
        }
        if provider == "doubao":
            request_payload["extra_body"] = {
                "max_completion_tokens": 10
            }
        else:
            request_payload["max_tokens"] = 10
        if provider == "openrouter":
            request_payload["extra_headers"] = {
                "HTTP-Referer": "https://mecagent.com",
                "X-Title": "MecAgent Model Test"
            }
            # ✅ 添加 provider.ignore 排除地域限制
            request_payload["provider"] = {
                "ignore": ["google-ai-studio"]
            }

        completion = client.chat.completions.create(**request_payload)

        # ✅ 防御性检查：确保响应格式正确
        if not completion or not completion.choices or len(completion.choices) == 0:
            return {
                "success": False,
                "error": "API返回了空响应或格式错误，请检查模型配置和API Key"
            }
        
        response_text = completion.choices[0].message.content
        
        # ✅ 检查content是否为None
        if response_text is None:
            return {
                "success": False,
                "error": "API返回的内容为空，请检查模型是否支持"
            }

        return {
            "success": True,
            "message": response_text,
            "model": request.model
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    print("🚀 启动简化版智能装配说明书生成系统...")
    print("📖 API文档: http://localhost:8000/api/docs")
    print("🌐 前端界面: http://localhost:3001")
    
    uvicorn.run(
        "simple_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
