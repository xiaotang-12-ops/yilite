# 装配说明书生成系统 - 前端对接指南

**版本**: v0.0.2  
**更新日期**: 2025-10-03  
**适用对象**: 前端开发人员

---

## 📋 目录

1. [核心入口文件](#核心入口文件)
2. [输入参数说明](#输入参数说明)
3. [输出文件位置](#输出文件位置)
4. [日志文件位置](#日志文件位置)
5. [数据结构说明](#数据结构说明)
6. [调用示例](#调用示例)
7. [错误处理](#错误处理)

---

## 🎯 核心入口文件

### 主程序入口

**文件路径**: `core/gemini_pipeline.py`

**核心类**: `GeminiPipeline`

**主要方法**: `run()`

### 快速启动

```python
from core.gemini_pipeline import GeminiPipeline

# 创建pipeline实例
pipeline = GeminiPipeline()

# 运行完整流程
result = pipeline.run()

# 检查结果
if result["success"]:
    print(f"✅ 成功生成装配说明书")
    print(f"📄 输出文件: {result['output_file']}")
else:
    print(f"❌ 生成失败: {result['error']}")
```

---

## 📥 输入参数说明

### 必需的输入文件

系统会自动从以下目录读取文件：

#### 1. PDF图纸文件

**目录**: `测试-pdf/`

**文件要求**:
- 产品总图: `产品总图.pdf`
- 组件图: `组件图1.pdf`, `组件图2.pdf`, `组件图3.pdf`

**文件格式**: PDF格式，包含BOM表和装配图

#### 2. 3D模型文件

**目录**: `step-stl文件/`

**文件要求**:
- 产品模型: `产品测试.STEP`
- 组件模型: `组件图1.STEP`, `组件图2.STEP`, `组件图3.STEP`

**文件格式**: STEP格式（推荐）或STL格式

### 可选配置

**配置文件**: `config.py`

```python
# API配置
OPENROUTER_API_KEY = "your_api_key_here"

# 模型配置
GEMINI_MODEL = "google/gemini-2.5-flash-preview-09-2025"

# 输出目录
OUTPUT_DIR = "pipeline_output"
```

---

## 📤 输出文件位置

### 主要输出文件

所有输出文件都在 `pipeline_output/` 目录下：

#### 1. **最终装配说明书** ⭐

**文件路径**: `pipeline_output/assembly_manual.json`

**用途**: 前端渲染装配说明书的主要数据源

**包含内容**:
- 产品元数据
- 组件装配步骤（含3D高亮信息）
- 产品总装步骤
- BOM到Mesh映射表
- 焊接和安全信息

#### 2. **3D模型文件**

**目录**: `pipeline_output/glb_files/`

**文件列表**:
- `component_01_03_6999.glb` - 组件1的3D模型
- `component_01_03_7000.glb` - 组件2的3D模型
- `component_01_03_7001.glb` - 组件3的3D模型
- `product_total.glb` - 产品总装3D模型

#### 3. **中间结果文件**（可选查看）

| 文件名 | 说明 |
|--------|------|
| `step1_file_hierarchy.json` | 文件分类结果 |
| `step2_bom_data.json` | BOM数据提取结果 |
| `step3_planning_result.json` | 装配规划结果 |
| `step4_matching_result.json` | BOM-3D匹配结果 |
| `step5_component_results.json` | 组件装配步骤 |
| `step6_product_result.json` | 产品总装步骤 |
| `step7_enhanced_component_results.json` | 增强后的组件步骤（含焊接/安全） |
| `step7_enhanced_product_result.json` | 增强后的产品步骤（含焊接/安全） |

#### 4. **PDF转图片**

**目录**: `pipeline_output/pdf_images/`

**说明**: PDF图纸转换成的PNG图片，供AI视觉分析使用

---

## 📊 日志文件位置

### 控制台日志

程序运行时会在控制台输出详细的进度信息：

```
================================================================================
🚀 Gemini 6-Agent装配说明书生成工作流启动
================================================================================
📁 输出目录: pipeline_output
📋 总步骤数: 8

--------------------------------------------------------------------------------
[1/8] 📂 文件管理员
--------------------------------------------------------------------------------
[15:49:26] 👷 文件管理AI员工加入工作，他开始查看文件夹里有哪些图纸...
  📄 他发现了 4 个PDF图纸
...
```

### Debug日志

**目录**: `debug_output/`

**文件命名**: `Agent{N}_{任务名}_{时间戳}.json`

**示例**:
- `Agent1__20251003_154946.json` - Agent 1的视觉规划结果
- `Agent3__20251003_155117.json` - Agent 3的组件装配结果
- `ai_matching_response_1759477792.txt` - AI匹配的详细响应

**用途**: 调试和问题排查

---

## 📐 数据结构说明

### assembly_manual.json 结构

```json
{
  "metadata": {
    "product_name": "产品名称",
    "total_components": 3,
    "base_component": {
      "code": "01.03.7000",
      "name": "后座连接架组件"
    },
    "generated_at": "2025-10-03 15:53:13"
  },
  
  "component_assembly": [
    {
      "component_code": "01.03.6999",
      "component_name": "连接器后座组件",
      "glb_file": "component_01_03_6999.glb",
      "steps": [
        {
          "step_number": 1,
          "title": "连接板定位",
          "parts_used": [
            {
              "bom_code": "01.01.11509",
              "bom_name": "连接板",
              "quantity": 1,
              "mesh_id": ["mesh_018"]  // ⭐ 3D高亮用
            }
          ],
          "tools_required": ["划线笔", "平台"],
          "operation": "操作说明...",
          "quality_check": "质量检查要求...",
          "estimated_time_minutes": 5,
          "welding": {  // ⭐ 焊接信息（如果需要）
            "required": true,
            "welding_type": "点焊",
            "welding_method": "CO2气保焊",
            ...
          },
          "safety_warnings": [  // ⭐ 安全警告
            "警告1",
            "警告2"
          ]
        }
      ]
    }
  ],
  
  "product_assembly": {
    "glb_file": "product_total.glb",
    "steps": [
      {
        "step_number": 1,
        "title": "安装连接器后座",
        "component_code": "01.03.6999",
        "fasteners": [
          {
            "bom_code": "02.03.0458",
            "bom_name": "六角头螺栓",
            "spec": "M30*60",
            "quantity": 2
          }
        ],
        "operation": "操作说明...",
        ...
      }
    ]
  },
  
  "3d_resources": {
    "bom_to_mesh": {  // ⭐ 全局BOM到Mesh映射表
      "02.03.1035": ["mesh_001", "mesh_004", "mesh_005", ...],
      "01.09.2561": ["mesh_253"]
    },
    "component_to_glb": {
      "01.03.6999": "component_01_03_6999.glb",
      "01.03.7000": "component_01_03_7000.glb",
      "01.03.7001": "component_01_03_7001.glb"
    },
    "product_glb": "product_total.glb"
  }
}
```

### 关键字段说明

| 字段 | 说明 | 用途 |
|------|------|------|
| `glb_file` | GLB文件名 | 加载3D模型 |
| `mesh_id` | Mesh ID数组 | 高亮零件 |
| `bom_code` | BOM代号 | 查询映射表 |
| `welding` | 焊接信息 | 显示焊接要求 |
| `safety_warnings` | 安全警告 | 显示安全提示 |
| `bom_to_mesh` | BOM到Mesh映射 | 快速查询 |

---

## 💻 调用示例

### 示例1: 基本调用

```python
from core.gemini_pipeline import GeminiPipeline

# 创建pipeline
pipeline = GeminiPipeline()

# 运行
result = pipeline.run()

# 获取输出文件路径
if result["success"]:
    manual_path = result["output_file"]
    print(f"装配说明书: {manual_path}")
```

### 示例2: 读取结果

```python
import json

# 读取装配说明书
with open("pipeline_output/assembly_manual.json", "r", encoding="utf-8") as f:
    manual = json.load(f)

# 获取组件装配步骤
for component in manual["component_assembly"]:
    print(f"组件: {component['component_name']}")
    print(f"GLB文件: {component['glb_file']}")
    
    for step in component["steps"]:
        print(f"  步骤{step['step_number']}: {step['title']}")
        
        # 获取需要高亮的零件
        for part in step["parts_used"]:
            mesh_ids = part.get("mesh_id", [])
            print(f"    零件: {part['bom_name']}, Mesh: {mesh_ids}")
```

### 示例3: 前端渲染流程

```javascript
// 1. 加载装配说明书
const response = await fetch('/api/assembly_manual.json');
const manual = await response.json();

// 2. 加载GLB模型
const glbUrl = `/glb_files/${manual.component_assembly[0].glb_file}`;
const model = await loadGLB(glbUrl);

// 3. 高亮零件
const step = manual.component_assembly[0].steps[0];
const meshIds = step.parts_used[0].mesh_id;

meshIds.forEach(meshId => {
  highlightMesh(model, meshId);
});

// 4. 显示焊接信息
if (step.welding && step.welding.required) {
  showWeldingInfo(step.welding);
}

// 5. 显示安全警告
if (step.safety_warnings && step.safety_warnings.length > 0) {
  showSafetyWarnings(step.safety_warnings);
}
```

---

## ⚠️ 错误处理

### 常见错误

#### 1. 文件未找到

**错误信息**: `FileNotFoundError: 未找到产品总图.pdf`

**解决方案**: 确保 `测试-pdf/` 目录下有所需的PDF文件

#### 2. API密钥错误

**错误信息**: `API key not found`

**解决方案**: 在 `config.py` 中配置 `OPENROUTER_API_KEY`

#### 3. 3D模型转换失败

**错误信息**: `STEP文件加载失败`

**解决方案**: 
- 检查STEP文件是否损坏
- 确保安装了 `OCP` 库: `pip install cadquery`

### 错误日志查看

```python
# 查看详细错误信息
result = pipeline.run()

if not result["success"]:
    print(f"错误: {result['error']}")
    print(f"详细信息: {result.get('details', '')}")
```

---

## 📞 技术支持

如有问题，请查看：

1. **Debug日志**: `debug_output/` 目录
2. **中间结果**: `pipeline_output/step*.json` 文件
3. **控制台输出**: 运行时的详细日志

---

## 🔄 版本历史

### v0.0.2 (2025-10-03)
- ✅ 完成BOM-3D匹配优化（匹配率提升至92.7%）
- ✅ Agent 5和Agent 6重构为嵌入式逻辑
- ✅ 修复组件图片传递问题
- ✅ 清理无用文件和代码

### v0.0.1 (2025-10-02)
- 初始版本发布

