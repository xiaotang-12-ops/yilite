# API 详细文档

**最后更新**: 2025-11-13

---

## 后端 API

### 1. 文件上传
**端点**: `/api/upload`  
**方法**: POST  
**功能**: 上传 PDF 图纸和 STEP 3D 模型文件

**请求参数**:
```typescript
files: List[UploadFile]  // 文件列表
```

**响应**:
```json
{
  "success": true,
  "files": [
    {
      "filename": "产品总图.pdf",
      "path": "uploads/产品总图.pdf"
    }
  ]
}
```

---

### 2. 生成装配说明书
**端点**: `/api/generate`  
**方法**: POST  
**功能**: 调用 AI 处理流水线生成装配说明书

**请求参数**:
```json
{
  "task_id": "70e910d5-75b3-438d-8475-ba728f0ca050"
}
```

**响应**:
```json
{
  "success": true,
  "task_id": "70e910d5-75b3-438d-8475-ba728f0ca050",
  "output_path": "output/70e910d5-75b3-438d-8475-ba728f0ca050/assembly_manual.json"
}
```

---

### 3. 获取输出文件
**端点**: `/output/{path}`  
**方法**: GET  
**功能**: 获取生成的装配说明书、3D 模型、图片等文件

**请求参数**:
```
path: str  // 文件路径，例如: "70e910d5-75b3-438d-8475-ba728f0ca050/assembly_manual.json"
```

**响应**: 文件内容（根据文件类型返回对应的 MIME type）

---

### 4. 健康检查
**端点**: `/api/health`  
**方法**: GET  
**功能**: 检查服务健康状态

**响应**:
```json
{
  "status": "healthy",
  "pipeline_ready": true,
  "timestamp": "2025-11-13T10:30:00"
}
```

---

## 前端路由

### 1. 首页
**路径**: `/`  
**组件**: `Home.vue`  
**功能**: 文件上传和任务创建

---

### 2. 装配说明书查看器
**路径**: `/manual/:taskId`  
**组件**: `ManualViewer.vue`  
**功能**: 查看和编辑装配说明书

**路由参数**:
- `taskId`: 任务ID（UUID）

---

## 数据结构

### 装配说明书 JSON 结构

```json
{
  "version": "1.2",
  "lastUpdated": "2025-11-13T10:30:00",
  "product_overview": {
    "product_name": "V型推雪板",
    "product_code": "E-CW3T"
  },
  "component_assembly": [
    {
      "component_name": "主框架组件-漆后",
      "assembly_order": 1,
      "steps": [
        {
          "step_id": "comp1_step1",
          "step_number": 1,
          "component_name": "主框架组件-漆后",
          "action": "安装底板",
          "parts_used": [...],
          "welding": {
            "required": true,
            "welding_type": "角焊（定位焊）",
            "weld_size": "点焊，焊点长度约10mm",
            "welding_position": "加强板（③）与卷圆板（①）的连接处"
          },
          "safety_warnings": [
            "卷圆板属于重物，必须使用行车或叉车进行吊运"
          ],
          "quality_check": "检查焊接牢固性"
        }
      ]
    }
  ],
  "product_assembly": {
    "steps": [...]
  }
}
```

### 关键字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `step_id` | string | 步骤唯一标识（v1.1.5+） |
| `step_number` | number | 步骤序号 |
| `component_name` | string | 组件名称（可编辑） |
| `action` | string | 操作描述 |
| `welding` | object | 焊接信息（单个对象） |
| `safety_warnings` | string[] | 安全警告（字符串数组） |
| `quality_check` | string | 质检要求 |

---

## 前端编辑功能 API

### 保存编辑内容
**实现方式**: 直接修改 JSON 文件并保存

**保存逻辑**:
1. 前端修改 `manualData` 对象
2. 调用 `saveManualData()` 函数
3. 发送 PUT 请求到后端（待实现）
4. 后端保存到 `output/{task_id}/assembly_manual.json`
5. 自动递增版本号

**当前实现**: 前端直接修改内存中的数据，刷新页面后丢失（需要后端 API 支持）

---

## WebSocket API（未来计划）

### 实时进度推送
**端点**: `/ws/progress/{task_id}`  
**功能**: 推送 AI 处理进度

**消息格式**:
```json
{
  "type": "progress",
  "agent": "Agent 1",
  "status": "processing",
  "progress": 30,
  "message": "正在分析图纸..."
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 文件不存在 |
| 500 | 服务器内部错误 |
| 503 | 处理流水线未初始化 |

