# 数据流与处理链路

> 来源：`core/gemini_pipeline.py`、`backend/simple_app.py`。

1. 上传阶段  
   - 前端 `/generator` 通过 `/api/upload` 提交 PDF/STEP/STL。后端清空 `uploads/` 后写入新文件。
2. 任务创建  
   - `/api/generate` 生成 `task_id`，复制上传文件到 `output/{task_id}/pdf_files`、`output/{task_id}/step_files`，后台线程启动 `GeminiAssemblyPipeline.run`。
3. 流水线（GeminiAssemblyPipeline）
   - **Step1**: 文件分类：`FileClassifier` → 产品图/组件图/零件图。
   - **Step2**: PDF 转图片、STEP 转 GLB（需 Blender）。
   - **Step3**: 装配规划（SimplePlanner）→ 按BOM序号生成装配规划（内存传递，不保存文件）。
     - **核心规则**：基准件=BOM序号1，装配顺序=BOM序号顺序
     - **输出**：planning_result（内存对象，不再保存step3_planning_result.json）
   - **Step4**: BOM/3D 匹配（HierarchicalBOMMatcher + Agent2 视觉匹配）→ 匹配结果 JSON。
   - **Step5**: 组件装配步骤（Agent3）、产品总装步骤（Agent4）。
     - **装配规则**：严格按BOM序号装配，步骤数=BOM项数，每步装配1个零件
   - **Step6**: 焊接工艺（Agent5）。
   - **Step7**: 安全 FAQ（Agent6）→ `step7_enhanced_result.json`（AI 视角：装配 + 焊接 + 安全）。
   - **Step8**: 手册整合：`ManualIntegratorV2` → `assembly_manual.json`（前端视角：添加图纸路径、step_id、3D 资源、API 路径、元数据）。
4. 结果访问  
   - JSON：`/api/manual/{task_id}` 读取 `assembly_manual.json`；`/api/manuals` 列表。  
   - 媒体：`/api/manual/{task_id}/glb/{file}`（GLB），`/api/manual/{task_id}/pdf_images/{pdf}/page_xxx.png`。  
   - 进度/日志：`/api/status/{task_id}`、SSE `/api/stream/{task_id}`、WebSocket `/ws/task/{task_id}`。
5. 编辑与版本  
   - 前端 ManualViewer 支持编辑焊接/安全/质检/组件名；调用 `PUT /api/manual/{task_id}` 自增版本号、写回并打 `lastUpdated`。

输出目录示例
```
output/{task_id}/
├── assembly_manual.json              # Step8 输出：前端最终使用的手册（包含图纸路径、3D 资源等）
├── draft.json                        # 草稿版本（编辑器使用）
├── versions/                         # 版本归档目录
│   ├── v1.json                       # 版本1
│   ├── v2.json                       # 版本2
│   └── version_history.json          # 版本历史元数据
├── step7_enhanced_result.json        # Step7 输出：AI 增强后的结果（装配 + 焊接 + 安全）
├── bom_data.json                     # BOM提取结果
├── matching_result.json              # BOM-3D匹配结果
├── glb_files/*.glb                   # Step2 输出：STEP 转换的 GLB 文件
├── pdf_images/{pdf_name}/page_001.png # Step2 输出：PDF 转换的图片
├── pdf_files/*.pdf                   # 原始 PDF 文件
├── step_files/*.stp|*.step|*.stl     # 原始 STEP 文件
└── （其他阶段性 JSON / 日志）

❌ 已删除的文件：
- step3_planning_result.json          # v2.0.10删除：基准件现在固定为BOM序号1，不需要保存规划结果
```

**Step7 vs Step8 的区别**：
- **step7_enhanced_result.json**：AI 视角的数据
  - 包含：装配步骤、焊接信息、安全警告
  - 缺少：图纸路径、step_id、3D 资源路径、API 路径
  - 用途：调试、检查 AI 输出质量

- **assembly_manual.json**：前端视角的数据
  - 包含：step7 的所有内容 + 图纸路径 + step_id + 3D 资源 + API 路径 + 元数据
  - 用途：前端渲染、用户查看
