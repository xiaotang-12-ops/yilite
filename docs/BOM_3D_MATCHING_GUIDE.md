# BOM表与3D模型匹配方案

## 📋 概述

本文档描述了如何将PDF工程图纸中的BOM表与STEP 3D模型进行匹配，并生成带有装配指导的GLB文件。

---

## 🎯 目标

1. **保留装配层级** - STEP文件转GLB时保留所有零件的独立性
2. **BOM匹配** - 将3D模型中的零件与BOM表进行智能匹配
3. **装配指导集成** - 结合视觉模型的分析结果，为每个零件提供装配指导
4. **支持交互** - 前端可以实现零件高亮、爆炸图动画等功能

---

## 🔄 完整流程

### **步骤1: PDF解析（双通道）**

```
PDF文件
  ├─ 文本通道 → 提取BOM表（53个零件）
  └─ 视觉通道 → 装配专家分析（CoT推理）
       ├─ 整体理解
       ├─ 零件装配指导
       ├─ 紧固件识别
       └─ 装配顺序建议
```

**输出：**
- `bom_candidates`: BOM表数据
- `vision_analysis`: 视觉模型分析结果

---

### **步骤2: STEP转GLB（保留装配层级）**

```python
from processors.file_processor import ModelProcessor

processor = ModelProcessor()
result = processor.step_to_glb(
    step_path="product.step",
    output_path="product.glb",
    scale_factor=0.001  # mm -> m
)

# 结果包含：
# - parts_count: 零件数量
# - parts_info: 零件列表（node_name, geometry_name）
```

**关键点：**
- ✅ 使用 `force='scene'` 保留装配结构
- ✅ **不合并**零件，保持独立性
- ✅ 提取零件节点信息

---

### **步骤3: BOM匹配**

```python
from processors.model_bom_matcher import ModelBOMMatcher

matcher = ModelBOMMatcher()

# 加载BOM表
matcher.load_bom(bom_items)

# 从STEP提取零件
parts = matcher.extract_parts_from_step("product.step")

# 执行匹配
matched_pairs = matcher.match_parts_to_bom(parts, bom_items)
```

**匹配策略：**

1. **策略1: 零件代号完全匹配** (置信度 1.0)
   - 检查BOM代号是否在节点名称中
   - 例如：`01.09.2549` 匹配 `Part_01.09.2549`

2. **策略2: 零件代号部分匹配** (置信度 0.9)
   - 去除特殊字符后匹配
   - 例如：`01-09-2549` 匹配 `Part_01092549`

3. **策略3: 名称相似度匹配** (置信度 0.6-0.8)
   - 使用字符串相似度算法
   - 例如：`连接器后座组件` 匹配 `Connector_Base_Assembly`

**输出：**
```json
{
  "part": {
    "node_name": "Part_01.09.2549",
    "geometry_name": "Mesh_001"
  },
  "bom_item": {
    "seq": 1,
    "code": "01.09.2549",
    "name": "T-SPV1830-EURO-01 连接器后座组件",
    "qty": 1,
    "weight": 77.27
  },
  "confidence": 1.0,
  "match_reason": "零件代号完全匹配: 01.09.2549"
}
```

---

### **步骤4: 生成GLB元数据**

```python
metadata = matcher.generate_glb_metadata(
    glb_path="product.glb",
    matched_pairs=matched_pairs,
    vision_result=vision_analysis
)

matcher.save_metadata(metadata, "product_metadata.json")
```

**元数据结构：**
```json
{
  "glb_file": "product.glb",
  "total_parts": 12,
  "matched_parts": 10,
  "parts": [
    {
      "part_id": "part_000",
      "node_name": "Part_01.09.2549",
      "geometry_name": "Mesh_001",
      "match_confidence": 1.0,
      "bom": {
        "seq": 1,
        "code": "01.09.2549",
        "name": "T-SPV1830-EURO-01 连接器后座组件",
        "qty": 1,
        "weight": 77.27
      },
      "assembly_guide": {
        "sequence": 1,
        "process_requirements": [
          "清洁所有配合面，去除油污和毛刺",
          "使用水平仪校准底座平面度"
        ],
        "key_points": [
          "此零件为整个组件的基准件，必须首先装配"
        ],
        "tools_needed": ["水平仪", "扭矩扳手"],
        "fasteners_used": [
          {
            "bom_code": "02.03.0458",
            "name": "M30*60 六角头螺栓",
            "qty": 6,
            "torque": "150Nm"
          }
        ],
        "safety_notes": ["吊装时使用专用吊具"]
      }
    }
  ]
}
```

