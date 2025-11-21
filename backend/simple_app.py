# -*- coding: utf-8 -*-
"""
简化版后端测试
"""

import os
import sys
import json
import uuid
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# ✅ 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ✅ 定义output目录的绝对路径（确保无论从哪里启动都能找到正确的目录）
OUTPUT_DIR = project_root / "output"
OUTPUT_DIR.mkdir(exist_ok=True)  # 确保目录存在

from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel
import uvicorn
import asyncio

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

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
        "timestamp": datetime.now().isoformat()
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

# 全局变量
tasks = {}
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "智能装配说明书生成系统 API"}

@app.post("/api/upload")
async def upload_files(
    pdf_files: List[UploadFile] = File(default=[]),
    model_files: List[UploadFile] = File(default=[])
):
    """上传文件接口 - 支持PDF和3D模型文件"""

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
    task_id = str(uuid.uuid4())

    try:
        # 创建任务目录
        task_dir = OUTPUT_DIR / task_id
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
        for pdf_file in request.pdf_files:
            src = upload_dir / pdf_file
            dst = pdf_dir / pdf_file
            if src.exists():
                shutil.copy2(src, dst)
                print(f"📄 已复制PDF: {pdf_file}")

        for step_file in request.model_files:
            src = upload_dir / step_file
            dst = step_dir / step_file
            if src.exists():
                shutil.copy2(src, dst)
                print(f"🎯 已复制STEP: {step_file}")

        # 创建任务记录
        tasks[task_id] = {
            "task_id": task_id,
            "status": "processing",
            "progress": 0,
            "config": request.config.model_dump(),
            "pdf_files": request.pdf_files,
            "model_files": request.model_files,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        # 直接调用gemini_pipeline（在后台线程中）
        import threading

        def run_pipeline():
            try:
                # 导入并运行pipeline
                import sys
                import os
                sys.path.append(str(Path(__file__).parent.parent))
                from core.gemini_pipeline import GeminiAssemblyPipeline
                from utils.logger import set_current_task  # ✅ 导入日志任务设置函数

                # ✅ 设置当前任务ID，让logger知道日志应该路由到哪个任务
                set_current_task(task_id)

                # 从保存的设置中读取API密钥和模型，如果没有则从环境变量读取
                api_key = app_settings.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
                if not api_key:
                    raise ValueError("未设置 OpenRouter API Key，请在设置页面配置")

                # 获取模型名称
                model_name = app_settings.get("default_model") or "google/gemini-2.0-flash-exp:free"

                print(f"✅ Backend 使用模型: {model_name}")

                # ✅ 获取用户输入的产品名称
                product_name = request.config.projectName

                pipeline = GeminiAssemblyPipeline(
                    api_key=api_key,
                    output_dir=str(task_dir),
                    product_name=product_name,  # ✅ 传入产品名称
                    model_name=model_name  # ✅ 传入模型名称
                )

                # 运行pipeline
                result = pipeline.run(
                    pdf_dir=str(pdf_dir),
                    step_dir=str(step_dir)
                )

                # 更新任务状态
                tasks[task_id]["status"] = "completed"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["result"] = result
                tasks[task_id]["updated_at"] = datetime.now()

            except Exception as e:
                print(f"Pipeline执行错误: {e}")
                tasks[task_id]["status"] = "failed"
                tasks[task_id]["error"] = str(e)
                tasks[task_id]["updated_at"] = datetime.now()

        # 在后台线程中运行
        thread = threading.Thread(target=run_pipeline)
        thread.start()

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
        raise HTTPException(status_code=404, detail="任务不存在")

    return tasks[task_id]

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
                    yield f"data: {json.dumps({'type': 'progress', 'task_id': task_id, 'progress': task.get('progress', 0), 'status': current_status})}\n\n"

                    # 如果状态变化，发送状态更新
                    if current_status != last_status:
                        yield f"data: {json.dumps({'type': 'status_change', 'task_id': task_id, 'status': current_status})}\n\n"
                        last_status = current_status

                    # 如果任务完成或失败，发送最终消息并结束
                    if current_status in ["completed", "failed"]:
                        yield f"data: {json.dumps({'type': 'complete', 'task_id': task_id, 'status': current_status, 'result': task.get('result'), 'error': task.get('error')})}\n\n"
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
            "timestamp": datetime.now().isoformat()
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
                        "timestamp": datetime.now().isoformat()
                    })

                    # 如果任务完成或失败，发送最终消息
                    if task["status"] in ["completed", "failed"]:
                        await websocket.send_json({
                            "type": "complete",
                            "task_id": task_id,
                            "status": task["status"],
                            "result": task.get("result"),
                            "error": task.get("error"),
                            "timestamp": datetime.now().isoformat()
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
async def list_manuals():
    """
    获取所有已生成的装配说明书列表
    ✅ 扫描output目录，返回所有包含assembly_manual.json的任务
    """
    try:
        output_base = OUTPUT_DIR
        if not output_base.exists():
            return {"manuals": [], "total": 0}

        manuals = []

        # 遍历output目录下的所有子目录
        for task_dir in output_base.iterdir():
            if not task_dir.is_dir():
                continue

            manual_path = task_dir / "assembly_manual.json"
            if not manual_path.exists():
                continue

            try:
                # 读取说明书元数据
                with open(manual_path, 'r', encoding='utf-8') as f:
                    manual_data = json.load(f)

                # 获取文件修改时间
                mtime = manual_path.stat().st_mtime
                timestamp = datetime.fromtimestamp(mtime).isoformat()

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
        output_dir = OUTPUT_DIR / task_id

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
        output_dir = OUTPUT_DIR / task_id

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
        # ✅ 直接检查输出目录（不依赖tasks字典）
        output_dir = OUTPUT_DIR / task_id

        if not output_dir.exists():
            raise HTTPException(
                status_code=404,
                detail=f"任务输出目录不存在。任务ID: {task_id}，可能任务未执行或已被删除。"
            )

        # ✅ 可选：如果任务在内存中，检查状态
        if task_id in tasks:
            task = tasks[task_id]
            if task["status"] == "processing":
                raise HTTPException(status_code=400, detail="任务正在处理中，请稍后再试")
            elif task["status"] == "failed":
                raise HTTPException(status_code=400, detail=f"任务失败: {task.get('error', '未知错误')}")

        # 查找 assembly_manual.json
        manual_path = output_dir / "assembly_manual.json"
        if not manual_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"装配说明书文件不存在。路径: {manual_path}"
            )

        # 读取并返回 JSON 数据
        with open(manual_path, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)

        # ✅ 替换所有的{task_id}占位符为实际的task_id
        manual_json_str = json.dumps(manual_data, ensure_ascii=False)
        manual_json_str = manual_json_str.replace("{task_id}", task_id)
        manual_data = json.loads(manual_json_str)

        print(f"✅ 成功加载说明书: {task_id}")
        return manual_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 获取说明书失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取说明书失败: {str(e)}")

@app.put("/api/manual/{task_id}")
async def update_manual(task_id: str, manual_data: dict):
    """
    更新装配说明书内容（管理员功能）
    - 接收前端提交的完整assembly_manual.json数据
    - 自动递增版本号(格式: major.minor)
    - 添加lastUpdated时间戳
    - 保存到output/{task_id}/assembly_manual.json
    """
    try:
        output_dir = OUTPUT_DIR / task_id
        if not output_dir.exists():
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        manual_path = output_dir / "assembly_manual.json"

        # 自动递增版本号
        current_version = manual_data.get('version', '1.0')
        try:
            major, minor = map(int, current_version.split('.'))
            new_version = f"{major}.{minor + 1}"
        except:
            # 如果版本号格式不正确，从1.1开始
            new_version = "1.1"

        manual_data['version'] = new_version
        manual_data['lastUpdated'] = datetime.now().isoformat()

        # 保存文件
        with open(manual_path, 'w', encoding='utf-8') as f:
            json.dump(manual_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 成功更新说明书: {task_id}, 版本: {new_version}")
        return {"success": True, "version": new_version, "message": "更新成功"}

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
    快速获取版本号（用于前端缓存检查）
    - 只返回版本号，不返回完整数据
    - 用于前端检查数据是否需要更新
    """
    try:
        output_dir = Path("output") / task_id
        manual_path = output_dir / "assembly_manual.json"

        if not manual_path.exists():
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        with open(manual_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        version = data.get('version', '1.0')

        # 使用Response返回，在header中包含版本号
        return Response(headers={"X-Manual-Version": version})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本号失败: {str(e)}")

# ============ 设置管理端点 ============
class SettingsModel(BaseModel):
    openrouter_api_key: str
    default_model: str = "google/gemini-2.5-flash-preview-09-2025"

# 全局设置存储（内存中）
app_settings = {
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
    "default_model": "google/gemini-2.5-flash-preview-09-2025"
}

@app.post("/api/settings")
async def save_settings(settings: SettingsModel):
    """保存系统设置"""
    try:
        app_settings["openrouter_api_key"] = settings.openrouter_api_key
        app_settings["default_model"] = settings.default_model

        # 更新环境变量
        os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

        return {
            "success": True,
            "message": "设置保存成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")

@app.get("/api/settings")
async def get_settings():
    """获取当前设置（脱敏）"""
    return {
        "openrouter_api_key": app_settings["openrouter_api_key"][:10] + "..." if app_settings["openrouter_api_key"] else "",
        "default_model": app_settings["default_model"],
        "has_openrouter_key": bool(app_settings["openrouter_api_key"])
    }

class TestModelRequest(BaseModel):
    openrouter_api_key: str
    model: str

@app.post("/api/test-model")
async def test_model(request: TestModelRequest):
    """测试模型连接"""
    try:
        from openai import OpenAI

        # 创建OpenAI客户端（OpenRouter兼容）
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=request.openrouter_api_key
        )

        # 发送测试请求
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://mecagent.com",
                "X-Title": "MecAgent Model Test"
            },
            model=request.model,
            messages=[
                {"role": "user", "content": "Hello, this is a test message. Please respond with 'OK'."}
            ],
            max_tokens=10
        )

        response_text = completion.choices[0].message.content

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
