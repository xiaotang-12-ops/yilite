# 数据流与处理链路

> 来源：`core/gemini_pipeline.py`、`backend/simple_app.py`。

1. 上传阶段  
   - 前端 `/generator` 通过 `/api/upload` 提交 PDF/STEP/STL。后端清空 `uploads/` 后写入新文件。
2. 任务创建  
   - `/api/generate` 生成 `task_id`，复制上传文件到 `output/{task_id}/pdf_files`、`output/{task_id}/step_files`，后台线程启动 `GeminiAssemblyPipeline.run`。
3. 流水线（GeminiAssemblyPipeline）  
   - 文件分类：`FileClassifier` → 产品图/组件图/零件图。  
   - PDF 转图片、STEP 转 GLB（需 Blender）。  
   - 视觉规划（Agent1）→ 装配规划 JSON。  
   - BOM/3D 匹配（HierarchicalBOMMatcher + Agent2 视觉匹配）→ 匹配结果 JSON。  
   - 组件装配步骤（Agent3）、产品总装步骤（Agent4）。  
   - 焊接工艺（Agent5）、安全 FAQ（Agent6）。  
   - 手册整合：`ManualIntegratorV2` → `assembly_manual.json`（嵌入模型/图片路径）。
4. 结果访问  
   - JSON：`/api/manual/{task_id}` 读取 `assembly_manual.json`；`/api/manuals` 列表。  
   - 媒体：`/api/manual/{task_id}/glb/{file}`（GLB），`/api/manual/{task_id}/pdf_images/{pdf}/page_xxx.png`。  
   - 进度/日志：`/api/status/{task_id}`、SSE `/api/stream/{task_id}`、WebSocket `/ws/task/{task_id}`。
5. 编辑与版本  
   - 前端 ManualViewer 支持编辑焊接/安全/质检/组件名；调用 `PUT /api/manual/{task_id}` 自增版本号、写回并打 `lastUpdated`。

输出目录示例
```
output/{task_id}/
├── assembly_manual.json
├── glb_files/*.glb
├── pdf_images/{pdf_name}/page_001.png
├── pdf_files/*.pdf
├── step_files/*.stp|*.step|*.stl
└── （其他阶段性 JSON / 日志）
```