---

## 🎨 前端集成

### **1. 加载GLB和元数据**

```typescript
// 加载GLB模型
const loader = new GLTFLoader()
const gltf = await loader.loadAsync('/models/product.glb')

// 加载元数据
const metadata = await fetch('/models/product_metadata.json').then(r => r.json())

// 建立零件映射
const partMap = new Map()
metadata.parts.forEach(part => {
  const node = gltf.scene.getObjectByName(part.node_name)
  if (node) {
    partMap.set(part.part_id, {
      node: node,
      bom: part.bom,
      guide: part.assembly_guide
    })
  }
})
```

### **2. 零件高亮**

```typescript
function highlightPart(partId: string) {
  const part = partMap.get(partId)
  if (part) {
    // 高亮显示
    part.node.material.emissive.setHex(0xff0000)
    
    // 显示装配指导
    showAssemblyGuide(part.guide)
  }
}
```

### **3. 爆炸图动画**

```typescript
function explodeView(factor: number) {
  const center = new THREE.Vector3()
  
  metadata.parts.forEach(part => {
    const node = partMap.get(part.part_id)?.node
    if (node) {
      const direction = node.position.clone().sub(center).normalize()
      node.position.copy(
        node.position.clone().add(direction.multiplyScalar(factor))
      )
    }
  })
}
```

### **4. 分步装配**

```typescript
function showAssemblyStep(stepNumber: number) {
  // 隐藏所有零件
  metadata.parts.forEach(part => {
    const node = partMap.get(part.part_id)?.node
    if (node) node.visible = false
  })
  
  // 显示当前步骤及之前的零件
  metadata.parts
    .filter(p => p.assembly_guide.sequence <= stepNumber)
    .forEach(part => {
      const node = partMap.get(part.part_id)?.node
      if (node) node.visible = true
    })
}
```

---

## 📊 优化建议

### **1. 提高匹配准确率**

**方法1: 优化提示词**
- 要求视觉模型输出零件的3D模型节点名称
- 在提示词中说明STEP文件的命名规范

**方法2: 使用正则表达式**
- 提取零件代号的模式（如 `\d{2}\.\d{2}\.\d{4}`）
- 在节点名称中查找匹配

**方法3: 人工校正**
- 提供前端界面，允许用户手动调整匹配
- 保存校正结果，用于训练匹配算法

### **2. 处理未匹配零件**

```python
# 对于未匹配的零件，使用启发式规则
unmatched_parts = [p for p in matched_pairs if p["bom_item"] is None]

for pair in unmatched_parts:
    # 根据位置、大小等特征推测
    # 或者标记为"待确认"
    pass
```

---

## 🧪 测试

### **运行测试脚本**

```bash
# 仅测试BOM提取和视觉分析
python test_bom_matching.py --mode bom-only

# 测试完整流程（需要STEP文件）
python test_bom_matching.py --mode full
```

### **预期输出**

```
✅ 测试完成！结果摘要
================================================================================

📊 统计信息:
   BOM项目总数: 53
   3D模型零件数: 12
   成功匹配: 10/12

📁 输出文件:
   GLB模型: test_output/bom_matching/product_model.glb
   元数据: test_output/bom_matching/product_model_metadata.json

🔗 匹配详情:
   1. Part_01.09.2549
      → BOM: 01.09.2549 - T-SPV1830-EURO-01 连接器后座组件
      → 置信度: 1.00
   2. Part_01.09.2550
      → BOM: 01.09.2550 - T-SPV1830-EURO-02 后座连接架组件
      → 置信度: 1.00
   ...
```

---

## 📝 总结

### **已完成：**
1. ✅ 前端修改为仅支持STEP格式
2. ✅ GLB转换优化（保留装配层级）
3. ✅ BOM匹配模块实现
4. ✅ 元数据生成功能
5. ✅ 测试脚本

### **下一步：**
1. 🔜 测试实际STEP文件的转换和匹配
2. 🔜 前端集成GLB加载和交互
3. 🔜 优化匹配算法
4. 🔜 添加人工校正界面

