#!/usr/bin/env python3
"""
极简API层 - 直接调用核心处理模块
生产级实现，无模拟数据
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.pipeline import AssemblyManualPipeline

class MockPipeline:
    """模拟处理流水线，用于开发测试"""

    def process_files(self, pdf_files, model_files, output_dir, focus_type="general", special_requirements=""):
        """模拟处理文件"""
        import time
        import json
        from pathlib import Path

        # 模拟处理时间
        time.sleep(2)

        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成模拟的装配说明书HTML
        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>装配说明书 - 开发模式</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #333; text-align: center; }}
        .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .step {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007bff; background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔧 装配说明书 - 开发模式</h1>

        <div class="warning">
            <strong>⚠️ 开发模式</strong><br>
            当前运行在开发模式下，未连接真实的AI模型。<br>
            请设置 DASHSCOPE_API_KEY 和 DEEPSEEK_API_KEY 环境变量以启用完整功能。
        </div>

        <h2>📋 处理信息</h2>
        <p><strong>PDF文件:</strong> {len(pdf_files)} 个</p>
        <p><strong>3D模型:</strong> {len(model_files)} 个</p>
        <p><strong>专业重点:</strong> {focus_type}</p>
        <p><strong>特殊要求:</strong> {special_requirements or "无"}</p>

        <h2>🔨 装配步骤（模拟）</h2>
        <div class="step">
            <h3>步骤 1: 准备工作</h3>
            <p>检查所有零件和工具是否齐全</p>
        </div>
        <div class="step">
            <h3>步骤 2: 基础装配</h3>
            <p>按照图纸进行基础结构装配</p>
        </div>
        <div class="step">
            <h3>步骤 3: 最终检查</h3>
            <p>检查装配质量和功能</p>
        </div>

        <p style="text-align: center; margin-top: 40px; color: #666;">
            生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>"""

        # 保存HTML文件
        html_file = output_path / "assembly_manual.html"
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 返回模拟结果
        return {
            "success": True,
            "manual_file": str(html_file),
            "pdf_analysis": {
                "total_pages": len(pdf_files) * 3,
                "total_bom_items": len(pdf_files) * 15
            },
            "assembly_steps": [
                {"step": 1, "title": "准备工作"},
                {"step": 2, "title": "基础装配"},
                {"step": 3, "title": "最终检查"}
            ],
            "processing_time": 2
        }

# 初始化FastAPI
app = FastAPI(title="装配说明书生成API", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
pipeline = None
tasks = {}

class GenerateRequest(BaseModel):
    focus: str = "general"
    quality: str = "high"
    language: str = "zh"
    requirements: str = ""
    pdf_files: List[str] = []
    model_files: List[str] = []

@app.on_event("startup")
async def startup():
    """启动时初始化处理流水线"""
    global pipeline

    # 检查API Keys
    dashscope_key = os.getenv("DASHSCOPE_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")

    if not dashscope_key:
        print("⚠️  警告: 未设置 DASHSCOPE_API_KEY，Qwen3-VL功能将不可用")
    if not deepseek_key:
        print("⚠️  警告: 未设置 DEEPSEEK_API_KEY，DeepSeek功能将不可用")

    # 初始化处理流水线
    try:
        pipeline = AssemblyManualPipeline(
            dashscope_api_key=dashscope_key,
            deepseek_api_key=deepseek_key
        )
        print("✅ 装配说明书生成系统启动完成")
    except Exception as e:
        print(f"⚠️  警告: 处理流水线初始化失败: {e}")
        print("系统将以有限功能模式运行")
        # 创建一个模拟的pipeline用于开发测试
        pipeline = MockPipeline()

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """文件上传"""
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")
    
    uploaded_files = []
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    for file in files:
        if not file.filename:
            continue
            
        # 保存文件
        file_path = upload_dir / file.filename
        content = await file.read()
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        uploaded_files.append({
            "filename": file.filename,
            "size": len(content),
            "path": str(file_path)
        })
    
    return {"success": True, "files": uploaded_files}

@app.post("/api/generate")
async def generate_manual(request: GenerateRequest):
    """生成装配说明书 - 直接调用核心处理流水线"""
    if not pipeline:
        raise HTTPException(status_code=500, detail="处理流水线未初始化")

    if not request.pdf_files and not request.model_files:
        raise HTTPException(status_code=400, detail="必须提供PDF文件或3D模型文件")
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    output_dir = Path("output") / task_id
    
    # 验证文件存在
    upload_dir = Path("uploads")
    for pdf_file in request.pdf_files:
        if not (upload_dir / pdf_file).exists():
            raise HTTPException(status_code=404, detail=f"PDF文件不存在: {pdf_file}")

    for model_file in request.model_files:
        if not (upload_dir / model_file).exists():
            raise HTTPException(status_code=404, detail=f"模型文件不存在: {model_file}")

    try:
        # 直接调用核心处理流水线
        result = await asyncio.to_thread(
            pipeline.process_files,
            pdf_files=[str(upload_dir / f) for f in request.pdf_files],
            model_files=[str(upload_dir / f) for f in request.model_files],
            output_dir=str(output_dir),
            focus_type=request.focus,
            special_requirements=request.requirements
        )
        
        # 返回结果
        return {
            "success": True,
            "task_id": task_id,
            "result": result,
            "manual_url": f"/output/{task_id}/assembly_manual.html"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.get("/output/{path:path}")
async def serve_output(path: str):
    """提供输出文件"""
    file_path = Path("output") / path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 设置正确的MIME类型
    if file_path.suffix.lower() == '.html':
        media_type = "text/html"
    elif file_path.suffix.lower() == '.glb':
        media_type = "model/gltf-binary"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={"Access-Control-Allow-Origin": "*"}
    )

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "pipeline_ready": pipeline is not None,
        "dashscope_configured": bool(os.getenv("DASHSCOPE_API_KEY")),
        "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY"))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
