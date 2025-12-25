# 🤖 当前AI匹配逻辑全解析

> **文档目的**：详细说明上传产品图/组件图后，AI如何进行BOM-3D匹配的完整流程
> **更新时间**：2025-12-09
> **适用版本**：v2.0.32+

---

## 📋 目录

0. [**核心术语解释（必读）**](#0️⃣-核心术语解释必读) ⭐⭐⭐
1. [整体流程概览](#整体流程概览)
2. [文件上传与分类](#文件上传与分类)
3. [BOM提取](#bom提取)
4. [3D模型处理](#3d模型处理)
5. [AI匹配核心逻辑](#ai匹配核心逻辑)
6. [匹配结果应用](#匹配结果应用)
7. [关键代码位置](#关键代码位置)

---

## 0️⃣ 核心术语解释（必读）⭐⭐⭐

> **为什么要先读这个**：后面的内容会大量使用这些术语，先理解术语才能看懂流程

### 术语1：product_code（产品代号）

**是什么**：零件的唯一标识符，类似于零件的"身份证号"

**从哪里来**：
1. **来源1：BOM表（PDF图纸）**
   - Gemini AI从PDF图纸中识别BOM表时提取
   - 对应BOM表中的"产品代号"列
   - 例如：`JXG-T6×100×50-970-Q355B`

2. **来源2：STEP文件（3D模型）**
   - STEP文件中的PRODUCT实体包含零件名称
   - 零件名称通常包含产品代号
   - 例如：`JXG-T6×100×50-970-Q355B矩形管`

**为什么重要**：
- product_code是**最可靠的匹配依据**（置信度0.90-0.98）
- 用于将BOM表中的零件和3D模型中的零件对应起来

**示例**：
```
BOM表（从PDF识别）：
序号 | 代号 | 名称   | 产品代号
1    | 01   | 矩形管 | JXG-T6×100×50-970-Q355B

STEP文件（3D模型）：
#123 = PRODUCT('JXG-T6×100×50-970-Q355B矩形管', ...)

匹配逻辑：
BOM的product_code（JXG-T6×100×50-970-Q355B）
包含在
STEP的零件名称（JXG-T6×100×50-970-Q355B矩形管）中
→ 匹配成功！置信度0.95
```

---

### 术语2：node_name（节点名称）

**是什么**：3D模型中每个零件的唯一标识符，类似于零件在3D模型中的"座位号"

**从哪里来**：
- STEP文件转换为GLB时自动生成
- 格式：`NAUO1`、`NAUO2`、`NAUO3`...
- NAUO = Next Assembly Usage Occurrence（装配使用实例）

**为什么重要**：
- 前端3D查看器通过node_name来高亮零件
- 装配步骤中的"高亮零件"功能依赖node_name

**示例**：
```
GLB文件中的零件列表：
node_name | geometry_name（包含产品代号）
NAUO1     | JXG-T6×100×50-970-Q355B矩形管
NAUO2     | JXG-T6×100×50-335-Q355B矩形管
NAUO3     | M8螺栓

前端高亮指令：
highlightParts(["NAUO1", "NAUO2"])
→ 高亮矩形管970和矩形管335
```

---

### 术语3：装配体 vs 叶子零件

**装配体（Assembly）**：
- 由多个零件组成的组件
- 在BOM表中是一个条目，但在3D模型中是多个零件
- 例如："挂架组件"包含3个零件（矩形管970、矩形管335、M8螺栓）

**叶子零件（Leaf Part）**：
- 不能再拆分的最小单元
- 在3D模型中是一个独立的几何体
- 例如："矩形管970"是一个叶子零件

**对比表格**：

| 特性 | 装配体 | 叶子零件 |
|------|--------|----------|
| **定义** | 由多个零件组成 | 不能再拆分 |
| **BOM表** | 1个条目 | 1个条目 |
| **3D模型** | 多个node_name | 1个node_name |
| **例子** | 挂架组件 | 矩形管970 |
| **能否高亮** | ❌ 不能直接高亮 | ✅ 可以直接高亮 |

**为什么需要区分**：
- 装配体在3D模型中不是一个独立的几何体，无法直接高亮
- 需要找到装配体包含的所有叶子零件，然后高亮这些叶子零件

**实际例子**：
```
BOM表：
序号 | 代号        | 名称     | 数量
3    | 01.03.0281  | 挂架组件 | 1

3D模型中的实际零件：
NAUO25 | 矩形管970
NAUO26 | 矩形管335
NAUO27 | M8螺栓

问题：
装配步骤说"安装挂架组件"，但3D模型中没有"挂架组件"这个几何体

解决方案：
通过层级结构找到"挂架组件"包含的所有叶子零件（NAUO25、NAUO26、NAUO27）
然后高亮这3个零件
```

---

### 术语4：层级结构（Hierarchy）

**是什么**：描述零件之间的"包含关系"，类似于文件夹的树形结构

**示例（树形图）**：
```
产品总装
├─ 挂架组件（装配体）
│   ├─ 矩形管970（叶子零件）
│   ├─ 矩形管335（叶子零件）
│   └─ M8螺栓（叶子零件）
├─ 连接器组件（装配体）
│   ├─ 轴套（叶子零件）
│   └─ M12螺栓（叶子零件）
└─ 固定座（叶子零件）
```

**用JSON表示**：
```json
{
  "产品总装": ["挂架组件", "连接器组件", "固定座"],
  "挂架组件": ["矩形管970", "矩形管335", "M8螺栓"],
  "连接器组件": ["轴套", "M12螺栓"]
}
```

**从哪里来**：
- 从STEP文件中解析出来（`parse_step_hierarchy()`函数）
- STEP文件中的NAUO实体记录了父子关系
- 保存到：`output/{task_id}/step_assembly_hierarchy.json`

---

### 术语5：DFS深度优先搜索（用人话解释）

**是什么**：一种遍历树形结构的方法，类似于"一条路走到黑"

**用文件夹类比**：
```
假设你要找"挂架组件"文件夹下的所有文件：

方法1：广度优先（BFS）
1. 先看第一层：挂架组件
2. 再看第二层：矩形管970、矩形管335、M8螺栓
3. 如果还有第三层，继续看第三层

方法2：深度优先（DFS）⭐ 我们用的方法
1. 进入"挂架组件"
2. 看到"矩形管970"，是文件（叶子），记录下来
3. 看到"矩形管335"，是文件（叶子），记录下来
4. 看到"M8螺栓"，是文件（叶子），记录下来
5. 完成！
```

**实际例子（收集叶子零件）**：
```
输入：
层级结构 = {
    "挂架组件": ["矩形管970", "矩形管335", "M8螺栓"]
}
起点 = "挂架组件"

执行过程：
1. 进入"挂架组件"
2. 看到"矩形管970"，检查它是否还有子节点
   → 没有子节点 → 这是叶子零件 → 记录
3. 看到"矩形管335"，检查它是否还有子节点
   → 没有子节点 → 这是叶子零件 → 记录
4. 看到"M8螺栓"，检查它是否还有子节点
   → 没有子节点 → 这是叶子零件 → 记录

输出：
["矩形管970", "矩形管335", "M8螺栓"]
```

**复杂例子（多层嵌套）**：
```
输入：
层级结构 = {
    "产品总装": ["挂架组件", "固定座"],
    "挂架组件": ["矩形管970", "螺栓组件"],
    "螺栓组件": ["M8螺栓", "垫圈"]
}
起点 = "产品总装"

执行过程：
1. 进入"产品总装"
2. 看到"挂架组件"，检查它是否还有子节点
   → 有子节点 → 这是装配体 → 递归进入
   2.1 进入"挂架组件"
   2.2 看到"矩形管970" → 叶子零件 → 记录
   2.3 看到"螺栓组件" → 有子节点 → 递归进入
       2.3.1 进入"螺栓组件"
       2.3.2 看到"M8螺栓" → 叶子零件 → 记录
       2.3.3 看到"垫圈" → 叶子零件 → 记录
3. 看到"固定座" → 叶子零件 → 记录

输出：
["矩形管970", "M8螺栓", "垫圈", "固定座"]
```

---

### 术语6：映射（Mapping）

**是什么**：建立两个东西之间的对应关系，类似于"通讯录"

**示例**：
```
BOM代号 → node_name 的映射：
{
  "01": ["NAUO1"],           # BOM代号01对应3D模型中的NAUO1
  "02": ["NAUO2", "NAUO3"],  # BOM代号02对应NAUO2和NAUO3（数量=2）
  "03": ["NAUO4"]
}

装配体 → 叶子零件 的映射：
{
  "01.03.0281": ["NAUO25", "NAUO26", "NAUO27"]  # 挂架组件对应3个叶子零件
}
```

**为什么需要映射**：
- BOM表用的是"代号"（如"01"）
- 3D模型用的是"node_name"（如"NAUO1"）
- 需要建立映射关系，才能在装配步骤中高亮正确的零件

**完整流程示例**：
```
1. BOM表：
   代号="01.03.0281", 名称="挂架组件"

2. 通过映射查找node_name：
   mapping["01.03.0281"] = ["NAUO25", "NAUO26", "NAUO27"]

3. 前端高亮指令：
   highlightParts(["NAUO25", "NAUO26", "NAUO27"])

4. 效果：
   3D模型中同时高亮矩形管970、矩形管335、M8螺栓
```

---

## 1️⃣ 整体流程概览

```
用户上传PDF+STEP文件
    ↓
文件分类（产品图 vs 组件图）
    ↓
PDF转图片 → BOM提取（Gemini视觉识别）
    ↓
STEP转GLB → 提取3D零件列表
    ↓
【核心】BOM-3D匹配（代码匹配已禁用 → 全部AI匹配）
    ↓
生成装配步骤 → 整合HTML手册
```

---

## 2️⃣ 文件上传与分类

### 2.1 前端上传
**文件**: `frontend/src/api/index.ts`

```typescript
// 用户上传PDF和STEP文件
async uploadFiles(pdfFiles: File[], modelFiles: File[]) {
  const formData = new FormData()
  pdfFiles.forEach(file => formData.append('pdf_files', file))
  modelFiles.forEach(file => formData.append('model_files', file))
  return api.post('/upload', formData)
}
```

### 2.2 后端接收
**文件**: `backend/simple_app.py`

- 接收文件并保存到 `uploads/` 目录
- 以PDF文件名作为 `task_id`
- 校验STEP文件名是否与PDF匹配

### 2.3 文件分类
**文件**: `core/file_classifier.py` → `classify_files()`

**分类规则**（按优先级）：
1. **前缀判定**（最高优先级）
   - `01*` → 组件图
   - `03*/06*/07*/08*` → 产品图
2. **关键字判定**
   - 含"组件" → 组件图
   - 其他 → 产品图

**分类结果**：
```json
{
  "product": {
    "pdf": "产品总图.pdf",
    "step": "产品总图.step",
    "product_code": ""
  },
  "components": [
    {
      "index": 1,
      "name": "组件图1",
      "bom_code": "",
      "pdf": "组件图1.pdf",
      "step": "组件图1.step"
    }
  ]
}
```

---

## 3️⃣ BOM提取

### 3.1 PDF转图片
**文件**: `core/file_classifier.py` → `convert_pdfs_to_images()`

- 使用 `PyMuPDF (fitz)` 库
- DPI: 200（平衡速度和质量）
- 输出: `output/{task_id}/pdf_images/product/page_001.png`

### 3.2 Gemini视觉识别BOM
**文件**: `models/gemini_model.py` → `extract_bom_from_images()`

**AI模型**: `google/gemini-2.5-flash-preview-09-2025`

**提取字段**：
- `seq`: 序号
- `code`: BOM代号（如 `01.09.2549`）
- `name`: 零件名称
- `product_code`: 产品代号（如 `T-SPV250-Z602-01-01-Q355B`）⭐ **关键字段**
- `spec`: 规格
- `material`: 材料
- `quantity`: 数量
- `source_pdf`: 来源PDF文件名

---

## 4️⃣ 3D模型处理

### 4.1 STEP转GLB
**文件**: `processors/step_to_glb_converter.py`

- 使用 `pythonocc-core` 解析STEP文件
- 提取装配层级结构
- 转换为GLB格式（WebGL可加载）

### 4.2 提取零件列表
**输出格式**：
```json
{
  "parts_info": [
    {
      "node_name": "NAUO1",
      "geometry_name": "JXG-T6×100×50-970-Q355B矩形管",
      "bounding_box": {...}
    }
  ]
}
```

**⚠️ 关键认知**：
- `geometry_name` 包含的是**产品代号**（`product_code`），不是BOM代号！
- 例如：`JXG-T6×100×50-970-Q355B` 是产品代号，对应BOM表中的 `product_code` 字段

---

## 5️⃣ AI匹配核心逻辑 ⭐

### 5.1 产品图 vs 组件图的处理策略差异

**关键区别**：产品图有**装配层级结构**，组件图没有

| 特性 | 组件图 | 产品图 |
|------|--------|--------|
| **STEP文件** | 单个组件的零件 | 完整产品（包含多个子装配体） |
| **装配层级** | ❌ 无层级（扁平结构） | ✅ 有层级（树形结构） |
| **BOM范围** | 仅组件内部零件 | 所有零件+组件 |
| **匹配策略** | AI匹配零件 | AI匹配零件 + 子装配体层级匹配 |
| **GLB命名** | `component_{index}.glb` | `product_total.glb` |
| **层级文件** | ❌ 不生成 | ✅ `step_assembly_hierarchy.json` |

---

### 5.2 组件级匹配流程

**文件**: `core/hierarchical_bom_matcher_v2.py` (行72-299)

```
组件级匹配（每个组件图）
├─ 步骤1：查找组件STEP文件
│   ├─ 优先使用 file_hierarchy 中的真实路径
│   └─ 回退：尝试 "组件图{index}.STEP" 等命名
│
├─ 步骤2：STEP转GLB
│   ├─ 输出：component_{index}.glb
│   └─ 提取：parts_list（所有3D零件）
│
├─ 步骤3：获取组件BOM
│   ├─ 根据 source_pdf 过滤（如 "组件图1.pdf"）
│   └─ 只包含组件内部的零件
│
├─ 步骤4：AI匹配（全部零件）✅
│   ├─ 输入：所有3D零件 + 组件BOM
│   ├─ 方法：调用 AIBOMMatcher (Gemini 2.5 Flash)
│   └─ 输出：ai_bom_to_mesh（BOM代号 → node_name列表）
│
├─ 步骤5：生成BOM映射宽表
│   └─ 包含完整的映射链条（bom_code → mesh_id → node_name）
│
└─ 步骤6：生成爆炸视图数据
    └─ 输出：manifest_component_{index}.json
```

**关键代码**：
```python
# 获取组件BOM（只包含组件内部的零件）
component_bom = self._get_component_bom(bom_data, comp_plan, file_index)

# 根据source_pdf过滤
possible_names = {
    f"组件图{drawing_index}.pdf",
    f"组件{drawing_index}.pdf"
}
for bom_item in bom_data:
    if bom_item.get("source_pdf") in possible_names:
        component_bom.append(bom_item)
```

---

### 5.3 产品级匹配流程 ⭐⭐⭐

**文件**: `core/hierarchical_bom_matcher_v2.py` (行302-514)

```
产品级匹配（产品总图）
├─ 步骤1：查找产品STEP文件
│   ├─ 优先使用 file_hierarchy 中的真实路径
│   └─ 回退：尝试 "产品总图.STEP" 等命名
│
├─ 步骤2：STEP转GLB
│   ├─ 输出：product_total.glb
│   └─ 提取：parts_list（所有3D零件，包括子装配体的零件）
│
├─ 步骤3：解析STEP装配层级 ⭐⭐⭐
│   ├─ 调用：parse_step_hierarchy(product_step)
│   ├─ 提取：PRODUCT、PRODUCT_DEFINITION、NAUO等实体
│   ├─ 建立：父子关系映射（hierarchy）
│   └─ 输出：step_assembly_hierarchy.json
│
├─ 步骤4：获取产品BOM
│   ├─ 根据 source_pdf 过滤（如 "产品总图.pdf"）
│   └─ 包含所有零件+组件（不排除组件）
│
├─ 步骤5：AI匹配（全部零件）✅
│   ├─ 输入：所有3D零件 + 产品BOM
│   ├─ 方法：调用 AIBOMMatcher (Gemini 2.5 Flash)
│   └─ 输出：ai_bom_to_mesh（BOM代号 → node_name列表）
│
├─ 步骤6：子装配体层级匹配 ⭐⭐⭐
│   ├─ 输入：hierarchy + product_bom + cleaned_parts
│   ├─ 方法：_build_assembly_mesh_mapping()
│   ├─ 逻辑：将子装配体（BOM项）映射到其所有叶子零件
│   └─ 输出：assembly_to_mesh（子装配体BOM代号 → 叶子零件node_name列表）
│
├─ 步骤7：合并结果
│   └─ final_bom_to_mesh = ai_bom_to_mesh + assembly_to_mesh
│
├─ 步骤8：生成BOM映射宽表
│   └─ 包含完整的映射链条
│
└─ 步骤9：生成爆炸视图数据
    └─ 输出：manifest_product.json
```

---

### 5.4 STEP装配层级解析详解 ⭐⭐⭐

**文件**: `core/step_hierarchy_parser.py`

#### 5.4.1 STEP文件结构

STEP文件包含以下关键实体：

1. **PRODUCT**：零件/组件的名称定义
   ```
   #123 = PRODUCT('JXG-T6×100×50-970-Q355B矩形管', ...)
   ```

2. **PRODUCT_DEFINITION_FORMATION**：产品定义形式
   ```
   #456 = PRODUCT_DEFINITION_FORMATION('', '', #123)
   ```

3. **PRODUCT_DEFINITION**：产品定义
   ```
   #789 = PRODUCT_DEFINITION('', '', #456, ...)
   ```

4. **NEXT_ASSEMBLY_USAGE_OCCURRENCE (NAUO)**：装配关系
   ```
   #999 = NEXT_ASSEMBLY_USAGE_OCCURRENCE('NAUO1', '', '', #parent_pd, #child_pd)
   ```

#### 5.4.2 解析流程

```python
def parse_step_hierarchy(step_file_path: str) -> Dict:
    # 1. 提取所有PRODUCT（零件名称）
    products = {}  # {product_id: product_name}

    # 2. 提取PRODUCT_DEFINITION_FORMATION
    pdfs = {}  # {pdf_id: product_id}

    # 3. 提取PRODUCT_DEFINITION
    prod_defs = {}  # {pd_id: pdf_id}

    # 4. 建立映射：pd_id -> product_name
    pd_to_name = {}
    for pd_id, pdf_id in prod_defs.items():
        product_id = pdfs.get(pdf_id)
        if product_id in products:
            pd_to_name[pd_id] = products[product_id]

    # 5. 提取NAUO（装配关系）
    nauos = []
    for match in re.finditer(NAUO_PATTERN, content):
        nauos.append({
            "parent_pd": parent_pd,
            "child_pd": child_pd,
            "parent_name": pd_to_name.get(parent_pd),
            "child_name": pd_to_name.get(child_pd)
        })

    # 6. 建立层级结构（父子关系）
    hierarchy = {}  # {parent_name: [child_names]}
    for nauo in nauos:
        hierarchy[nauo["parent_name"]].append(nauo["child_name"])

    return {"hierarchy": hierarchy, "stats": {...}}
```

#### 5.4.3 层级结构示例

```json
{
  "hierarchy": {
    "产品总装": [
      "挂架组件",
      "连接器组件",
      "固定座组件"
    ],
    "挂架组件": [
      "JXG-T6×100×50-970-Q355B矩形管",
      "JXG-T6×100×50-335-Q355B矩形管",
      "M8螺栓"
    ],
    "连接器组件": [
      "E-KP410GP300-VIO27-KP-09-45#轴套",
      "M12螺栓"
    ]
  },
  "stats": {
    "total_products": 50,
    "total_nauos": 120,
    "total_assemblies": 5
  }
}
```

---

### 5.5 【技术实现】子装配体层级匹配详解 ⭐⭐⭐

> **本节面向技术人员**：包含实际代码、文件路径、函数调用链、数据流向
>
> **实际案例**：`03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）`

---

#### 5.5.0 真实案例数据预览

**项目目录结构**：
```
output/03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）/
├── step_files/
│   └── 03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.step  # 产品STEP文件
├── pdf_files/
│   └── 03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.pdf   # 产品PDF图纸
├── glb_files/
│   └── product_total.glb                                              # 转换后的GLB文件
├── step_assembly_hierarchy.json  ⭐ # 层级结构文件（本节重点）
├── step2_bom_data.json            # BOM数据
└── step4_matching_result.json     # 匹配结果
```

**step_assembly_hierarchy.json 文件内容（部分）**：
```json
{
  "hierarchy": {
    "S-AB1830(72IN)-MP1140滑移清扫器（斜角型）": [
      "H-AB1830(72IN)-Manitou-05主框架组件",
      "S-AB1830(72IN)-MP1140-01挂架组件",
      "T-AB1830(72IN)-EURO-02毛刷套组件",
      "S-RB1830-05毛刷固定板组",
      "BMR250液压马达(4安装孔)",
      "MS-φ162-φ550-黄色PP+钢丝-圆形毛刷盘",
      "GB／T 5783-2016六角头螺栓全螺纹 C级M14×70",
      ...
    ],
    "H-AB1830(72IN)-Manitou-05主框架组件": [
      "H-AB1830(72IN)-Manitou-01左侧板组件",
      "H-AB1830(72IN)-Manitou-02右侧板组件",
      "H-AB1830(72IN)-Manitou-04-Q235盖板",
      ...
    ],
    "S-AB1830(72IN)-MP1140-01挂架组件": [
      "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
      "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板",
      ...
    ],
    "T-AB1830(72IN)-EURO-02毛刷套组件": [
      "T-AB1830(72IN)-EURO-02-01-Q355B毛刷套",
      ...
    ]
  },
  "stats": {
    "total_products": 150,
    "total_nauos": 200,
    "total_assemblies": 4
  }
}
```

**step2_bom_data.json 文件内容（部分）**：
```json
[
  {
    "seq": "1",
    "code": "01.09.2154",
    "product_code": "S-AB1830(72IN)-MP1140-01",
    "name": "挂架组件-漆后",
    "quantity": 1,
    "weight": 76.42,
    "source_pdf": "03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.pdf"
  },
  {
    "seq": "2",
    "code": "01.09.1144",
    "product_code": "H-AB1830(72IN)-Manitou-05",
    "name": "主框架组件-漆后",
    "quantity": 1,
    "weight": 56.67,
    "source_pdf": "03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.pdf"
  },
  {
    "seq": "3",
    "code": "01.09.0402",
    "product_code": "T-AB1830(72IN)-EURO-02",
    "name": "毛刷套组件-漆后",
    "quantity": 1,
    "weight": 32.43,
    "source_pdf": "03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.pdf"
  }
]
```

**step4_matching_result.json 文件内容（部分）**：
```json
{
  "success": true,
  "product_level_mapping": {
    "glb_file": "/app/output/.../glb_files/product_total.glb",
    "bom_to_mesh": {
      "01.09.2154": ["NAUO25", "NAUO26", "NAUO27"],  # 挂架组件 → 3个叶子零件
      "01.09.1144": ["NAUO30", "NAUO31", "NAUO32"],  # 主框架组件 → 3个叶子零件
      "02.03.0169": ["NAUO194", "NAUO193", "NAUO188"]  # 某个零件 → 3个实例
    }
  }
}
```

---

#### 5.5.1 完整的技术流程（代码级别）

**流程图**：
```
用户上传产品STEP文件
    ↓
【文件】core/gemini_pipeline.py → _step4_bom_3d_matching()
    ↓
【调用】core/hierarchical_bom_matcher_v2.py → process_hierarchical_matching()
    ↓
【步骤1】STEP转GLB
    ├─ 调用：processors/file_processor.py → step_to_glb()
    ├─ 输出：glb_files/product_total.glb
    └─ 提取：parts_list（所有3D零件的node_name和geometry_name）
    ↓
【步骤2】解析STEP装配层级 ⭐
    ├─ 调用：core/step_hierarchy_parser.py → parse_step_hierarchy()
    ├─ 输入：step_files/03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.step
    ├─ 处理：正则表达式提取PRODUCT、NAUO等实体
    ├─ 输出：step_assembly_hierarchy.json
    └─ 内容：{"hierarchy": {...}, "stats": {...}}
    ↓
【步骤3】AI匹配零件
    ├─ 调用：core/ai_matcher.py → match_unmatched_parts()
    ├─ 输入：parts_list + bom_data
    ├─ 处理：Gemini 2.5 Flash AI匹配
    └─ 输出：ai_bom_to_mesh（BOM代号 → node_name列表）
    ↓
【步骤4】子装配体层级匹配 ⭐⭐⭐
    ├─ 调用：core/hierarchical_bom_matcher_v2.py → _build_assembly_mesh_mapping()
    ├─ 输入：
    │   ├─ hierarchy（从step_assembly_hierarchy.json读取）
    │   ├─ product_bom（从step2_bom_data.json读取）
    │   └─ cleaned_parts（AI匹配后的零件列表）
    ├─ 处理：
    │   ├─ 遍历product_bom中的每个项
    │   ├─ 判断是否为装配体（在hierarchy中有子节点）
    │   ├─ 收集叶子零件（DFS搜索）
    │   └─ 映射到node_name
    └─ 输出：assembly_to_mesh（装配体BOM代号 → 叶子零件node_name列表）
    ↓
【步骤5】合并结果
    ├─ final_bom_to_mesh = ai_bom_to_mesh + assembly_to_mesh
    └─ 保存到：step4_matching_result.json
```

---

**文件**: `core/hierarchical_bom_matcher_v2.py` → `_build_assembly_mesh_mapping()`

#### 5.5.2 代码实现详解（逐行解释）

**文件位置**：`core/hierarchical_bom_matcher_v2.py` → 行456-514

**函数签名**：
```python
def _build_assembly_mesh_mapping(
    self,
    hierarchy: Dict,              # 从step_assembly_hierarchy.json读取
    product_bom: List[Dict],      # 从step2_bom_data.json读取
    cleaned_parts: List[Dict]     # AI匹配后的零件列表
) -> Dict[str, List[str]]:
    """将子装配体（BOM项）映射到其所有叶子零件的 node_name 列表"""
```

**代码逐行解释**：

```python
# 第1步：初始化
assembly_to_mesh = {}  # 输出结果：{bom_code: [node_name1, node_name2, ...]}

# 第2步：读取层级结构
if not hierarchy or not product_bom or not cleaned_parts:
    return {}  # 如果任何输入为空，直接返回空字典

# 第3步：遍历产品BOM中的每个项
for bom_item in product_bom:
    bom_code = bom_item.get("code", "")          # 例如："01.09.2154"
    product_code = bom_item.get("product_code", "")  # 例如："S-AB1830(72IN)-MP1140-01"

    if not product_code:
        continue  # 如果没有product_code，跳过

    # 第4步：在层级结构中查找对应的装配体名称
    assembly_name = None

    # 方法1：product_code包含匹配（核心方法）⭐
    for key in hierarchy.keys():
        if product_code in key:
            assembly_name = key
            break

    # 示例：
    # product_code = "S-AB1830(72IN)-MP1140-01"
    # hierarchy的key = "S-AB1830(72IN)-MP1140-01挂架组件"
    # 判断："S-AB1830(72IN)-MP1140-01" in "S-AB1830(72IN)-MP1140-01挂架组件" → True
    # 结果：assembly_name = "S-AB1830(72IN)-MP1140-01挂架组件"

    if not assembly_name:
        continue  # 如果没找到，跳过（说明这不是装配体，是叶子零件）

    # 第5步：收集该装配体的所有叶子零件名称
    from core.step_hierarchy_parser import collect_leaf_parts
    leaves = collect_leaf_parts(hierarchy, assembly_name)

    # 示例：
    # 输入：hierarchy, "S-AB1830(72IN)-MP1140-01挂架组件"
    # 输出：["S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
    #        "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板", ...]

    # 第6步：将叶子零件名称映射到node_name
    node_names = []
    for leaf_name in leaves:
        # 在cleaned_parts中查找geometry_name匹配的零件
        for part in cleaned_parts:
            geometry_name = part.get("geometry_name", "")

            # 方法1：直接匹配
            if geometry_name == leaf_name:
                node_names.append(part["node_name"])
                break

            # 方法2：规范化匹配（去除空白、分隔符）
            normalized_geo = geometry_name.replace(" ", "").replace("-", "").replace("_", "")
            normalized_leaf = leaf_name.replace(" ", "").replace("-", "").replace("_", "")
            if normalized_geo == normalized_leaf:
                node_names.append(part["node_name"])
                break

            # 方法3：前缀匹配（处理_1, _2后缀）
            if geometry_name.startswith(leaf_name):
                node_names.append(part["node_name"])
                break

    # 第7步：输出映射
    if node_names:
        assembly_to_mesh[bom_code] = node_names

    # 示例：
    # assembly_to_mesh["01.09.2154"] = ["NAUO25", "NAUO26", "NAUO27"]

# 第8步：返回结果
return assembly_to_mesh
```

**实际执行示例（滑移清扫器项目）**：

```python
# 输入数据
hierarchy = {
    "S-AB1830(72IN)-MP1140-01挂架组件": [
        "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
        "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板",
        "JXG-T6×100×50-970-Q355B矩形管"
    ]
}

product_bom = [
    {
        "code": "01.09.2154",
        "product_code": "S-AB1830(72IN)-MP1140-01",
        "name": "挂架组件-漆后"
    }
]

cleaned_parts = [
    {"node_name": "NAUO25", "geometry_name": "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板"},
    {"node_name": "NAUO26", "geometry_name": "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板"},
    {"node_name": "NAUO27", "geometry_name": "JXG-T6×100×50-970-Q355B矩形管"}
]

# 执行过程
# 1. 遍历product_bom，取第一项
# 2. product_code = "S-AB1830(72IN)-MP1140-01"
# 3. 在hierarchy中查找：找到"S-AB1830(72IN)-MP1140-01挂架组件"
# 4. 收集叶子零件：["S-AB1830(72IN)-MP1140-01-01-Q355B挂架板", ...]
# 5. 映射到node_name：["NAUO25", "NAUO26", "NAUO27"]
# 6. 输出：{"01.09.2154": ["NAUO25", "NAUO26", "NAUO27"]}
```

---

#### 5.5.3 DFS搜索的代码实现（collect_leaf_parts）

**文件位置**：`core/step_hierarchy_parser.py` → 行108-131

**函数签名**：
```python
def collect_leaf_parts(hierarchy: Dict[str, List[str]], root: str) -> List[str]:
    """从给定装配体（root）收集所有叶子零件名称"""
```

**代码逐行解释**：

```python
def collect_leaf_parts(hierarchy: Dict[str, List[str]], root: str) -> List[str]:
    leaves = []        # 存储叶子零件名称
    visited = set()    # 防止重复访问（避免死循环）

    def _dfs(node: str):
        """递归函数：深度优先搜索"""

        # 第1步：检查是否已访问过
        if node in visited:
            return  # 已访问过，跳过
        visited.add(node)  # 标记为已访问

        # 第2步：获取子节点列表
        children = hierarchy.get(node, [])

        # 第3步：判断是否为叶子节点
        if not children:
            # 没有子节点 = 叶子零件
            leaves.append(node)
            return

        # 第4步：遍历子节点
        for child in children:
            if child in hierarchy:
                # 子节点还有子节点 = 装配体，继续递归
                _dfs(child)
            else:
                # 子节点没有子节点 = 叶子零件
                leaves.append(child)

    # 第5步：从根节点开始搜索
    _dfs(root)

    # 第6步：返回所有叶子零件
    return leaves
```

**实际执行示例（滑移清扫器项目）**：

```python
# 输入数据
hierarchy = {
    "S-AB1830(72IN)-MP1140滑移清扫器（斜角型）": [
        "H-AB1830(72IN)-Manitou-05主框架组件",
        "S-AB1830(72IN)-MP1140-01挂架组件",
        "BMR250液压马达(4安装孔)"
    ],
    "H-AB1830(72IN)-Manitou-05主框架组件": [
        "H-AB1830(72IN)-Manitou-01左侧板组件",
        "H-AB1830(72IN)-Manitou-02右侧板组件",
        "H-AB1830(72IN)-Manitou-04-Q235盖板"
    ],
    "S-AB1830(72IN)-MP1140-01挂架组件": [
        "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
        "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板"
    ]
}

root = "S-AB1830(72IN)-MP1140-01挂架组件"

# 执行过程（DFS搜索）
# 调用：_dfs("S-AB1830(72IN)-MP1140-01挂架组件")
#   ├─ visited.add("S-AB1830(72IN)-MP1140-01挂架组件")
#   ├─ children = ["S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
#   │              "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板"]
#   ├─ 遍历child1 = "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板"
#   │   ├─ child1 不在hierarchy的key中 → 叶子零件
#   │   └─ leaves.append("S-AB1830(72IN)-MP1140-01-01-Q355B挂架板")
#   ├─ 遍历child2 = "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板"
#   │   ├─ child2 不在hierarchy的key中 → 叶子零件
#   │   └─ leaves.append("S-AB1830(72IN)-MP1140-01-02-Q355B挂架板")
#   └─ 返回

# 输出
leaves = [
    "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
    "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板"
]
```

**复杂示例（多层嵌套）**：

```python
root = "H-AB1830(72IN)-Manitou-05主框架组件"

# 执行过程（DFS搜索）
# 调用：_dfs("H-AB1830(72IN)-Manitou-05主框架组件")
#   ├─ children = ["H-AB1830(72IN)-Manitou-01左侧板组件",
#   │              "H-AB1830(72IN)-Manitou-02右侧板组件",
#   │              "H-AB1830(72IN)-Manitou-04-Q235盖板"]
#   ├─ 遍历child1 = "H-AB1830(72IN)-Manitou-01左侧板组件"
#   │   ├─ child1 在hierarchy的key中 → 装配体，递归
#   │   └─ 调用：_dfs("H-AB1830(72IN)-Manitou-01左侧板组件")
#   │       └─ ... 继续递归收集叶子零件
#   ├─ 遍历child2 = "H-AB1830(72IN)-Manitou-02右侧板组件"
#   │   └─ ... 同上
#   └─ 遍历child3 = "H-AB1830(72IN)-Manitou-04-Q235盖板"
#       ├─ child3 不在hierarchy的key中 → 叶子零件
#       └─ leaves.append("H-AB1830(72IN)-Manitou-04-Q235盖板")
```

---

**核心问题**：产品BOM中有子装配体（如"挂架组件"），如何将其映射到3D模型中的叶子零件？

#### 5.5.4 文件读取流程（代码级别）

**问题**：代码是怎么读取 `step_assembly_hierarchy.json` 文件的？

**答案**：在 `core/hierarchical_bom_matcher_v2.py` 的 `process_hierarchical_matching()` 函数中

**代码位置**：`core/hierarchical_bom_matcher_v2.py` → 行304-357

**代码片段**：
```python
# 第1步：定义层级文件路径
hierarchy_output = glb_output.parent / "step_assembly_hierarchy.json"
# 例如：output/03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）/step_assembly_hierarchy.json

hierarchy_data = None

# 第2步：查找产品STEP文件
product_step = None
product_info = file_hierarchy.get("product") if isinstance(file_hierarchy, dict) else None
if isinstance(product_info, dict) and product_info.get("step"):
    candidate = Path(product_info["step"])
    if candidate.exists():
        product_step = candidate

# 第3步：如果找到产品STEP文件，解析层级结构
if product_step and product_step.exists():
    print_info(f"处理产品总图: {product_step.name}")

    # 第3.1步：STEP转GLB
    product_glb = glb_output / "product_total.glb"
    convert_result = self.step_converter.convert(
        step_path=str(product_step),
        output_path=str(product_glb),
        scale_factor=0.001
    )

    if convert_result["success"]:
        parts_list = convert_result.get("parts_info", [])

        # 第3.2步：解析并保存STEP装配层级 ⭐⭐⭐
        try:
            from core.step_hierarchy_parser import parse_step_hierarchy

            # 调用解析函数
            hierarchy_data = parse_step_hierarchy(str(product_step))

            # 保存到JSON文件
            hierarchy_output.parent.mkdir(parents=True, exist_ok=True)
            with open(hierarchy_output, "w", encoding="utf-8") as f:
                json.dump(hierarchy_data, f, ensure_ascii=False, indent=2)

            print_success(f"装配层级已生成: {hierarchy_output.name}", indent=1)
        except Exception as e:
            print_warning(f"装配层级解析失败: {e}", indent=1)

# 第4步：读取层级数据（用于后续匹配）
if hierarchy_data:
    hierarchy = hierarchy_data.get("hierarchy", {})
else:
    hierarchy = {}
```

**实际执行流程（滑移清扫器项目）**：

```python
# 输入
product_step = Path("output/.../step_files/03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.step")

# 第1步：调用parse_step_hierarchy()
hierarchy_data = parse_step_hierarchy(str(product_step))

# 第2步：hierarchy_data的内容
hierarchy_data = {
    "hierarchy": {
        "S-AB1830(72IN)-MP1140滑移清扫器（斜角型）": [
            "H-AB1830(72IN)-Manitou-05主框架组件",
            "S-AB1830(72IN)-MP1140-01挂架组件",
            ...
        ],
        "H-AB1830(72IN)-Manitou-05主框架组件": [
            "H-AB1830(72IN)-Manitou-01左侧板组件",
            ...
        ]
    },
    "stats": {
        "total_products": 150,
        "total_nauos": 200,
        "total_assemblies": 4
    }
}

# 第3步：保存到文件
# 文件路径：output/03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）/step_assembly_hierarchy.json
with open(hierarchy_output, "w", encoding="utf-8") as f:
    json.dump(hierarchy_data, f, ensure_ascii=False, indent=2)

# 第4步：提取hierarchy字典（用于后续匹配）
hierarchy = hierarchy_data.get("hierarchy", {})
```

---

#### 5.5.5 数据流向图（完整链路）

```
【文件1】step_files/03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）.step
    ↓ [读取]
【函数】parse_step_hierarchy()
    ├─ 正则表达式提取PRODUCT实体
    ├─ 正则表达式提取NAUO实体
    └─ 建立父子关系映射
    ↓ [输出]
【文件2】step_assembly_hierarchy.json
    {
      "hierarchy": {
        "S-AB1830(72IN)-MP1140滑移清扫器（斜角型）": [...],
        "H-AB1830(72IN)-Manitou-05主框架组件": [...]
      }
    }
    ↓ [读取]
【变量】hierarchy = hierarchy_data.get("hierarchy", {})
    ↓ [传入]
【函数】_build_assembly_mesh_mapping(hierarchy, product_bom, cleaned_parts)
    ├─ 遍历product_bom
    ├─ 在hierarchy中查找装配体
    ├─ 调用collect_leaf_parts()收集叶子零件
    └─ 映射到node_name
    ↓ [输出]
【变量】assembly_to_mesh = {
    "01.09.2154": ["NAUO25", "NAUO26", "NAUO27"],
    "01.09.1144": ["NAUO30", "NAUO31", "NAUO32"]
}
    ↓ [合并]
【变量】final_bom_to_mesh = ai_bom_to_mesh + assembly_to_mesh
    ↓ [保存]
【文件3】step4_matching_result.json
    {
      "product_level_mapping": {
        "bom_to_mesh": {
          "01.09.2154": ["NAUO25", "NAUO26", "NAUO27"],
          "01.09.1144": ["NAUO30", "NAUO31", "NAUO32"],
          "02.03.0169": ["NAUO194", "NAUO193", "NAUO188"]
        }
      }
    }
    ↓ [读取]
【Agent4】agents/product_assembly_agent.py
    ├─ 读取step4_matching_result.json
    ├─ 生成装配步骤JSON
    └─ 为每个步骤添加node_name
    ↓ [输出]
【文件4】step6_product_result.json
    {
      "assembly_steps": [
        {
          "step": 1,
          "description": "安装挂架组件",
          "components": [
            {
              "bom_code": "01.09.2154",
              "node_name": ["NAUO25", "NAUO26", "NAUO27"]  ← 从映射中获取
            }
          ]
        }
      ]
    }
    ↓ [传给前端]
【前端】3D查看器
    highlightParts(["NAUO25", "NAUO26", "NAUO27"])
    ↓ [效果]
【用户】看到挂架组件的所有零件同时高亮
```

---

#### 5.5.6 智能体协作流程

**涉及的智能体/模块**：

1. **FileClassifier（文件分类器）**
   - 作用：区分产品图和组件图
   - 输入：PDF文件名、STEP文件名
   - 输出：file_hierarchy.json

2. **StepHierarchyParser（STEP层级解析器）**
   - 作用：解析STEP文件的装配层级
   - 输入：产品STEP文件
   - 输出：step_assembly_hierarchy.json

3. **AIBOMMatcher（AI匹配器）**
   - 作用：AI匹配BOM零件和3D零件
   - 输入：parts_list + bom_data
   - 输出：ai_bom_to_mesh

4. **HierarchicalBOMMatcher（层级匹配器）**
   - 作用：子装配体层级匹配
   - 输入：hierarchy + product_bom + cleaned_parts
   - 输出：assembly_to_mesh

5. **ProductAssemblyAgent（产品装配智能体）**
   - 作用：生成产品总装步骤
   - 输入：step4_matching_result.json
   - 输出：step6_product_result.json

**协作时序图**：

```
时间轴 ↓

T1: FileClassifier.classify()
    └─ 输出：file_hierarchy.json

T2: StepConverter.convert()
    └─ 输出：product_total.glb + parts_list

T3: StepHierarchyParser.parse_step_hierarchy()
    └─ 输出：step_assembly_hierarchy.json

T4: AIBOMMatcher.match_unmatched_parts()
    └─ 输出：ai_bom_to_mesh

T5: HierarchicalBOMMatcher._build_assembly_mesh_mapping()
    ├─ 读取：step_assembly_hierarchy.json
    ├─ 读取：step2_bom_data.json
    ├─ 读取：cleaned_parts（来自T4）
    └─ 输出：assembly_to_mesh

T6: 合并结果
    └─ final_bom_to_mesh = ai_bom_to_mesh + assembly_to_mesh

T7: 保存结果
    └─ 输出：step4_matching_result.json

T8: ProductAssemblyAgent.generate_assembly_steps()
    ├─ 读取：step4_matching_result.json
    └─ 输出：step6_product_result.json

T9: 前端读取
    └─ 读取：step6_product_result.json
    └─ 高亮零件
```

---

**为什么需要这个功能**：
```
问题场景：
装配步骤说："步骤3：安装挂架组件"
但3D模型中没有"挂架组件"这个几何体，只有：
- NAUO25（矩形管970）
- NAUO26（矩形管335）
- NAUO27（M8螺栓）

如果不做层级匹配：
→ 前端无法高亮"挂架组件"
→ 用户不知道要装哪些零件

做了层级匹配后：
→ 系统知道"挂架组件" = NAUO25 + NAUO26 + NAUO27
→ 前端同时高亮这3个零件
→ 用户清楚地看到要装的所有零件
```

#### 5.5.1 匹配策略（用人话解释）

**输入**：
1. **hierarchy（层级结构）**：从STEP文件解析出来的树形结构
2. **product_bom（产品BOM）**：包含所有零件和组件的BOM表
3. **cleaned_parts（已匹配的3D零件）**：已经通过AI匹配的零件列表

**输出**：
```python
assembly_to_mesh = {
    "01.03.0281": ["NAUO25", "NAUO26", "NAUO27"],  # 挂架组件 → 3个叶子零件
    "01.03.0282": ["NAUO28", "NAUO29"]             # 连接器组件 → 2个叶子零件
}
```

**核心逻辑**：
```
遍历产品BOM中的每个项
├─ 步骤1：判断这个BOM项是不是装配体
│   └─ 方法：检查它在层级结构中是否有子节点
│
├─ 步骤2：如果是装配体，提取它的product_code
│   └─ 例如：product_code = "S-AB1830(72IN)-MP1140-01"
│
├─ 步骤3：在层级结构中查找对应的装配体名称
│   ├─ 方法1：product_code包含匹配（核心）⭐
│   │   └─ 层级key = "S-AB1830(72IN)-MP1140-01挂架组件"
│   │   └─ 判断：product_code in 层级key → 匹配！
│   │
│   └─ 方法2：代码提取匹配（备用）
│       └─ 提取代码片段（如"S-AB1830"）进行匹配
│
├─ 步骤4：收集该装配体的所有叶子零件名称
│   ├─ 调用：collect_leaf_parts(hierarchy, assembly_name)
│   ├─ 方法：DFS深度优先搜索（见术语5）
│   └─ 输出：["矩形管970", "矩形管335", "M8螺栓"]
│
├─ 步骤5：将叶子零件名称映射到node_name
│   ├─ 方法1：直接匹配（geometry_name == 叶子名称）
│   ├─ 方法2：规范化匹配（去除空白、分隔符后匹配）
│   ├─ 方法3：前缀匹配（处理_1, _2后缀）
│   └─ 方法4：代码片段匹配（提取产品代号匹配）
│
└─ 步骤6：输出映射
    └─ assembly_to_mesh[bom_code] = [node_name1, node_name2, ...]
```

#### 5.5.7 【实战案例】滑移清扫器项目完整演示

**项目**：`03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）`

**场景**：产品BOM中有3个装配体，需要映射到3D模型中的叶子零件

---

**步骤1：查看实际的层级结构文件**

```bash
# 文件路径
D:\yilite\output\03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）\step_assembly_hierarchy.json
```

**文件内容（精简版）**：
```json
{
  "hierarchy": {
    "S-AB1830(72IN)-MP1140滑移清扫器（斜角型）": [
      "H-AB1830(72IN)-Manitou-05主框架组件",      ← 装配体1
      "S-AB1830(72IN)-MP1140-01挂架组件",         ← 装配体2
      "T-AB1830(72IN)-EURO-02毛刷套组件",         ← 装配体3
      "BMR250液压马达(4安装孔)",                   ← 叶子零件
      "MS-φ162-φ550-黄色PP+钢丝-圆形毛刷盘",      ← 叶子零件
      "GB／T 5783-2016六角头螺栓全螺纹 C级M14×70" ← 叶子零件
    ],
    "H-AB1830(72IN)-Manitou-05主框架组件": [
      "H-AB1830(72IN)-Manitou-01左侧板组件",
      "H-AB1830(72IN)-Manitou-02右侧板组件",
      "H-AB1830(72IN)-Manitou-04-Q235盖板"
    ],
    "S-AB1830(72IN)-MP1140-01挂架组件": [
      "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
      "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板",
      "JXG-T6×100×50-970-Q355B矩形管"
    ],
    "T-AB1830(72IN)-EURO-02毛刷套组件": [
      "T-AB1830(72IN)-EURO-02-01-Q355B毛刷套",
      "T-AB1830(72IN)-EURO-02-02-Q355B毛刷套"
    ]
  }
}
```

**关键观察**：
- 顶层有3个装配体：主框架组件、挂架组件、毛刷套组件
- 每个装配体都有自己的子零件
- 叶子零件（如液压马达、毛刷盘）直接在顶层

---

**步骤2：查看实际的BOM数据**

```bash
# 文件路径
D:\yilite\output\03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）\step2_bom_data.json
```

**文件内容（精简版）**：
```json
[
  {
    "seq": "1",
    "code": "01.09.2154",
    "product_code": "S-AB1830(72IN)-MP1140-01",
    "name": "挂架组件-漆后",
    "quantity": 1
  },
  {
    "seq": "2",
    "code": "01.09.1144",
    "product_code": "H-AB1830(72IN)-Manitou-05",
    "name": "主框架组件-漆后",
    "quantity": 1
  },
  {
    "seq": "3",
    "code": "01.09.0402",
    "product_code": "T-AB1830(72IN)-EURO-02",
    "name": "毛刷套组件-漆后",
    "quantity": 1
  },
  {
    "seq": "4",
    "code": "02.03.0169",
    "product_code": "MS-φ162-φ550-黄色PP+钢丝",
    "name": "圆形毛刷盘",
    "quantity": 36
  }
]
```

**关键观察**：
- 前3项是装配体（有对应的层级结构）
- 第4项是叶子零件（数量=36，说明有36个实例）

---

**步骤3：代码执行过程（逐项处理）**

**处理第1项：挂架组件**

```python
# 输入
bom_item = {
    "code": "01.09.2154",
    "product_code": "S-AB1830(72IN)-MP1140-01",
    "name": "挂架组件-漆后"
}

# 第1步：在hierarchy中查找
for key in hierarchy.keys():
    if "S-AB1830(72IN)-MP1140-01" in key:
        assembly_name = key
        break

# 结果：assembly_name = "S-AB1830(72IN)-MP1140-01挂架组件"

# 第2步：收集叶子零件
leaves = collect_leaf_parts(hierarchy, "S-AB1830(72IN)-MP1140-01挂架组件")

# 结果：
leaves = [
    "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板",
    "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板",
    "JXG-T6×100×50-970-Q355B矩形管"
]

# 第3步：映射到node_name
# 假设cleaned_parts中有：
# {"node_name": "NAUO25", "geometry_name": "S-AB1830(72IN)-MP1140-01-01-Q355B挂架板"}
# {"node_name": "NAUO26", "geometry_name": "S-AB1830(72IN)-MP1140-01-02-Q355B挂架板"}
# {"node_name": "NAUO27", "geometry_name": "JXG-T6×100×50-970-Q355B矩形管"}

node_names = ["NAUO25", "NAUO26", "NAUO27"]

# 第4步：输出映射
assembly_to_mesh["01.09.2154"] = ["NAUO25", "NAUO26", "NAUO27"]
```

**处理第2项：主框架组件**

```python
# 输入
bom_item = {
    "code": "01.09.1144",
    "product_code": "H-AB1830(72IN)-Manitou-05",
    "name": "主框架组件-漆后"
}

# 第1步：在hierarchy中查找
assembly_name = "H-AB1830(72IN)-Manitou-05主框架组件"

# 第2步：收集叶子零件
leaves = collect_leaf_parts(hierarchy, "H-AB1830(72IN)-Manitou-05主框架组件")

# 结果：
leaves = [
    "H-AB1830(72IN)-Manitou-01左侧板组件",
    "H-AB1830(72IN)-Manitou-02右侧板组件",
    "H-AB1830(72IN)-Manitou-04-Q235盖板"
]

# 第3步：映射到node_name
node_names = ["NAUO30", "NAUO31", "NAUO32"]

# 第4步：输出映射
assembly_to_mesh["01.09.1144"] = ["NAUO30", "NAUO31", "NAUO32"]
```

**处理第3项：毛刷套组件**

```python
# 输入
bom_item = {
    "code": "01.09.0402",
    "product_code": "T-AB1830(72IN)-EURO-02",
    "name": "毛刷套组件-漆后"
}

# 第1步：在hierarchy中查找
assembly_name = "T-AB1830(72IN)-EURO-02毛刷套组件"

# 第2步：收集叶子零件
leaves = [
    "T-AB1830(72IN)-EURO-02-01-Q355B毛刷套",
    "T-AB1830(72IN)-EURO-02-02-Q355B毛刷套"
]

# 第3步：映射到node_name
node_names = ["NAUO40", "NAUO41"]

# 第4步：输出映射
assembly_to_mesh["01.09.0402"] = ["NAUO40", "NAUO41"]
```

**处理第4项：圆形毛刷盘（叶子零件）**

```python
# 输入
bom_item = {
    "code": "02.03.0169",
    "product_code": "MS-φ162-φ550-黄色PP+钢丝",
    "name": "圆形毛刷盘",
    "quantity": 36
}

# 第1步：在hierarchy中查找
for key in hierarchy.keys():
    if "MS-φ162-φ550-黄色PP+钢丝" in key:
        assembly_name = key
        break

# 结果：assembly_name = None（因为这不是装配体，是叶子零件）

# 第2步：跳过（不处理叶子零件）
# 叶子零件由AI匹配器处理，不需要层级匹配
```

---

**步骤4：最终输出**

```python
assembly_to_mesh = {
    "01.09.2154": ["NAUO25", "NAUO26", "NAUO27"],  # 挂架组件 → 3个叶子零件
    "01.09.1144": ["NAUO30", "NAUO31", "NAUO32"],  # 主框架组件 → 3个叶子零件
    "01.09.0402": ["NAUO40", "NAUO41"]             # 毛刷套组件 → 2个叶子零件
}
```

**保存到文件**：
```bash
# 文件路径
D:\yilite\output\03.03.04.0002S-AB1830(72IN)-MP1140滑移清扫器（斜角型）\step4_matching_result.json
```

**文件内容（部分）**：
```json
{
  "success": true,
  "product_level_mapping": {
    "bom_to_mesh": {
      "01.09.2154": ["NAUO25", "NAUO26", "NAUO27"],
      "01.09.1144": ["NAUO30", "NAUO31", "NAUO32"],
      "01.09.0402": ["NAUO40", "NAUO41"],
      "02.03.0169": ["NAUO194", "NAUO193", "NAUO188", ...]  ← AI匹配的结果（36个实例）
    }
  }
}
```

---

**步骤5：前端应用**

**装配步骤JSON**：
```json
{
  "assembly_steps": [
    {
      "step": 1,
      "description": "安装挂架组件",
      "components": [
        {
          "bom_code": "01.09.2154",
          "bom_name": "挂架组件-漆后",
          "node_name": ["NAUO25", "NAUO26", "NAUO27"]  ← 从assembly_to_mesh获取
        }
      ]
    },
    {
      "step": 2,
      "description": "安装主框架组件",
      "components": [
        {
          "bom_code": "01.09.1144",
          "bom_name": "主框架组件-漆后",
          "node_name": ["NAUO30", "NAUO31", "NAUO32"]  ← 从assembly_to_mesh获取
        }
      ]
    }
  ]
}
```

**前端高亮指令**：
```javascript
// 步骤1：高亮挂架组件
highlightParts(["NAUO25", "NAUO26", "NAUO27"])

// 效果：3D模型中同时高亮3个零件
// - S-AB1830(72IN)-MP1140-01-01-Q355B挂架板
// - S-AB1830(72IN)-MP1140-01-02-Q355B挂架板
// - JXG-T6×100×50-970-Q355B矩形管
```

---

#### 5.5.8 完整示例（从头到尾）

**场景**：产品BOM中有一个"挂架组件"，需要映射到3D模型中的叶子零件

**步骤1：输入数据**

```python
# BOM表中的一项（挂架组件）
bom_item = {
    "bom_code": "01.03.0281",
    "bom_name": "挂架组件",
    "product_code": "S-AB1830(72IN)-MP1140-01",
    "quantity": 1
}

# STEP层级结构（从step_assembly_hierarchy.json读取）
hierarchy = {
    "产品总装": ["挂架组件", "连接器组件", "固定座"],
    "S-AB1830(72IN)-MP1140-01挂架组件": [
        "JXG-T6×100×50-970-Q355B矩形管",
        "JXG-T6×100×50-335-Q355B矩形管",
        "M8螺栓"
    ]
}

# 已匹配的3D零件（AI匹配的结果）
cleaned_parts = [
    {"node_name": "NAUO25", "geometry_name": "JXG-T6×100×50-970-Q355B矩形管"},
    {"node_name": "NAUO26", "geometry_name": "JXG-T6×100×50-335-Q355B矩形管"},
    {"node_name": "NAUO27", "geometry_name": "M8螺栓"}
]
```

**步骤2：在层级结构中查找装配体**

```python
# 提取product_code
product_code = "S-AB1830(72IN)-MP1140-01"

# 在hierarchy的key中查找包含product_code的项
for assembly_name in hierarchy.keys():
    if product_code in assembly_name:
        # 找到了！assembly_name = "S-AB1830(72IN)-MP1140-01挂架组件"
        break
```

**为什么用"包含匹配"而不是"精确匹配"**：
- STEP文件中的名称：`S-AB1830(72IN)-MP1140-01挂架组件`
- BOM表中的product_code：`S-AB1830(72IN)-MP1140-01`
- 两者不完全一样，但product_code包含在STEP名称中
- 所以用"包含匹配"更可靠

**步骤3：收集叶子零件名称**

```python
# 调用DFS搜索
leaves = collect_leaf_parts(hierarchy, "S-AB1830(72IN)-MP1140-01挂架组件")

# 执行过程（见术语5的DFS解释）：
# 1. 进入"S-AB1830(72IN)-MP1140-01挂架组件"
# 2. 看到"JXG-T6×100×50-970-Q355B矩形管" → 叶子零件 → 记录
# 3. 看到"JXG-T6×100×50-335-Q355B矩形管" → 叶子零件 → 记录
# 4. 看到"M8螺栓" → 叶子零件 → 记录

# 输出：
leaves = [
    "JXG-T6×100×50-970-Q355B矩形管",
    "JXG-T6×100×50-335-Q355B矩形管",
    "M8螺栓"
]
```

**步骤4：将叶子零件名称映射到node_name**

```python
node_names = []

for leaf_name in leaves:
    # 在cleaned_parts中查找geometry_name匹配的零件
    for part in cleaned_parts:
        if part["geometry_name"] == leaf_name:
            node_names.append(part["node_name"])
            break

# 输出：
node_names = ["NAUO25", "NAUO26", "NAUO27"]
```

**步骤5：输出映射**

```python
assembly_to_mesh = {
    "01.03.0281": ["NAUO25", "NAUO26", "NAUO27"]
}
```

**步骤6：实际应用**

```python
# 装配步骤JSON：
{
    "step": 3,
    "description": "安装挂架组件",
    "components": [
        {
            "bom_code": "01.03.0281",
            "bom_name": "挂架组件",
            "node_name": ["NAUO25", "NAUO26", "NAUO27"]  # ← 从映射中获取
        }
    ]
}

# 前端高亮指令：
highlightParts(["NAUO25", "NAUO26", "NAUO27"])

# 效果：
3D模型中同时高亮矩形管970、矩形管335、M8螺栓
用户清楚地看到"挂架组件"包含哪些零件
```

#### 5.5.3 关键代码（供技术人员参考）

**文件**: `core/step_hierarchy_parser.py` → `collect_leaf_parts()`

这个函数实现了DFS深度优先搜索，用于收集装配体的所有叶子零件。

**代码逻辑**：
```python
def collect_leaf_parts(hierarchy: Dict[str, List[str]], root: str) -> List[str]:
    """从给定装配体（root）收集所有叶子零件名称"""
    leaves = []
    visited = set()  # 防止重复访问

    def _dfs(node: str):
        if node in visited:
            return  # 已访问过，跳过
        visited.add(node)

        children = hierarchy.get(node, [])
        if not children:
            # 没有子节点 = 叶子零件
            leaves.append(node)
            return

        for child in children:
            if child in hierarchy:
                # 子节点还有子节点 = 装配体，继续递归
                _dfs(child)
            else:
                # 子节点没有子节点 = 叶子零件
                leaves.append(child)

    _dfs(root)
    return leaves
```

---

### 5.6 产品图 vs 组件图的BOM范围差异

**关键问题**：产品BOM包含组件吗？

**答案**：✅ **包含！**（v2.0.32修复）

**原因**：
- 产品总装步骤需要高亮组件内的零件
- 例如："步骤3：安装挂架组件" → 需要高亮挂架组件内的所有零件
- 如果产品BOM不包含组件的零件，就无法高亮

**代码**：
```python
# ✅ 产品级别的BOM数据（包含所有零件+组件）
product_bom_all = [
    item for item in bom_data
    if product_pdf_stem and str(item.get("source_pdf", "")).startswith(product_pdf_stem)
]

# ✅ 新策略：包含所有BOM项（组件+零件）
product_bom = product_bom_all
```

**对比**：

| BOM类型 | 组件BOM | 产品BOM |
|---------|---------|---------|
| **范围** | 仅组件内部零件 | 所有零件+组件 |
| **过滤条件** | `source_pdf == "组件图1.pdf"` | `source_pdf.startswith("产品总图")` |
| **是否包含子装配体** | ❌ 否 | ✅ 是 |
| **用途** | 组件装配步骤 | 产品总装步骤 |

---

### 5.7 AI匹配器详解

**文件**: `core/ai_matcher.py` → `AIBOMMatcher`

**AI模型**: `google/gemini-2.5-flash-preview-09-2025`
**API**: OpenRouter (`https://openrouter.ai/api/v1`)

#### 5.2.1 批处理策略
```python
if len(unmatched_parts) > 200:  # 超过阈值
    # 分批处理（每批100个零件）
    _match_in_batches()
else:
    # 一次性处理
    _match_all_at_once()
```

**为什么要分批？**
- Gemini 2.5 Flash支持100万token输入，但响应可能被截断
- 超过200个零件时，分批处理避免响应截断
- 每批100个零件，确保稳定性

#### 5.2.2 AI提示词（Prompt）

**文件**: `prompts/agent_2_bom_3d_matching.py`

**角色设定**：
- 你是**张工**，10年机械装配和3D建模经验的BOM-3D匹配专家

**核心认知**（⚠️ 非常重要）：
1. **STEP文件中的geometry_name包含的是产品代号（product_code），不是BOM代号！**
2. **产品代号是最可靠的匹配依据**
3. **目标：100%匹配率**

**匹配策略优先级**：

| 优先级 | 方法 | 置信度 | 示例 |
|--------|------|--------|------|
| 1 | **产品代号精确匹配** | 0.90-0.98 | geometry_name: `JXG-T6×100×50-970-Q355B矩形管`<br>BOM product_code: `JXG-T6×100×50-970-Q355B`<br>→ **完全匹配！置信度0.98** |
| 2 | 规格匹配（标准件） | 0.75-0.90 | geometry_name: `GB/T889.1-2000...M8`<br>BOM product_code: `M8`<br>→ 标准号+规格匹配，置信度0.88 |
| 3 | 材料+类型匹配 | 0.70-0.75 | 规格+材料一致 |

**⚠️ 精确匹配要求**：
- 产品代号必须**完全一致**，不允许模糊匹配
- 不要混淆相似的产品代号（如970和335长度的矩形管）

**反例**：
```
geometry_name: JXG-T6×100×50-335-Q355B矩形管
BOM product_code: JXG-T6×100×50-970-Q355B
→ 长度不同（335 vs 970）→ 不匹配！
```

#### 5.2.3 COT推理流程（Chain of Thought）

AI对每个未匹配的BOM项，按以下5步推理：

1. **信息提取**：从BOM中提取产品代号、规格、标准号、材料、零件类型
2. **候选筛选**：从3D零件中找出至少3个可能匹配的候选零件
3. **逐一对比**：对每个候选零件进行产品代号、规格、标准号、材料、类型的对比
4. **置信度评估**：根据匹配依据评估置信度（0.70-0.98）
5. **最佳选择**：选择置信度最高的候选零件（≥0.70即可输出）

**输出格式**：
```json
{
  "cot_analysis": {
    "total_unmatched_bom": 15,
    "total_unmatched_3d": 50,
    "analysis_steps": [
      {
        "bom_code": "02.03.0028",
        "step1_extract": "标准号=GB/T889.1, 规格=M8",
        "step2_candidates": ["NAUO15: GB/T889.1-2000...M8"],
        "step3_comparison": "标准号一致, 规格M8一致",
        "step4_confidence": 0.88,
        "step5_decision": "匹配NAUO15"
      }
    ]
  },
  "ai_matched_pairs": [
    {
      "node_name": "NAUO15",
      "bom_code": "02.03.0028",
      "confidence": 0.88,
      "reasoning": "标准号GB/T889.1+规格M8匹配"
    }
  ]
}
```

---

## 6️⃣ 匹配结果应用

### 6.1 更新cleaned_parts
**文件**: `core/hierarchical_bom_matcher_v2.py` (行193-214)

```python
# 将AI匹配结果应用到cleaned_parts（更新bom_code）
for ai_result in ai_results:
    bom_code = ai_result.get("matched_bom_code")
    node_name = ai_result.get("node_name")

    if bom_code and node_name:
        # 找到对应的零件并更新bom_code
        for part in cleaned_parts:
            if part.get("node_name") == node_name and not part.get("bom_code"):
                part["bom_code"] = bom_code
                part["match_method"] = "AI匹配"
                part["confidence"] = ai_result.get("confidence", 0.0)
                break
```

### 6.2 生成BOM映射宽表
**文件**: `core/bom_3d_matcher.py` → `generate_bom_mapping_table()`

**宽表结构**：
```json
[
  {
    "bom_code": "01.09.2549",
    "bom_name": "后座组件",
    "product_code": "T-SPV250-Z602-01-01-Q355B",
    "mesh_id": "mesh_001",
    "node_name": "NAUO1",
    "geometry_name": "T-SPV250-Z602-01-01-Q355B连接板",
    "match_method": "AI匹配",
    "confidence": 0.98
  }
]
```

### 6.3 统计匹配率
```python
# BOM匹配率：匹配成功的BOM数 / 总BOM数
bom_matching_rate = bom_matched_count / total_bom_count

# 3D零件覆盖率：匹配成功的3D零件数 / 总3D零件数
parts_matching_rate = matched_3d_count / total_3d_parts
```

---

## 7️⃣ 关键代码位置

| 功能 | 文件路径 | 关键函数/类 |
|------|----------|-------------|
| 文件上传 | `frontend/src/api/index.ts` | `uploadFiles()` |
| 文件分类 | `core/file_classifier.py` | `classify_files()` |
| BOM提取 | `models/gemini_model.py` | `extract_bom_from_images()` |
| STEP转GLB | `processors/step_to_glb_converter.py` | `convert()` |
| **AI匹配器** | `core/ai_matcher.py` | `AIBOMMatcher` |
| **AI提示词** | `prompts/agent_2_bom_3d_matching.py` | `build_ai_matching_prompt()` |
| 分层级匹配 | `core/hierarchical_bom_matcher_v2.py` | `process_hierarchical_matching()` |
| BOM映射宽表 | `core/bom_3d_matcher.py` | `generate_bom_mapping_table()` |

---

## 8️⃣ 常见问题

### Q1: 为什么代码匹配被禁用？
**A**: 因为STEP文件中的`geometry_name`包含的是**产品代号**（如`JXG-T6×100×50-970-Q355B`），不是BOM代号（如`01.09.2549`）。代码匹配会把相似的零件混淆（如970和335长度的矩形管）。

### Q2: AI匹配的准确率如何？
**A**:
- **高置信度（≥0.85）**：产品代号完全匹配，准确率接近100%
- **中等置信度（0.70-0.85）**：规格+材料匹配，准确率约90%
- **低置信度（<0.70）**：不输出，避免错误匹配

### Q3: 如果AI匹配失败怎么办？
**A**:
1. 检查BOM表中的`product_code`字段是否完整
2. 检查STEP文件中的零件命名是否包含产品代号
3. 查看调试文件：`output/{task_id}/ai_matching_debug_{timestamp}.json`

### Q4: 一个BOM可以对应多个3D零件吗？
**A**: 可以！例如：
- BOM: `02.03.0610` 平垫圈 (quantity=3)
- 3D零件: NAUO10, NAUO13, NAUO14（3个垫圈实例）
- AI会为每个零件输出一个匹配对（同一个bom_code重复3次）

---

## 9️⃣ 调试技巧

### 9.1 查看AI匹配调试文件
```
output/{task_id}/ai_matching_debug_{timestamp}.json
```

**内容**：
- 输入的未匹配零件列表
- 输入的未匹配BOM列表
- AI返回的原始JSON
- 匹配结果统计

### 9.2 查看BOM映射宽表
```
output/{task_id}/step4_matching_result.json
```

**内容**：
- 组件级别的BOM映射宽表
- 产品级别的BOM映射宽表
- 匹配率统计

---

## 🎯 总结：产品图和组件图的核心差异

### 快速对比表

| 维度 | 组件图 | 产品图 |
|------|--------|--------|
| **STEP文件内容** | 单个组件的零件 | 完整产品（包含多个子装配体） |
| **是否有层级结构** | ❌ 否（扁平结构） | ✅ 是（树形结构） |
| **是否解析层级** | ❌ 不解析 | ✅ 解析并保存到JSON |
| **BOM范围** | 仅组件内部零件 | 所有零件+组件 |
| **匹配策略** | AI匹配零件 | AI匹配零件 + 子装配体层级匹配 |
| **GLB文件名** | `component_{index}.glb` | `product_total.glb` |
| **层级文件** | ❌ 不生成 | ✅ `step_assembly_hierarchy.json` |
| **装配体处理** | ❌ 无装配体 | ✅ 映射到叶子零件 |

---

### 核心流程总结

#### 组件图处理流程（简化版）

```
1. 上传组件图PDF + 组件STEP
   ↓
2. PDF → BOM表（只包含组件内部零件）
   ↓
3. STEP → GLB（扁平结构，无层级）
   ↓
4. AI匹配：BOM零件 ↔ 3D零件
   ↓
5. 输出：bom_to_mesh（BOM代号 → node_name）
```

#### 产品图处理流程（完整版）

```
1. 上传产品图PDF + 产品STEP
   ↓
2. PDF → BOM表（包含所有零件+组件）
   ↓
3. STEP → GLB（包含所有零件）
   ↓
4. STEP → 层级结构（树形结构）⭐
   ├─ 解析PRODUCT、NAUO等实体
   ├─ 建立父子关系映射
   └─ 保存到step_assembly_hierarchy.json
   ↓
5. AI匹配：BOM零件 ↔ 3D零件
   ↓
6. 子装配体层级匹配 ⭐⭐⭐
   ├─ 遍历BOM中的装配体
   ├─ 在层级结构中查找对应的装配体
   ├─ 收集装配体的所有叶子零件（DFS）
   ├─ 将叶子零件名称映射到node_name
   └─ 输出：assembly_to_mesh（装配体BOM代号 → 叶子零件node_name列表）
   ↓
7. 合并结果：final_bom_to_mesh = ai_bom_to_mesh + assembly_to_mesh
   ↓
8. 输出：完整的BOM-3D映射关系
```

---

### 关键术语速查

| 术语 | 含义 | 来源 | 用途 |
|------|------|------|------|
| **product_code** | 产品代号（零件身份证） | BOM表 + STEP文件 | 最可靠的匹配依据 |
| **node_name** | 节点名称（3D座位号） | STEP转GLB时生成 | 前端高亮零件 |
| **装配体** | 由多个零件组成的组件 | BOM表 | 需要映射到叶子零件 |
| **叶子零件** | 不能再拆分的最小单元 | 3D模型 | 可以直接高亮 |
| **层级结构** | 零件之间的包含关系 | STEP文件解析 | 找到装配体的叶子零件 |
| **DFS** | 深度优先搜索（一条路走到黑） | 算法 | 收集叶子零件 |
| **映射** | 建立对应关系（通讯录） | 匹配结果 | BOM代号 → node_name |

---

### 最重要的3个知识点

#### 1️⃣ product_code是匹配的核心

```
BOM表的product_code（从PDF识别）
    ↕ 匹配
STEP文件的零件名称（包含product_code）
    ↕ 映射
GLB文件的node_name（NAUO1, NAUO2...）
```

**为什么重要**：
- product_code是最可靠的匹配依据（置信度0.90-0.98）
- 比BOM代号更准确（BOM代号可能重复或不规范）
- 比零件名称更精确（名称可能有后缀差异）

#### 2️⃣ 装配体需要映射到叶子零件

```
问题：
BOM表说"安装挂架组件"
但3D模型中没有"挂架组件"这个几何体

解决方案：
通过层级结构找到"挂架组件"包含的所有叶子零件
然后高亮这些叶子零件

效果：
用户看到"挂架组件"的所有零件同时高亮
清楚地知道要装哪些零件
```

#### 3️⃣ 产品图和组件图的处理策略完全不同

```
组件图：
- 扁平结构，无层级
- 只匹配零件
- 简单直接

产品图：
- 树形结构，有层级
- 匹配零件 + 映射装配体
- 复杂但完整
```

---

### 调试技巧

**查看层级结构**：
```bash
cat output/{task_id}/step_assembly_hierarchy.json
```

**查看AI匹配调试文件**：
```bash
cat output/{task_id}/ai_matching_debug_{timestamp}.json
```

**查看BOM映射宽表**：
```bash
cat output/{task_id}/step4_matching_result.json
```

**检查匹配率**：
```json
{
  "bom_match_rate": 0.95,  // ≥0.95优秀，≥0.90良好
  "part_coverage_rate": 0.98,
  "high_confidence_rate": 0.85  // ≥0.80优秀
}
```

---

**文档结束** 🎉

**如果还有疑问，请参考**：
- 术语解释章节（第0章）
- 完整示例（第5.5.2节）
- 关键代码位置（第7章）