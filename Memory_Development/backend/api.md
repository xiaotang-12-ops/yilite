# 后端 API 速查 (FastAPI / port 8008)

> 来源：`backend/simple_app.py`。所有路径默认前缀 `/api`，除 WebSocket `/ws/task/{task_id}`。

| 方法 | 路径 | 目的 | 请求要点 | 响应/副作用 |
| --- | --- | --- | --- | --- |
| GET | `/api/health` | 健康检查 | - | `status`,`version`,`timestamp` |
| POST | `/api/upload` | 上传 PDF/STEP/STL | FormData：`pdf_files[]`, `model_files[]`；上传前清空 `uploads/` | 返回文件名/size/path；写入磁盘 |
| POST | `/api/generate` | 启动生成任务 | JSON：`config.projectName`，`pdf_files[]`，`model_files[]`；复制上传文件到 `output/{task}/` | 返回 `task_id`，后台线程跑 `GeminiAssemblyPipeline.run`，任务状态写入 `tasks` |
| GET | `/api/status/{task_id}` | 查询任务状态 | 路径参数 | 返回内存中的任务字典 |
| GET | `/api/stream/{task_id}` | SSE 日志/进度流 | 路径参数 | 文本/event-stream，读取 utils.logger 日志缓冲 |
| WS | `/ws/task/{task_id}` | WebSocket 进度流 | 路径参数 | 周期推送进度/完成/失败 |
| GET | `/api/manuals` | 列出已生成手册 | - | 扫描 `output/*/assembly_manual.json`，返回列表 |
| GET | `/api/manual/{task_id}` | 读取手册 JSON | 路径参数 | 直接读文件，替换 JSON 中 `{task_id}` 占位 |
| PUT | `/api/manual/{task_id}` | 更新手册并自增版本 | 路径参数 + 完整 JSON | 版本号 `major.minor+1`，写回 `assembly_manual.json`，更新 `lastUpdated` |
| DELETE | `/api/manual/{task_id}` | 删除任务目录 | 路径参数 | 删除 `output/{task_id}`，移除内存任务 |
| HEAD | `/api/manual/{task_id}/version` | 取版本号 | 路径参数 | Header `X-Manual-Version` |
| GET | `/api/manual/{task_id}/glb/{glb}` | 下载 GLB | 路径参数 | 查找 `output/{task}/glb_files/{glb}` 或根目录 |
| GET | `/api/manual/{task_id}/pdf_images/{path}` | 下载 PDF 图片 | 路径参数 | 访问 `output/{task}/pdf_images/{pdf_name}/page_xxx.png` |
| POST | `/api/settings` | 保存 API Key & 模型 | JSON：`openrouter_api_key`,`default_model` | 保存在内存 `app_settings`，更新环境变量 |
| GET | `/api/settings` | 获取已保存设置 | - | 返回脱敏的 key、默认模型、是否已配置 |
| POST | `/api/test-model` | OpenRouter 连通性测试 | JSON：`openrouter_api_key`,`model` | 调用 ChatCompletion，返回测试响应文本 |

### 任务/输出目录结构
- 上传：`uploads/`（每次上传会清空旧文件）
- 生成输出：`output/{task_id}/`，包含 `assembly_manual.json`、`glb_files/`、`pdf_images/{pdf}/page_*.png` 等阶段产物。

### 运行端口
- Docker：`uvicorn backend.simple_app:app --port 8008`（Dockerfile EXPOSE 8008，compose 映射 8008:8008）
- 本地快速调试：可手动运行但需与前端 baseURL 配置一致。
