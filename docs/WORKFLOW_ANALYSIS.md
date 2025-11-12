# 智能装配说明书生成系统 - 完整工作流程分析

**文档版本**: 1.0  
**创建日期**: 2025-11-11  
**分析目标**: 理解从用户上传文件到生成完整装配说明书的全流程

---

## 📋 目录

1. [系统架构概览](#系统架构概览)
2. [完整执行流程](#完整执行流程)
3. [Output文件生成详解](#output文件生成详解)
4. [6个AI智能体详解](#6个ai智能体详解)
5. [数据流向图](#数据流向图)

---

## 系统架构概览

### 核心组件

```
用户上传文件
    ↓
FastAPI后端 (backend/simple_app.py)
    ↓
Gemini Pipeline (core/gemini_pipeline.py)
    ↓
6个AI智能体 + 3个核心处理器
    ↓
Output文件夹 (装配说明书JSON + 3D模型 + 图片)
```

### 技术栈

- **后端框架**: FastAPI
- **AI模型**: Google Gemini 2.0 Flash (via OpenRouter)
- **3D处理**: Blender (STEP → GLB转换)
- **PDF处理**: PyMuPDF (PDF → 图片转换)
- **视觉分析**: Gemini Vision API (BOM提取 + 装配规划)

---

## 完整执行流程

### 流程图

```
步骤0: 用户上传文件
  ↓ API: POST /api/upload
  ↓ 保存到: uploads/
  
步骤1: 文件分类 + PDF转图片
  ↓ 模块: FileClassifier (core/file_classifier.py)
  ↓ 输出: step1_file_hierarchy.json + step1_image_hierarchy.json
  ↓ 图片: pdf_images/
  
步骤2: BOM数据提取
  ↓ 模块: Gemini Vision API (gemini_pipeline.py)
  ↓ 输出: step2_bom_data.json
  
步骤3: Agent 1 - 视觉规划
  ↓ 智能体: VisionPlanningAgent
  ↓ 提示词: prompts/agent_1_vision_planning.py
  ↓ 输出: step3_planning_result.json
  
步骤4: Agent 2 - BOM-3D匹配
  ↓ 模块: HierarchicalBOMMatcher (core/hierarchical_bom_matcher_v2.py)
  ↓ 3D转换: Blender (STEP → GLB)
  ↓ 输出: step4_matching_result.json + glb_files/
  
步骤5: Agent 3 - 组件装配
  ↓ 智能体: ComponentAssemblyAgent
  ↓ 提示词: prompts/agent_3_component_assembly.py
  ↓ 输出: step5_component_results.json
  
步骤6: Agent 4 - 产品总装
  ↓ 智能体: ProductAssemblyAgent
  ↓ 提示词: prompts/agent_4_product_assembly.py
  ↓ 输出: step6_product_result.json
  
步骤7: Agent 5 & 6 - 焊接 + 安全
  ↓ 智能体: WeldingAgent + SafetyFAQAgent
  ↓ 提示词: prompts/agent_5_welding.py + prompts/agent_6_safety_faq.py
  ↓ 输出: step7_enhanced_component_results.json + step7_enhanced_product_result.json
  
步骤8: 整合最终手册
  ↓ 模块: ManualIntegratorV2 (core/manual_integrator_v2.py)
  ↓ 输出: assembly_manual.json (最终装配说明书)
```

---

## Output文件生成详解

### 文件夹结构

```
output/
└── {task_id}/                          # 任务ID（UUID）
    ├── assembly_manual.json            # 最终装配说明书 (步骤8)
    ├── step1_file_hierarchy.json       # 文件分类结果 (步骤1)
    ├── step1_image_hierarchy.json      # 图片层级结构 (步骤1)
    ├── step2_bom_data.json             # BOM数据 (步骤2)
    ├── step3_planning_result.json      # 装配规划 (步骤3)
    ├── step4_matching_result.json      # BOM-3D匹配结果 (步骤4)
    ├── step5_component_results.json    # 组件装配步骤 (步骤5)
    ├── step6_product_result.json       # 产品总装步骤 (步骤6)
    ├── step7_enhanced_component_results.json  # 增强后的组件步骤 (步骤7)
    ├── step7_enhanced_product_result.json     # 增强后的产品步骤 (步骤7)
    ├── glb_files/                      # 3D模型文件 (步骤4)
    │   ├── component_1.glb
    │   ├── component_2.glb
    │   ├── component_3.glb
    │   ├── product_total.glb
    │   ├── manifest_component_1.json
    │   ├── manifest_component_2.json
    │   ├── manifest_component_3.json
    │   └── manifest_product.json
    ├── pdf_images/                     # PDF转换的图片 (步骤1)
    │   ├── 产品总图/
    │   │   └── page_001.png
    │   ├── 1/组件图1/
    │   │   └── page_001.png
    │   ├── 2/组件图2/
    │   │   └── page_001.png
    │   └── 3/组件图3/
    │       └── page_001.png
    ├── pdf_files/                      # 原始PDF文件（复制）
    │   ├── 产品总图.PDF
    │   ├── 组件图1.PDF
    │   ├── 组件图2.PDF
    │   └── 组件图3.PDF
    └── step_files/                     # 原始STEP文件（复制）
        ├── 产品总图.STEP
        ├── 组件图1.STEP
        ├── 组件图2.STEP
        └── 组件图3.STEP
```

### 详细文件说明

#### 1. step1_file_hierarchy.json (步骤1)

**生成函数**: `FileClassifier.classify_files()`  
**文件位置**: `core/file_classifier.py` 第24-152行  
**输入数据**: PDF文件列表 + STEP文件列表  
**处理逻辑**:
1. 使用正则表达式匹配文件名
2. 识别产品总图（包含"产品"、"总图"关键词）
3. 识别组件图（包含"组件图1"、"组件图2"等）
4. 匹配PDF和STEP文件（基于文件名）

**数据结构**:
```json
{
  "product": {
    "pdf": "产品总图.PDF",
    "step": "产品总图.STEP",
    "product_code": ""
  },
  "components": [
    {
      "index": 1,
      "name": "组件图1",
      "bom_code": "",
      "pdf": "组件图1.PDF",
      "step": "组件图1.STEP"
    }
  ]
}
```

---

#### 2. step1_image_hierarchy.json (步骤1)

**生成函数**: `FileClassifier.convert_pdfs_to_images()`  
**文件位置**: `core/file_classifier.py` 第154-306行  
**输入数据**: step1_file_hierarchy.json  
**处理逻辑**:
1. 使用PyMuPDF (fitz)打开PDF文件
2. 将每一页转换为PNG图片（DPI=200）
3. 保存到 `pdf_images/` 目录
4. 记录图片路径到JSON

**数据结构**:
```json
{
  "product_images": [
    "/api/manual/{task_id}/pdf_images/产品总图/page_001.png"
  ],
  "component_images": {
    "1": ["/api/manual/{task_id}/pdf_images/1/组件图1/page_001.png"],
    "2": ["/api/manual/{task_id}/pdf_images/2/组件图2/page_001.png"],
    "3": ["/api/manual/{task_id}/pdf_images/3/组件图3/page_001.png"]
  }
}
```

---

#### 3. step2_bom_data.json (步骤2)

**生成函数**: `GeminiAssemblyPipeline._step2_extract_bom_from_pdfs()`  
**文件位置**: `core/gemini_pipeline.py` 第271-331行  
**调用的AI**: Gemini Vision API  
**输入数据**: PDF文件（转换为base64图片）  
**处理逻辑**:
1. 将PDF每一页转换为base64图片
2. 构建BOM提取提示词（识别BOM表格）
3. 调用Gemini Vision API分析图片
4. 解析JSON响应，提取BOM项
5. 添加 `source_pdf` 字段标记来源

**提示词关键点**:
- 识别BOM表（必须有"代号"列，格式为XX.XX.XXXX）
- 提取字段：seq（序号）、code（代号）、name（名称）、quantity（数量）、weight（重量）
- 排除"工艺路线"表（只有2段代号）

**数据结构**:
```json
[
  {
    "seq": "1",
    "code": "01.01.01.10852",
    "product_code": "S-AB1830(72IN)-MP1140-01",
    "name": "方形板-机加",
    "quantity": 1,
    "weight": 76.42,
    "source_pdf": "组件图1.PDF"
  }
]
```

---

#### 4. step3_planning_result.json (步骤3)

**生成智能体**: Agent 1 - VisionPlanningAgent  
**文件位置**: `agents/vision_planning_agent.py`  
**提示词位置**: `prompts/agent_1_vision_planning.py`  
**输入数据**: 
- 所有PDF图片（产品总图 + 组件图）
- BOM数据（step2_bom_data.json）
- 期望的组件数量（从文件系统识别）

**处理逻辑**:
1. 调用 `build_simple_assembly_planning_prompt()` 构建提示词
2. 调用Gemini Vision API分析图纸
3. 识别组件装配顺序（基于重量、位置关系）
4. 为每个组件规划内部装配步骤

**数据结构**:
```json
{
  "success": true,
  "component_assembly_plan": [
    {
      "component_code": "01.03.4178",
      "component_name": "滚轮组件",
      "assembly_order": 1,
      "reason": "最重的组件，作为基准",
      "assembly_steps": [
        {
          "step": 1,
          "action": "放置基准件",
          "parts": ["方形板-机加"],
          "drawing_number": "①"
        }
      ]
    }
  ],
  "product_assembly_plan": {
    "base_component_code": "01.03.4178",
    "base_component_name": "滚轮组件",
    "assembly_sequence": [...]
  }
}
```

---

#### 5. step4_matching_result.json (步骤4)

**生成模块**: HierarchicalBOMMatcher  
**文件位置**: `core/hierarchical_bom_matcher_v2.py`  
**输入数据**:
- STEP文件目录
- BOM数据（step2_bom_data.json）
- 组件规划（step3_planning_result.json）
- 文件层级结构（step1_file_hierarchy.json）

**处理逻辑**:
1. **STEP → GLB转换**: 调用Blender将STEP文件转换为GLB
2. **提取3D模型信息**: 解析GLB文件，提取mesh节点名称
3. **BOM-3D匹配**: 使用AI匹配BOM代号和mesh节点名称
4. **生成映射表**: 创建 `seq → code → mesh_id` 的完整映射链

**调用的AI**: Gemini API (用于BOM-3D匹配)  
**提示词位置**: `core/bom_3d_matcher.py`

**数据结构**:
```json
{
  "success": true,
  "component_level_mappings": {
    "01.03.4178": {
      "drawing_index": 1,
      "glb_file": "component_1.glb",
      "bom_to_mesh": {
        "01.01.01.10852": "NAUO1"
      },
      "bom_mapping_table": [
        {
          "seq": "1",
          "code": "01.01.01.10852",
          "name": "方形板-机加",
          "mesh_id": "NAUO1"
        }
      ]
    }
  },
  "product_level_mapping": {...},
  "glb_files": {
    "component_1": "component_1.glb",
    "product_total": "product_total.glb"
  }
}
```

---

#### 6. step5_component_results.json (步骤5)

**生成智能体**: Agent 3 - ComponentAssemblyAgent
**文件位置**: `agents/component_assembly_agent.py`
**提示词位置**: `prompts/agent_3_component_assembly.py`
**输入数据**:
- 组件规划（step3_planning_result.json）
- 组件图片（step1_image_hierarchy.json）
- 组件BOM列表（从step2_bom_data.json筛选）
- BOM-3D映射（step4_matching_result.json）

**处理逻辑**:
1. 遍历每个组件
2. 调用 `build_component_assembly_prompt()` 构建提示词
3. 调用Gemini Vision API生成装配步骤
4. 使用BOM映射表添加 `mesh_id` 到每个零件
5. 检查BOM覆盖率（确保所有零件都被使用）

**数据结构**:
```json
[
  {
    "success": true,
    "component_code": "01.03.4178",
    "component_name": "滚轮组件",
    "assembly_order": 1,
    "drawing_index": 1,
    "assembly_steps": [
      {
        "step_id": "01.03.4178_step_1",
        "step_number": 1,
        "action": "放置基准件并安装侧板",
        "description": "将图纸上标注为①的方形板-机加...",
        "position_description": "②号侧板安装在①号方形板-机加的两侧",
        "parts_used": [
          {
            "bom_seq": "1",
            "bom_code": "01.01.01.10852",
            "bom_name": "方形板-机加",
            "quantity": 1,
            "drawing_number": "①",
            "node_name": ["NAUO1"]
          }
        ],
        "tools": ["焊接工装", "CO2焊机"],
        "warnings": ["侧板定位时，必须确保其与基准件的垂直度"]
      }
    ]
  }
]
```

---

#### 7. step6_product_result.json (步骤6)

**生成智能体**: Agent 4 - ProductAssemblyAgent
**文件位置**: `agents/product_assembly_agent.py`
**提示词位置**: `prompts/agent_4_product_assembly.py`
**输入数据**:
- 产品规划（step3_planning_result.json）
- 产品总图图片（step1_image_hierarchy.json）
- 组件列表（step3_planning_result.json）
- 产品级BOM（从step2_bom_data.json筛选）
- BOM-3D映射（step4_matching_result.json）

**处理逻辑**:
1. 调用 `build_product_assembly_prompt()` 构建提示词
2. 调用Gemini Vision API生成产品总装步骤
3. 使用BOM映射表添加 `mesh_id` 到每个零件
4. 检查BOM覆盖率（产品级允许80%，因为有很多标准件）

**数据结构**:
```json
{
  "success": true,
  "assembly_steps": [
    {
      "step_id": "product_step_1",
      "step_number": 1,
      "action": "安装基准组件",
      "description": "将滚轮组件作为基准...",
      "components_used": ["滚轮组件"],
      "parts_used": [...],
      "tools": ["吊装设备"],
      "warnings": ["确保组件水平放置"]
    }
  ]
}
```

---

#### 8. step7_enhanced_component_results.json & step7_enhanced_product_result.json (步骤7)

**生成智能体**: Agent 5 (WeldingAgent) + Agent 6 (SafetyFAQAgent)
**文件位置**:
- `agents/welding_agent.py`
- `agents/safety_faq_agent.py`

**提示词位置**:
- `prompts/agent_5_welding.py`
- `prompts/agent_6_safety_faq.py`

**输入数据**:
- 组件装配步骤（step5_component_results.json）
- 产品装配步骤（step6_product_result.json）
- 图片（step1_image_hierarchy.json）

**处理逻辑**:

**Agent 5 - 焊接工程师**:
1. 分析每个装配步骤
2. 识别涉及焊接的步骤
3. 为每个焊接步骤添加 `welding` 字段
4. 包含：焊接类型、焊缝尺寸、焊接位置、质量要求

**Agent 6 - 安全专员**:
1. 接收Agent 5增强后的步骤
2. 为每个步骤添加 `safety_warnings` 字段
3. 包含：安全注意事项、防护措施

**数据结构**:
```json
{
  "assembly_steps": [
    {
      "step_number": 1,
      "action": "放置基准件并安装侧板",
      "welding": {
        "required": true,
        "welding_type": "角焊（定位焊）",
        "welding_method": "CO2气保焊",
        "weld_size": "点焊长度10-15mm，焊脚高度3mm",
        "welding_position": "零件①与零件②的连接边缘",
        "quality_requirements": "点焊牢固，定位准确",
        "safety_notes": "佩戴焊接面罩和防护手套"
      },
      "safety_warnings": [
        "佩戴安全帽、防护眼镜和防割手套",
        "进行点焊作业时，必须佩戴焊接面罩",
        "确认CO2焊机接地良好"
      ]
    }
  ]
}
```

---

#### 9. assembly_manual.json (步骤8 - 最终输出)

**生成模块**: ManualIntegratorV2
**文件位置**: `core/manual_integrator_v2.py`
**输入数据**:
- 所有前面步骤的JSON文件
- 图片层级结构
- BOM-3D映射
- 任务ID

**处理逻辑**:
1. 整合元数据（产品名称、组件数量）
2. 整合组件装配步骤（从step7_enhanced_component_results.json）
3. 整合产品装配步骤（从step7_enhanced_product_result.json）
4. 提取焊接要求（从步骤内嵌的 `welding` 字段）
5. 提取安全警告（从步骤内嵌的 `safety_warnings` 字段）
6. 构建3D资源映射（GLB文件路径、BOM-mesh映射）

---

## 6个AI智能体详解

### 智能体架构

所有智能体都继承自 `BaseGeminiAgent` (agents/base_gemini_agent.py)，提供统一的AI调用接口。

**基础能力**:
- `call_gemini()`: 调用Gemini API（支持文本+图片）
- `call_gemini_with_retry()`: 带重试机制的调用（JSON解析失败时重试）
- 调试日志保存（debug_output/Agent{N}__timestamp.json）

---

### Agent 1: 视觉规划师 (VisionPlanningAgent)

**文件位置**: `agents/vision_planning_agent.py`
**提示词位置**: `prompts/agent_1_vision_planning.py`

#### 角色定位
资深的**装配工艺规划工程师**，15年装配工艺规划经验，专门负责分析工程图纸并制定装配工艺规划。

#### 核心能力
1. **工程图纸识读**: 识别主视图、俯视图、剖视图、BOM表
2. **装配顺序规划**: 基准件优先、由内到外、由下到上
3. **组件化装配思维**: 识别可预装配的组件单元
4. **质量与安全意识**: 识别关键工序、质量控制点

#### 输入数据
- **图片**: 所有PDF图片（产品总图 + 组件图1/2/3）
- **BOM数据**: 完整的BOM列表（step2_bom_data.json）
- **期望组件数量**: 从文件系统识别出的组件图数量

#### 处理流程
```python
# 1. 构建提示词
system_prompt, user_query = build_simple_assembly_planning_prompt(
    bom_data=bom_data,
    expected_component_count=expected_component_count
)

# 2. 调用Gemini Vision API
result = self.call_gemini(
    system_prompt=system_prompt,
    user_query=user_query,
    images=all_images  # 所有PDF图片
)
```

#### 提示词关键点 (prompts/agent_1_vision_planning.py)

**系统提示词** (ASSEMBLY_PLANNING_SYSTEM_PROMPT):
- 角色定位：装配工艺规划工程师
- 教育背景：机械工程硕士
- 职业背景：15年装配工艺规划经验
- 知识结构：工程图纸识读、装配工艺知识、组件化装配思维

**用户查询** (ASSEMBLY_PLANNING_USER_QUERY):
- 视觉分析任务：识别序号标注、观察空间位置关系
- 问题1：哪个组件先做？（基于重量、位置关系）
- 问题2：每个组件怎么做？（找出基准件、规划装配顺序）

**输出格式**:
```json
{
  "component_assembly_plan": [
    {
      "component_code": "01.03.4178",
      "component_name": "滚轮组件",
      "assembly_order": 1,
      "reason": "最重的组件，作为基准",
      "visual_analysis": "从图纸上观察到的关键信息",
      "assembly_steps": [...]
    }
  ],
  "product_assembly_plan": {
    "base_component_code": "01.03.4178",
    "assembly_sequence": [...]
  }
}
```

#### 调用时机
**步骤3**: 在BOM数据提取完成后，开始装配规划

---

### Agent 2: 3D模型工程师 (HierarchicalBOMMatcher)

**注意**: Agent 2不是传统的AI智能体，而是一个**混合处理模块**，结合了3D转换和AI匹配。

**文件位置**: `core/hierarchical_bom_matcher_v2.py`
**提示词位置**: `core/bom_3d_matcher.py` (match_bom_to_3d函数)

#### 核心能力
1. **STEP → GLB转换**: 调用Blender将STEP文件转换为GLB
2. **3D模型解析**: 提取GLB文件中的mesh节点名称
3. **BOM-3D匹配**: 使用AI匹配BOM代号和mesh节点名称

#### 输入数据
- **STEP文件目录**: 所有STEP文件
- **BOM数据**: 完整的BOM列表
- **组件规划**: Agent 1的规划结果
- **文件层级结构**: step1_file_hierarchy.json

#### 处理流程
```python
# 1. STEP → GLB转换
glb_file = self.model_processor.convert_step_to_glb(
    step_file=step_file,
    output_file=glb_file
)

# 2. 提取mesh节点名称
mesh_names = extract_glb_mesh_names(glb_file)

# 3. AI匹配BOM和mesh
matching_result = match_bom_to_3d(
    bom_items=component_bom,
    mesh_names=mesh_names,
    api_key=api_key
)
```

#### AI匹配提示词 (core/bom_3d_matcher.py)

**核心逻辑**:
- 输入：BOM列表（代号、名称）+ mesh节点名称列表
- 输出：BOM代号 → mesh_id 的映射表
- 匹配策略：基于名称相似度、代号规则

**输出格式**:
```json
{
  "bom_to_mesh": {
    "01.01.01.10852": "NAUO1",
    "01.01.01.10853": "NAUO2"
  },
  "bom_mapping_table": [
    {
      "seq": "1",
      "code": "01.01.01.10852",
      "name": "方形板-机加",
      "mesh_id": "NAUO1"
    }
  ]
}
```

#### 调用时机
**步骤4**: 在装配规划完成后，进行BOM-3D匹配

---

### Agent 3: 组件装配工程师 (ComponentAssemblyAgent)

**文件位置**: `agents/component_assembly_agent.py`
**提示词位置**: `prompts/agent_3_component_assembly.py`

#### 角色定位
资深的**组件装配工艺工程师**，专门负责编写组件内部的装配步骤。

#### 核心能力
1. **装配步骤生成**: 为每个组件生成详细的装配步骤
2. **BOM覆盖率检查**: 确保所有零件都被使用（95%覆盖率）
3. **重试机制**: 如果覆盖率不足，自动重试

#### 输入数据
- **组件规划**: Agent 1的组件规划
- **组件图片**: 组件图的PDF图片
- **组件BOM列表**: 从step2_bom_data.json筛选出的组件零件
- **BOM-3D映射**: Agent 2的匹配结果

#### 处理流程
```python
# 1. 构建提示词
system_prompt, user_query = build_component_assembly_prompt(
    component_plan=component_plan,
    parts_list=parts_list
)

# 2. 调用Gemini Vision API
result = self.call_gemini_with_retry(
    system_prompt=system_prompt,
    user_query=user_query,
    images=component_images,
    max_retries=3
)

# 3. 添加mesh_id
assembly_steps = self._add_mesh_ids_from_table(
    assembly_steps,
    bom_mapping_table
)

# 4. 检查BOM覆盖率
coverage_rate = self._check_bom_coverage(
    assembly_steps,
    parts_list
)
```

#### 提示词关键点 (prompts/agent_3_component_assembly.py)

**系统提示词**:
- 角色定位：组件装配工艺工程师
- 核心能力：装配步骤规划、工艺文件编写
- 输出格式：JSON（包含step_number、action、description、parts_used等）

**用户查询**:
- 组件信息：组件代号、名称、BOM列表
- 任务要求：生成3-5个装配步骤，确保100%覆盖所有BOM项

**输出格式**:
```json
{
  "assembly_steps": [
    {
      "step_number": 1,
      "action": "放置基准件",
      "description": "详细描述...",
      "parts_used": [
        {
          "bom_seq": "1",
          "bom_code": "01.01.01.10852",
          "bom_name": "方形板-机加",
          "quantity": 1,
          "drawing_number": "①"
        }
      ],
      "tools": ["焊接工装"],
      "warnings": ["注意事项"]
    }
  ]
}
```

#### 调用时机
**步骤5**: 在BOM-3D匹配完成后，为每个组件生成装配步骤

---

### Agent 4: 产品总装工程师 (ProductAssemblyAgent)

**文件位置**: `agents/product_assembly_agent.py`
**提示词位置**: `prompts/agent_4_product_assembly.py`

#### 角色定位
资深的**产品总装工艺工程师**，专门负责编写产品总装步骤（组件之间的装配）。

#### 核心能力
1. **总装步骤生成**: 生成组件之间的装配步骤
2. **BOM覆盖率检查**: 确保主要零件都被使用（80%覆盖率，因为有很多标准件）
3. **重试机制**: 如果覆盖率不足，自动重试

#### 输入数据
- **产品规划**: Agent 1的产品规划
- **产品总图图片**: 产品总图的PDF图片
- **组件列表**: Agent 1识别出的组件列表
- **产品级BOM**: 从step2_bom_data.json筛选出的产品级零件
- **BOM-3D映射**: Agent 2的匹配结果

#### 处理流程
```python
# 1. 构建提示词
system_prompt, user_query = build_product_assembly_prompt(
    product_plan=product_plan,
    components_list=components_list,
    product_bom=product_bom
)

# 2. 调用Gemini Vision API
result = self.call_gemini_with_retry(
    system_prompt=system_prompt,
    user_query=user_query,
    images=product_images,
    max_retries=3
)

# 3. 添加mesh_id
assembly_steps = self._add_mesh_ids_from_table(
    assembly_steps,
    bom_mapping_table
)
```

#### 提示词关键点 (prompts/agent_4_product_assembly.py)

**系统提示词**:
- 角色定位：产品总装工艺工程师
- 核心能力：总装步骤规划、组件装配顺序
- 输出格式：JSON（包含step_number、action、components_used、parts_used等）

**用户查询**:
- 产品信息：产品名称、组件列表、产品级BOM
- 任务要求：生成3-5个总装步骤，说明组件之间的装配关系

**输出格式**:
```json
{
  "assembly_steps": [
    {
      "step_number": 1,
      "action": "安装基准组件",
      "description": "详细描述...",
      "components_used": ["滚轮组件"],
      "parts_used": [...],
      "tools": ["吊装设备"],
      "warnings": ["注意事项"]
    }
  ]
}
```

#### 调用时机
**步骤6**: 在组件装配步骤生成完成后，生成产品总装步骤

---

### Agent 5: 焊接工程师 (WeldingAgent)

**文件位置**: `agents/welding_agent.py`
**提示词位置**: `prompts/agent_5_welding.py`

#### 角色定位
资深的**焊接工艺工程师**，专门负责为装配步骤添加焊接工艺要点。

#### 核心能力
1. **焊接步骤识别**: 识别哪些装配步骤涉及焊接
2. **焊接工艺规划**: 确定焊接类型、焊缝尺寸、焊接位置
3. **质量要求制定**: 制定焊接质量要求和检验标准

#### 输入数据
- **装配步骤**: Agent 3或Agent 4生成的装配步骤
- **图片**: 组件图或产品总图的PDF图片

#### 处理流程
```python
# 1. 构建提示词
system_prompt, user_query = build_welding_prompt(
    assembly_steps=assembly_steps
)

# 2. 调用Gemini Vision API
result = self.call_gemini(
    system_prompt=system_prompt,
    user_query=user_query,
    images=all_images
)

# 3. 返回增强后的步骤（包含welding字段）
enhanced_steps = result["result"]["enhanced_steps"]
```

#### 提示词关键点 (prompts/agent_5_welding.py)

**系统提示词**:
- 角色定位：焊接工艺工程师
- 教育背景：焊接技术与工程硕士
- 职业背景：20年焊接工艺规划经验
- 核心能力：焊接接头设计、焊接工艺规划、焊接质量控制

**任务步骤** (Chain of Thought):
1. **识别焊接步骤**: 判断是否涉及零件的永久性连接
2. **确定焊接类型**: 对接、角焊、塞焊等
3. **分析焊接位置**: 平焊、横焊、立焊、仰焊
4. **制定焊接工艺**: 焊接参数、焊接顺序、质量要求
5. **添加安全提示**: 焊接安全注意事项

**输出格式**:
```json
{
  "enhanced_steps": [
    {
      "step_number": 1,
      "action": "放置基准件并安装侧板",
      "welding": {
        "required": true,
        "welding_type": "角焊（定位焊）",
        "welding_method": "CO2气保焊",
        "weld_size": "点焊长度10-15mm，焊脚高度3mm",
        "welding_position": "零件①与零件②的连接边缘",
        "quality_requirements": "点焊牢固，定位准确",
        "safety_notes": "佩戴焊接面罩和防护手套"
      }
    }
  ]
}
```

#### 调用时机
**步骤7**: 在组件装配和产品总装步骤生成完成后，为每个步骤添加焊接要点

---

### Agent 6: 安全专员 (SafetyFAQAgent)

**文件位置**: `agents/safety_faq_agent.py`
**提示词位置**: `prompts/agent_6_safety_faq.py`

#### 角色定位
资深的**安全工程师**，专门负责为装配步骤添加安全警告和FAQ。

#### 核心能力
1. **安全风险识别**: 识别每个装配步骤的安全风险
2. **安全警告生成**: 为每个步骤生成具体的安全警告
3. **FAQ生成**: 生成常见问题和解答

#### 输入数据
- **装配步骤**: Agent 5增强后的装配步骤（已包含焊接信息）

#### 处理流程
```python
# 1. 构建提示词
system_prompt, user_query = build_safety_faq_prompt(
    assembly_steps=assembly_steps
)

# 2. 调用Gemini API（不需要图片）
result = self.call_gemini(
    system_prompt=system_prompt,
    user_query=user_query,
    images=None
)

# 3. 返回增强后的步骤（包含safety_warnings字段）
enhanced_steps = result["result"]["enhanced_steps"]
```

#### 提示词关键点 (prompts/agent_6_safety_faq.py)

**系统提示词**:
- 角色定位：安全工程师
- 教育背景：安全工程硕士
- 职业背景：15年装配安全管理经验
- 核心能力：安全风险评估、安全措施制定、应急预案编制

**任务步骤** (Chain of Thought):
1. **识别安全风险**: 分析每个步骤的潜在危险
2. **制定安全措施**: 针对每个风险制定防护措施
3. **添加安全警告**: 为每个步骤添加具体的安全警告
4. **生成FAQ**: 整理常见安全问题和解答

**输出格式**:
```json
{
  "enhanced_steps": [
    {
      "step_number": 1,
      "action": "放置基准件并安装侧板",
      "safety_warnings": [
        "佩戴安全帽、防护眼镜和防割手套",
        "进行点焊作业时，必须佩戴焊接面罩",
        "确认CO2焊机接地良好"
      ]
    }
  ],
  "faq_items": [
    {
      "question": "焊接时如何防止弧光伤害？",
      "answer": "必须佩戴焊接面罩，使用符合标准的滤光片..."
    }
  ]
}
```

#### 调用时机
**步骤7**: 在Agent 5添加焊接要点后，为每个步骤添加安全警告

---

## 数据流向图

### 完整数据流向

```
用户上传文件 (PDF + STEP)
    ↓
uploads/ 目录
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤1: 文件分类 + PDF转图片                                    │
│ 模块: FileClassifier                                         │
│ 输入: PDF文件列表 + STEP文件列表                               │
│ 输出: step1_file_hierarchy.json + step1_image_hierarchy.json │
│       pdf_images/ (PNG图片)                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤2: BOM数据提取                                            │
│ AI: Gemini Vision API                                        │
│ 输入: PDF图片 (base64)                                        │
│ 输出: step2_bom_data.json                                    │
│       [{"seq":"1", "code":"01.01.01.10852", "name":"..."}]   │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤3: Agent 1 - 视觉规划                                     │
│ 智能体: VisionPlanningAgent                                  │
│ 提示词: prompts/agent_1_vision_planning.py                   │
│ 输入: 所有PDF图片 + BOM数据 + 期望组件数量                      │
│ 输出: step3_planning_result.json                             │
│       {component_assembly_plan: [...], product_assembly_plan: {...}} │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤4: Agent 2 - BOM-3D匹配                                   │
│ 模块: HierarchicalBOMMatcher                                 │
│ 3D转换: Blender (STEP → GLB)                                 │
│ AI匹配: Gemini API (BOM代号 → mesh_id)                        │
│ 输入: STEP文件 + BOM数据 + 组件规划                            │
│ 输出: step4_matching_result.json + glb_files/                │
│       {component_level_mappings: {...}, product_level_mapping: {...}} │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤5: Agent 3 - 组件装配                                     │
│ 智能体: ComponentAssemblyAgent                               │
│ 提示词: prompts/agent_3_component_assembly.py                │
│ 输入: 组件规划 + 组件图片 + 组件BOM + BOM-3D映射               │
│ 输出: step5_component_results.json                           │
│       [{component_code: "...", assembly_steps: [...]}]       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤6: Agent 4 - 产品总装                                     │
│ 智能体: ProductAssemblyAgent                                 │
│ 提示词: prompts/agent_4_product_assembly.py                  │
│ 输入: 产品规划 + 产品总图图片 + 组件列表 + 产品BOM + BOM-3D映射 │
│ 输出: step6_product_result.json                              │
│       {assembly_steps: [...]}                                │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤7: Agent 5 & 6 - 焊接 + 安全                              │
│ 智能体: WeldingAgent + SafetyFAQAgent                        │
│ 提示词: prompts/agent_5_welding.py + prompts/agent_6_safety_faq.py │
│ 输入: 组件装配步骤 + 产品装配步骤 + 图片                        │
│ 输出: step7_enhanced_component_results.json                  │
│       step7_enhanced_product_result.json                     │
│       (步骤中包含welding和safety_warnings字段)                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤8: 整合最终手册                                           │
│ 模块: ManualIntegratorV2                                     │
│ 输入: 所有前面步骤的JSON + 图片层级 + BOM-3D映射 + 任务ID      │
│ 输出: assembly_manual.json (最终装配说明书)                   │
│       {metadata: {...}, component_assembly: [...],           │
│        product_assembly: {...}, welding_requirements: [...], │
│        safety_and_faq: {...}, 3d_resources: {...}}           │
└─────────────────────────────────────────────────────────────┘
    ↓
前端展示 (ManualViewer.vue)
```

---

### 焊接数据流向（重点）

**数据结构双轨制**:

1. **步骤内嵌的 `welding` 字段** (正确的设计，符合API文档)
   - 位置：`assembly_steps[i].welding`
   - 来源：Agent 5直接添加到步骤中
   - 优先级：**高**（前端优先读取）

2. **全局的 `welding_requirements` 数组** (兼容旧数据)
   - 位置：`assembly_manual.welding_requirements`
   - 来源：ManualIntegratorV2从步骤中提取
   - 优先级：**低**（仅用于兼容旧数据）

**前端读取逻辑** (v1.1.5修复后):
```javascript
// 优先从步骤内嵌字段读取
const currentStepWeldingRequirements = computed(() => {
  if (currentStep.value?.welding?.required) {
    // 优先使用步骤内嵌的welding字段
    return [currentStep.value.welding];
  } else {
    // 兼容旧数据：从全局数组读取
    return manualData.value.welding_requirements.filter(
      w => w.step_number === currentStepNumber.value &&
           w.component === currentComponentName.value
    );
  }
});
```

**保存逻辑** (双重保存机制):
```javascript
// 1. 主要保存：更新步骤内嵌的welding字段
currentStep.value.welding = {
  required: true,
  welding_type: editData.welding_type,
  weld_size: editData.weld_size,
  welding_position: editData.welding_position
};

// 2. 兼容保存：同时更新全局数组
manualData.value.welding_requirements.push({
  step_number: currentStepNumber.value,
  component: currentComponentName.value,
  welding_type: editData.welding_type,
  weld_size: editData.weld_size,
  welding_position: editData.welding_position
});
```

---

## 总结

### 核心流程

1. **文件上传** → uploads/
2. **文件分类** → 识别产品总图和组件图
3. **PDF转图片** → pdf_images/
4. **BOM提取** → 使用Gemini Vision API从图纸中提取零件清单
5. **装配规划** → Agent 1分析图纸，规划装配顺序
6. **3D转换** → Blender将STEP转换为GLB
7. **BOM-3D匹配** → AI匹配BOM代号和3D模型节点
8. **组件装配** → Agent 3生成组件内部装配步骤
9. **产品总装** → Agent 4生成组件之间的装配步骤
10. **焊接增强** → Agent 5添加焊接工艺要点
11. **安全增强** → Agent 6添加安全警告
12. **手册整合** → 整合所有数据生成最终JSON

### 6个智能体总览

| 智能体 | 角色 | 输入 | 输出 | 提示词位置 |
|--------|------|------|------|-----------|
| Agent 1 | 视觉规划师 | PDF图片 + BOM数据 | 装配规划 | prompts/agent_1_vision_planning.py |
| Agent 2 | 3D模型工程师 | STEP文件 + BOM数据 | GLB文件 + BOM-3D映射 | core/bom_3d_matcher.py |
| Agent 3 | 组件装配工程师 | 组件规划 + 组件图片 + 组件BOM | 组件装配步骤 | prompts/agent_3_component_assembly.py |
| Agent 4 | 产品总装工程师 | 产品规划 + 产品总图 + 组件列表 | 产品总装步骤 | prompts/agent_4_product_assembly.py |
| Agent 5 | 焊接工程师 | 装配步骤 + 图片 | 增强后的步骤（含焊接） | prompts/agent_5_welding.py |
| Agent 6 | 安全专员 | 装配步骤（含焊接） | 增强后的步骤（含安全） | prompts/agent_6_safety_faq.py |

### 关键文件

- **核心流程**: `core/gemini_pipeline.py` (991行)
- **文件分类**: `core/file_classifier.py` (306行)
- **BOM-3D匹配**: `core/hierarchical_bom_matcher_v2.py` (522行)
- **手册整合**: `core/manual_integrator_v2.py` (511行)
- **6个智能体**: `agents/` 目录
- **6个提示词**: `prompts/` 目录

---

**文档版本**: 1.0
**创建日期**: 2025-11-11
**作者**: AI Assistant
**用途**: 帮助开发者理解系统完整工作流程

