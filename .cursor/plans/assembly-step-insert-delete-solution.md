# 装配步骤插入/删除技术方案

> **创建日期**: 2025-12-02
> **状态**: 待实现
> **相关需求**: 阶段5 - 5.2 插入新步骤
> **关联文档**: `yilite-system-upgrade-072ca783.plan.md`

---

## 🎯 本方案要解决的问题

### 核心需求
管理员需要能够在已生成的装配手册中**插入新步骤**或**删除现有步骤**，而不破坏整个装配流程的完整性。

### 当前痛点

1. **step_id 不稳定**
   - 当前 `step_id = 组件图1_step_3` 依赖 step_number
   - 插入步骤后，所有后续步骤的 step_id 都会变化
   - 导致版本追溯、外部引用全部失效

2. **累积零件显示问题**
   - 装配是累积的：步骤N应显示步骤1~N的所有已装配零件
   - 插入步骤后，后续步骤的累积列表需要包含新零件
   - 如果存储累积列表，需要修改所有后续步骤 → 复杂且易出错

3. **3D 显示效果需求**
   - 初始状态：模型爆炸开（所有零件分散）
   - 逐步点击"下一步"：零件逐个归位，模型慢慢拼接完整
   - 当前步骤的零件需要**高亮显示**

### 本方案的解决策略

| 问题 | 解决策略 |
|------|---------|
| step_id 不稳定 | 使用 UUID 生成，与 step_number 解耦 |
| 步骤排序 | 新增 `display_order` 字段，插入时取中间值 |
| 累积零件 | **不存储**，前端实时计算（按步骤顺序累加） |
| 3D 显示 | 爆炸归位 + 当前步骤高亮 |

### 最终效果

```
插入步骤后：
- ✅ 所有 step_id 保持不变
- ✅ 后续步骤的数据无需修改
- ✅ 3D 显示自动正确（累积列表实时计算）
- ✅ 当前步骤零件高亮，已装配零件归位，未装配零件爆炸+半透明
```

---

## ⚠️ 落地差距与前置依赖（必读）

> **重要**：以下是方案落地前必须解决的现实约束，跳过任何一项都会导致功能不可用。



**必须修改**：
- [ ] 提示词输出格式增加 `display_order` 字段
- [ ] 允许 step_id 使用 UUID 格式
- [ ] 允许新增零件（不在原BOM中）

### 2. 后端/存储现状差距（🟡 中阻力）

| 文件 | 现状 | 需要改动 |
|------|------|---------|
| `core/manual_integrator_v2.py` (302-335行) | 用 step_number 生成 step_id，无 display_order | 改为 UUID + display_order |
| `core/storage.py` | 迁移只做版本归档，无 step_id→UUID 迁移 | 增加旧格式迁移 + 旧ID映射保留 |
| `backend/simple_app.py` (698+行) | 无 `_edit_version` 乐观锁 | 增加版本号检查 |
| 输出文件 `assembly_manual.json` | 旧格式（step_number持久化、无display_order） | 新生成需包含新字段 |

### 3. 前端现状差距（🟡 中阻力）

| 位置 | 现状 | 需要改动 |
|------|------|---------|
| `ManualViewer.vue` allSteps (819-880行) | 按 step_number 顺序拼接，不看 display_order | 改为按 display_order 排序 |
| 3D 逻辑 (1720-2250行) | 手动爆炸/收起 + 当前步高亮，无累积归位 | 新增"初始爆炸→逐步归位"逻辑 |
| 高亮逻辑 (945-1015行) | 依赖 parts_used.node_name，多数量同编码会被合并 | 需支持多实例、新零件无 node_name 的情况 |
| step_number 引用 (900+行) | 安全提示、质检列表等多处引用 step_number | 需全量梳理，改为动态计算值 |

### 4. 3D 资产与新增零件入口（🔴 高阻力）

**核心问题**：新方案假设"插入的新3D零件"已有GLB节点可用，但：

| 问题 | 现状 | 影响 |
|------|------|------|
| GLB节点验证 | 缺少 `step3_glb_inventory.json`，无法验证 node_name 覆盖率 | 不确定哪些零件有3D节点 |
| 新增零件入口 | 没有 per-step glb_file 或追加GLB的机制 | 新增零件无法可视化 |
| GLB载入逻辑 | 按 component_x.glb / product_total.glb 载入，无法动态引入新模型 | 爆炸/高亮对新零件失效 |

**待确认**：
- [ ] GLB 节点命名是否与 node_name 一致？
- [ ] 新增零件如何提供模型/节点命名？
- [ ] 是否需要支持动态加载额外的 GLB 文件？

**关于 step3_glb_inventory.json**：
- 代码位置：`core/hierarchical_bom_matcher_v2.py` 第 487-503 行
- 预期输出：`output/{task_id}/step3_glb_inventory.json`
- **当前状态**：代码存在但未生成文件！
- 原因分析：第 502-503 行有 `try-except` 静默捕获异常
- **修复建议**：在 except 中打印详细错误信息，排查具体失败原因

### 5. 新增零件入口策略（已明确）

用户提供的新增零件交互流程：
```
┌─────────────────────────────────────────────────────────────┐
│  用户点击"添加新零件"按钮                                   │
│           ↓                                                 │
│  弹出文件选择框，用户上传 STEP 文件                         │
│           ↓                                                 │
│  后端自动将 STEP 转换为 GLB                                 │
│  （复用 processors/step_to_glb_converter.py）               │
│           ↓                                                 │
│  前端加载新的 GLB 到场景中                                  │
│           ↓                                                 │
│  用户拖拽新零件，磁吸到目标位置                             │
│           ↓                                                 │
│  保存新零件的位置和关联信息到 assembly_manual.json          │
└─────────────────────────────────────────────────────────────┘
```

**需要新增的功能**：
- [ ] 前端：添加新零件按钮 + STEP 上传组件
- [ ] 后端：STEP 上传 → GLB 转换 API
- [ ] 前端：GLB 动态加载到 Three.js 场景
- [ ] 前端：拖拽定位 + 磁吸对齐功能
- [ ] 后端：保存新零件信息到草稿

### 5. 迁移与版本历史风险（🟡 中阻力）

| 风险 | 说明 | 应对 |
|------|------|------|
| 历史版本对比失效 | 旧 step_id 替换为 UUID 后，历史版本无法与当前草稿对比 | 需保留旧ID映射或在版本文件中保留旧字段 |
| step_number 引用断裂 | 多处 UI/质检引用 step_number，改为动态计算可能空值或错位 | 全量梳理引用点 |

### 6. 落地优先级建议

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 0: 前置调研（必须先完成）                            │
│  ├─ [ ] 确认 GLB 节点命名与 node_name 的对应关系           │
│  ├─ [ ] 确认新增零件的 3D 入口策略（追加GLB？手动绑定？）   │
│  └─ [ ] 梳理 step_number 的所有引用点                      │
├─────────────────────────────────────────────────────────────┤
│  Phase 2: 后端 API + 迁移                                   │
│  ├─ [ ] 插入/删除/移动 API                                 │
│  ├─ [ ] 旧数据迁移（保留旧ID映射）                         │
│  └─ [ ] 乐观锁版本号                                       │
├─────────────────────────────────────────────────────────────┤
│  Phase 3: 前端适配                                          │
│  ├─ [ ] allSteps 按 display_order 排序                     │
│  ├─ [ ] step_number 动态计算 + 引用点修复                  │
│  └─ [ ] 插入/删除 UI                                       │
├─────────────────────────────────────────────────────────────┤
│  Phase 4: 3D 累积归位 + 高亮                                │
│  ├─ [ ] 初始爆炸 → 逐步归位逻辑                            │
│  ├─ [ ] 当前步骤高亮 + 已装配正常色 + 未装配半透明         │
│  └─ [ ] 支持新增零件的可视化（待 Phase 0 确认方案）        │
└─────────────────────────────────────────────────────────────┘
```

---

## 一、问题详细描述

### 1.1 当前系统架构

当前 `step_id` 生成规则（`core/manual_integrator_v2.py`）：
```python
# 组件装配步骤：{component_code}_step_{step_number}
# 产品装配步骤：product_step_{step_number}
step_id = f"{component_code}_step_{step_number}"
```

### 1.2 核心问题

装配步骤是**环环相扣**的，插入或删除某个步骤会产生两个问题：

**问题1：step_id 不稳定**
- 当前 step_id 依赖 step_number
- 插入步骤3后，原步骤4的 step_id 从 `组件图1_step_4` 变成 `组件图1_step_5`
- 影响：版本追溯失效、外部引用断裂

**问题2：累积零件显示**
- 装配是累积的：步骤N应显示步骤1~N的所有已装配零件
- 插入步骤后，后续所有步骤的"累积零件列表"都需要包含新零件

### 1.3 用户原方案评估

用户提出：仅使用 `step_number` 做前端渲染，插入新步骤时让后续所有步骤的 `step_number` 自动 +1

| 风险点 | 严重程度 | 说明 |
|-------|---------|------|
| step_id不稳定 | 🔴 严重 | 所有后续step_id都会变化 |
| 历史数据追溯 | 🔴 严重 | 版本间无法通过step_id对比 |
| 累积零件更新 | 🔴 严重 | 需要修改所有后续步骤的数据 |
| 数据一致性 | 🟡 中等 | 批量更新可能部分失败 |
| 并发操作 | 🟡 中等 | 两人同时编辑可能冲突 |

---

## 二、推荐方案概述

### 2.1 核心设计原则

1. **step_id 稳定性**：基于 UUID 生成，一旦创建永不改变
2. **display_order 排序**：独立排序字段，插入时取中间值
3. **step_number 动态计算**：前端根据排序结果实时计算，不存储
4. **累积零件实时计算**：不存储累积列表，前端按步骤顺序累加
5. **爆炸视图逐步归位**：初始爆炸开，逐步点击后零件归位拼接

### 2.2 3D显示效果（用户期望）

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   初始状态          点击步骤1       点击步骤2       最终    │
│   (爆炸开)          (A归位)         (A B归位)      (完整)   │
│                                                             │
│    A   B   C   D  →  [A]  B C D  →  [A B]  C D  →  [ABCD]  │
│    ↑   ↑   ↑   ↑      ↑   ↑ ↑ ↑       ↑    ↑ ↑            │
│   全部散开          A移动归位     A B归位        全部归位   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 关键洞察

**累积列表不应该被存储，而应该被实时计算！**

| 方式 | 问题 |
|------|------|
| ❌ 存储累积列表 | 插入步骤时需要修改所有后续步骤 → 复杂且易出错 |
| ✅ 实时计算 | 每个步骤只存储自己的零件，显示时按顺序累加 → 无副作用 |

**为什么这个设计能解决"插入步骤后续零件归位"的问题？**

```
原始：步骤1[A] → 步骤2[B] → 步骤3[C]
      到步骤3时，累积归位 = [A, B, C]

插入X后：步骤1[A] → 步骤2[B] → 步骤3[X] → 步骤4[C]
         到步骤4时，累积归位 = [A, B, X, C]  ← X自动包含！

关键：步骤4的数据完全不需要修改，累积列表是实时计算的
```

---

## 三、数据结构设计

### 3.1 新版步骤数据结构

```json
{
  "step_id": "step_a1b2c3d4e5f6",  // UUID-based，永久稳定
  "display_order": 2000,            // 排序权重，间隔1000
  "action": "焊接侧板",
  "description": "...",
  "parts_used": [                   // ✅ 只存储本步骤新增的零件
    {
      "bom_seq": "2",
      "bom_code": "01.09.1144",
      "bom_name": "主框架组件",
      "node_name": ["NAUO273", "NAUO272", "NAUO271"]
    }
  ],
  "welding": {...},
  "safety_warnings": [...],
  "drawings": [...]
}
```

### 3.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `step_id` | string | UUID格式，如 `step_a1b2c3d4e5f6`，创建后不变 |
| `display_order` | number | 排序权重，初始间隔1000（1000, 2000, 3000...） |
| `step_number` | number | **不存储**，前端按 display_order 排序后动态计算 |
| `parts_used` | array | 只存储当前步骤新增的零件，不存储累积列表 |

### 3.3 新旧格式对比

```diff
{
- "step_id": "组件图1_step_3",      // 旧：基于step_number，会变化
+ "step_id": "step_a1b2c3d4e5f6",   // 新：基于UUID，永久稳定
+ "display_order": 3000,             // 新增：排序权重
  "step_number": 3,                  // 保留但不存储，动态计算
  "action": "...",
  "parts_used": [...]                // 不变：只存储当前步骤的零件
}
```

### 3.4 补充说明（落地时必须遵守）

- UUID + display_order 由后端代码生成：初始生成流程自动赋值，插入接口再生成新的 UUID 并计算 display_order；前端只按 display_order 排序并动态计算 step_number，智能体无需输出这两个字段。
- 新增零件必须把转换后 GLB 的节点名写入步骤的 `node_name`（一个零件多个节点时用数组）；节点名需唯一且可在 GLB 中找到，否则无法高亮/归位。若暂时没有 GLB，可先插入文字步骤但无法 3D 显示。

---

## 四、后端实现

### 4.1 修改 step_id 生成逻辑

**文件**: `core/manual_integrator_v2.py`

```python
import uuid

def _add_step_ids(self, steps, component_code, step_type):
    """为每个步骤添加全局唯一的 step_id 和 display_order"""
    enhanced_steps = []

    for i, step in enumerate(steps):
        step_copy = step.copy()

        # 新规则：基于UUID生成稳定的step_id
        step_id = f"step_{uuid.uuid4().hex[:12]}"

        # 新增：排序权重（间隔1000）
        display_order = (i + 1) * 1000

        step_copy["step_id"] = step_id
        step_copy["display_order"] = display_order
        enhanced_steps.append(step_copy)

    return enhanced_steps
```

### 4.2 新增 API 接口

**文件**: `backend/simple_app.py`

#### 4.2.1 插入步骤

```python
class InsertStepRequest(BaseModel):
    chapter_type: str  # "component_assembly" 或 "product_assembly"
    component_code: Optional[str] = None  # component_assembly 时需要
    after_step_id: Optional[str] = None  # 在哪个步骤后插入，None表示开头
    new_step: Dict[str, Any]  # 新步骤数据

@app.post("/api/manual/{task_id}/steps/insert")
async def insert_step(task_id: str, request: InsertStepRequest):
    """插入新步骤"""
    storage = get_storage(task_id)
    draft = storage.load_draft() or storage.load_published()

    # 获取目标步骤列表
    steps = get_steps_by_chapter(draft, request.chapter_type, request.component_code)

    # 计算插入位置的 display_order
    new_order = calculate_insert_order(steps, request.after_step_id)

    # 生成新步骤
    new_step = {
        "step_id": f"step_{uuid.uuid4().hex[:12]}",
        "display_order": new_order,
        **request.new_step
    }

    # 插入到草稿
    insert_step_to_draft(draft, new_step, request.chapter_type, request.component_code)
    storage.save_draft(draft)

    return {
        "success": True,
        "step_id": new_step["step_id"],
        "display_order": new_order
    }
```

#### 4.2.2 删除步骤

```python
@app.delete("/api/manual/{task_id}/steps/{step_id}")
async def delete_step(task_id: str, step_id: str):
    """删除步骤"""
    storage = get_storage(task_id)
    draft = storage.load_draft() or storage.load_published()

    # 获取被删除步骤的零件（用于提示）
    deleted_parts = get_step_parts(draft, step_id)

    # 从草稿中删除
    remove_step_from_draft(draft, step_id)
    storage.save_draft(draft)

    return {
        "success": True,
        "deleted_step_id": step_id,
        "affected_parts": deleted_parts  # 返回被影响的零件，前端可提示
    }
```

#### 4.2.3 移动步骤

```python
class MoveStepRequest(BaseModel):
    step_id: str
    after_step_id: Optional[str] = None  # 移动到此步骤之后，None表示移动到开头

@app.post("/api/manual/{task_id}/steps/move")
async def move_step(task_id: str, request: MoveStepRequest):
    """移动步骤位置"""
    storage = get_storage(task_id)
    draft = storage.load_draft() or storage.load_published()

    # 获取步骤所在章节
    chapter_type, component_code = find_step_location(draft, request.step_id)
    steps = get_steps_by_chapter(draft, chapter_type, component_code)

    # 计算新的 display_order
    new_order = calculate_insert_order(
        [s for s in steps if s["step_id"] != request.step_id],
        request.after_step_id
    )

    # 更新步骤的 display_order
    update_step_order(draft, request.step_id, new_order)
    storage.save_draft(draft)

    return {"success": True, "new_display_order": new_order}
```

### 4.3 display_order 计算函数

```python
def calculate_insert_order(steps: List[Dict], after_step_id: Optional[str]) -> int:
    """计算插入位置的 display_order"""
    if not steps:
        return 1000

    sorted_steps = sorted(steps, key=lambda s: s.get("display_order", 0))

    if not after_step_id:
        # 插入到开头
        first_order = sorted_steps[0].get("display_order", 1000)
        return first_order // 2 if first_order > 1 else 500

    # 找到目标位置
    for i, step in enumerate(sorted_steps):
        if step["step_id"] == after_step_id:
            if i + 1 < len(sorted_steps):
                # 中间插入：取平均值
                prev_order = step["display_order"]
                next_order = sorted_steps[i + 1]["display_order"]
                new_order = (prev_order + next_order) // 2

                # 检查是否需要重整（空间不足）
                if new_order == prev_order or new_order == next_order:
                    rebalance_orders(sorted_steps)
                    return calculate_insert_order(sorted_steps, after_step_id)
                return new_order
            else:
                # 追加到末尾
                return step["display_order"] + 1000

    raise ValueError(f"Step not found: {after_step_id}")


def rebalance_orders(steps: List[Dict]) -> None:
    """重整所有步骤的 display_order"""
    sorted_steps = sorted(steps, key=lambda s: s.get("display_order", 0))
    for i, step in enumerate(sorted_steps):
        step["display_order"] = (i + 1) * 1000
```


### 4.4 数据迁移逻辑

**文件**: `core/storage.py`

```python
import uuid

def migrate_legacy_steps(manual_data: Dict) -> Dict:
    """迁移旧格式步骤数据到新格式"""
    migrated = False

    def migrate_step(step: Dict, index: int) -> Dict:
        nonlocal migrated
        step_id = step.get("step_id", "")

        # 检测是否为旧格式（step_id以数字结尾，如 组件图1_step_3）
        is_legacy = "_step_" in step_id and step_id.split("_step_")[-1].isdigit()

        if is_legacy or "display_order" not in step:
            migrated = True
            # 生成新的 UUID-based step_id
            step["step_id"] = f"step_{uuid.uuid4().hex[:12]}"
            # 根据原有顺序计算 display_order
            step["display_order"] = (index + 1) * 1000

        return step

    # 迁移组件装配步骤
    for component in manual_data.get("component_assembly", []):
        component["steps"] = [
            migrate_step(s, i) for i, s in enumerate(component.get("steps", []))
        ]

    # 迁移产品装配步骤
    if "product_assembly" in manual_data and "steps" in manual_data["product_assembly"]:
        manual_data["product_assembly"]["steps"] = [
            migrate_step(s, i)
            for i, s in enumerate(manual_data["product_assembly"].get("steps", []))
        ]

    if migrated:
        manual_data["_migrated_to_v2"] = True

    return manual_data
```

---

## 五、前端实现

### 5.1 排序与 step_number 计算

**文件**: `frontend/src/views/ManualViewer.vue`

```typescript
// 按 display_order 排序并计算 step_number
const sortedSteps = computed(() => {
  const steps: StepData[] = []

  // 1. 收集所有步骤（现有逻辑保持不变）
  for (const component of (manualData.value?.component_assembly || [])) {
    for (const step of (component.steps || [])) {
      steps.push({
        ...step,
        chapter_type: 'component_assembly',
        component_code: component.component_code,
        component_name: component.component_name,
        glb_file: component.glb_file
      })
    }
  }

  // 产品装配步骤
  for (const step of (manualData.value?.product_assembly?.steps || [])) {
    steps.push({
      ...step,
      chapter_type: 'product_assembly',
      glb_file: 'product_total.glb'
    })
  }

  // 2. 按 display_order 排序
  steps.sort((a, b) => (a.display_order || 0) - (b.display_order || 0))

  // 3. 动态计算 step_number（仅用于显示）
  steps.forEach((step, index) => {
    step.step_number = index + 1
  })

  return steps
})

// 替换原来的 allSteps
const allSteps = sortedSteps
```

### 5.2 累积零件计算

```typescript
// 计算到当前步骤之前已装配的零件（用于绿色显示）
const previouslyAssembledParts = computed(() => {
  const assembled = new Map<string, any>()  // bom_code -> part

  for (let i = 0; i < currentStepIndex.value; i++) {
    const step = sortedSteps.value[i]
    const partsUsed = step.parts_used || step.components || step.fasteners || []

    for (const part of partsUsed) {
      const key = part.bom_code || part.bom_seq
      if (key && !assembled.has(key)) {
        assembled.set(key, part)
      }
    }
  }

  return Array.from(assembled.values())
})

// 当前步骤正在装配的零件（用于黄色高亮）
const currentStepParts = computed(() => {
  const step = currentStepData.value
  return step?.parts_used || step?.components || step?.fasteners || []
})

// 累积到当前步骤的所有零件（包含当前步骤）
const accumulatedParts = computed(() => {
  const parts = [...previouslyAssembledParts.value]
  for (const part of currentStepParts.value) {
    const key = part.bom_code || part.bom_seq
    if (key && !parts.find(p => (p.bom_code || p.bom_seq) === key)) {
      parts.push(part)
    }
  }
  return parts
})
```

### 5.3 爆炸视图逐步归位（核心效果）

**用户期望效果**：
- 初始状态：模型是**爆炸开**的（所有零件分散）
- 逐步点击"下一步"：零件一个一个**移动到正确位置**，模型慢慢拼接完整
- 最终：所有零件归位，模型完整

```
┌─────────────────────────────────────────────────────────────┐
│  初始（爆炸状态）    步骤1        步骤2        最终（完整）  │
│                                                             │
│    A   B   C   D  →  [A]  B C D →  [A B]  C D →  [A B C D]  │
│    ↑   ↑   ↑   ↑      ↑   ↑ ↑ ↑      ↑     ↑ ↑              │
│   爆炸位置          A归位        A B归位       全部归位     │
└─────────────────────────────────────────────────────────────┘
```

#### 5.3.1 数据结构：记录爆炸位置

每个零件需要存储两个位置：
- `originalPosition`：正确装配位置（从GLB加载时获取）
- `explodedPosition`：爆炸位置（根据算法计算）

```typescript
// 零件位置映射
interface PartPosition {
  originalPosition: THREE.Vector3  // 正确装配位置
  explodedPosition: THREE.Vector3  // 爆炸位置
}

const partPositions = new Map<string, PartPosition>()

// 加载模型时，计算并存储每个零件的位置
const initPartPositions = () => {
  const modelCenter = new THREE.Vector3()
  const box = new THREE.Box3().setFromObject(model)
  box.getCenter(modelCenter)

  model.traverse((child: any) => {
    if (child.isMesh) {
      // 原始位置
      const originalPos = child.position.clone()

      // 计算爆炸位置（从中心向外扩散）
      const direction = originalPos.clone().sub(modelCenter).normalize()
      const explodedPos = originalPos.clone().add(direction.multiplyScalar(explodeDistance))

      partPositions.set(child.name, {
        originalPosition: originalPos,
        explodedPosition: explodedPos
      })

      // 初始状态：所有零件在爆炸位置
      child.position.copy(explodedPos)
    }
  })
}
```

#### 5.3.2 步骤切换：逐步归位

```typescript
// 已装配的零件 node_name 列表（累积计算）
const assembledNodeNames = computed(() => {
  const names: string[] = []

  // 累积到当前步骤（包含当前步骤）
  for (let i = 0; i <= currentStepIndex.value; i++) {
    const step = sortedSteps.value[i]
    const partsUsed = step.parts_used || step.components || step.fasteners || []

    for (const part of partsUsed) {
      if (part.node_name) {
        if (Array.isArray(part.node_name)) {
          names.push(...part.node_name)
        } else {
          names.push(part.node_name)
        }
      }
    }
  }

  return names
})

// 更新零件位置（根据是否已装配）
const updatePartPositions = (animate: boolean = true) => {
  const assembled = new Set(assembledNodeNames.value)

  model.traverse((child: any) => {
    if (child.isMesh && partPositions.has(child.name)) {
      const positions = partPositions.get(child.name)!

      // 目标位置：已装配→原始位置，未装配→爆炸位置
      const targetPos = assembled.has(child.name)
        ? positions.originalPosition
        : positions.explodedPosition

      if (animate) {
        // 带动画过渡
        animateToPosition(child, targetPos, 500)  // 500ms动画
      } else {
        child.position.copy(targetPos)
      }
    }
  })
}

// 动画过渡函数
const animateToPosition = (mesh: THREE.Mesh, targetPos: THREE.Vector3, duration: number) => {
  const startPos = mesh.position.clone()
  const startTime = Date.now()

  const animate = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)

    // 使用 easeOutCubic 缓动
    const eased = 1 - Math.pow(1 - progress, 3)

    mesh.position.lerpVectors(startPos, targetPos, eased)

    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }

  animate()
}

// 监听步骤变化
watch(currentStepIndex, () => {
  updatePartPositions(true)  // 带动画
})
```

#### 5.3.3 高亮当前步骤零件 + 位置归位

**完整效果**：位置变化 + 颜色变化

| 零件状态 | 位置 | 颜色 |
|---------|------|------|
| 当前步骤正在装配 | 归位 | 🟡 **高亮（黄色发光）** |
| 之前步骤已装配 | 归位 | 正常颜色（蓝色） |
| 未装配 | 爆炸位置 | 半透明灰色 |

```typescript
// 当前步骤的零件 node_name（用于高亮）
const currentStepNodeNames = computed(() => {
  const step = currentStepData.value
  const partsUsed = step?.parts_used || step?.components || step?.fasteners || []

  return partsUsed.flatMap((part: any) => {
    if (Array.isArray(part.node_name)) return part.node_name
    if (part.node_name) return [part.node_name]
    return []
  })
})

// 之前步骤已装配的零件 node_name（不含当前步骤）
const previouslyAssembledNodeNames = computed(() => {
  const names: string[] = []

  for (let i = 0; i < currentStepIndex.value; i++) {
    const step = sortedSteps.value[i]
    const partsUsed = step.parts_used || step.components || step.fasteners || []

    for (const part of partsUsed) {
      if (part.node_name) {
        if (Array.isArray(part.node_name)) {
          names.push(...part.node_name)
        } else {
          names.push(part.node_name)
        }
      }
    }
  }

  return names
})

// 综合更新：位置 + 颜色
const updateStepDisplay = (animate: boolean = true) => {
  const currentNodes = new Set(currentStepNodeNames.value)
  const previousNodes = new Set(previouslyAssembledNodeNames.value)
  const allAssembled = new Set([...currentNodes, ...previousNodes])

  // 定义材质
  const highlightMaterial = new THREE.MeshStandardMaterial({
    color: 0xffff00,        // 黄色
    emissive: 0xffaa00,
    emissiveIntensity: 0.8,
    metalness: 0.3,
    roughness: 0.4
  })

  const normalMaterial = new THREE.MeshStandardMaterial({
    color: 0x4A90E2,        // 蓝色
    metalness: 0.5,
    roughness: 0.4
  })

  const unassembledMaterial = new THREE.MeshStandardMaterial({
    color: 0x888888,        // 灰色
    opacity: 0.3,
    transparent: true,
    metalness: 0.2,
    roughness: 0.6
  })

  model.traverse((child: any) => {
    if (child.isMesh && partPositions.has(child.name)) {
      const positions = partPositions.get(child.name)!

      // === 1. 位置更新 ===
      const targetPos = allAssembled.has(child.name)
        ? positions.originalPosition   // 已装配：归位
        : positions.explodedPosition   // 未装配：爆炸位置

      if (animate) {
        animateToPosition(child, targetPos, 500)
      } else {
        child.position.copy(targetPos)
      }

      // === 2. 颜色更新 ===
      if (currentNodes.has(child.name)) {
        // 当前步骤：高亮黄色
        child.material = highlightMaterial.clone()
      } else if (previousNodes.has(child.name)) {
        // 之前已装配：正常蓝色
        child.material = normalMaterial.clone()
      } else {
        // 未装配：半透明灰色
        child.material = unassembledMaterial.clone()
      }
    }
  })
}

// 监听步骤变化
watch(currentStepIndex, () => {
  updateStepDisplay(true)  // 带动画
})
```

**视觉效果示意**：

```
步骤3时的显示效果：

  已归位区域                    爆炸区域
┌─────────────────┐       ┌─────────────────┐
│ [A] [B] [C*]    │       │   D   E   F     │
│  蓝  蓝  黄     │       │  灰  灰  灰     │
│                 │       │ (半透明)        │
└─────────────────┘       └─────────────────┘
       ↑                          ↑
  A B 正常色              D E F 保持爆炸
  C 高亮(当前步骤)        半透明灰色
```

### 5.4 插入/删除步骤 UI

```vue
<!-- 插入步骤对话框 -->
<el-dialog v-model="showInsertDialog" title="插入新步骤" width="600px">
  <el-form label-width="100px">
    <el-form-item label="插入位置">
      <el-select v-model="insertAfterStepId" placeholder="选择插入位置">
        <el-option :value="null" label="在开头插入" />
        <el-option
          v-for="step in sortedSteps"
          :key="step.step_id"
          :value="step.step_id"
          :label="`在步骤${step.step_number}「${step.action}」之后`"
        />
      </el-select>
    </el-form-item>

    <el-form-item label="步骤标题">
      <el-input v-model="newStepAction" placeholder="如：安装零件X" />
    </el-form-item>

    <el-form-item label="步骤描述">
      <el-input v-model="newStepDescription" type="textarea" :rows="3" />
    </el-form-item>

    <el-form-item label="使用零件">
      <!-- 零件选择器，从BOM列表中选择 -->
      <el-select v-model="newStepParts" multiple placeholder="选择零件">
        <el-option
          v-for="bom in bomList"
          :key="bom.bom_code"
          :value="bom.bom_code"
          :label="`${bom.bom_seq}. ${bom.bom_name}`"
        />
      </el-select>
    </el-form-item>
  </el-form>

  <template #footer>
    <el-button @click="showInsertDialog = false">取消</el-button>
    <el-button type="primary" @click="handleInsertStep">确认插入</el-button>
  </template>
</el-dialog>

<!-- 删除确认 -->
<script setup>
const deleteStep = async (stepId: string) => {
  const step = sortedSteps.value.find(s => s.step_id === stepId)
  const partsInfo = (step?.parts_used || [])
    .map(p => `${p.bom_name}（BOM序号：${p.bom_seq}）`)
    .join('\n- ')

  const message = partsInfo
    ? `删除此步骤后，以下零件将不再出现在装配流程中：\n- ${partsInfo}\n\n确定要删除吗？`
    : '确定要删除此步骤吗？'

  await ElMessageBox.confirm(message, '删除确认', { type: 'warning' })

  await axios.delete(`/api/manual/${taskId}/steps/${stepId}`)
  await refreshManualData()
  ElMessage.success('步骤已删除')
}
</script>
```

---

## 六、并发安全

### 6.1 乐观锁机制

```python
# 后端：保存时检查版本号
@app.post("/api/manual/{task_id}/save-draft")
async def save_draft(task_id: str, request: SaveDraftRequest):
    storage = get_storage(task_id)
    current = storage.load_draft() or storage.load_published()

    # 版本检查
    current_version = current.get("_edit_version", 0)
    request_version = request.manual_data.get("_edit_version", 0)

    if current_version != request_version:
        raise HTTPException(
            status_code=409,
            detail="数据已被其他用户修改，请刷新后重试"
        )

    # 递增版本号
    request.manual_data["_edit_version"] = request_version + 1
    storage.save_draft(request.manual_data)

    return {"success": True}
```

### 6.2 前端冲突处理

```typescript
const saveDraft = async () => {
  try {
    await axios.post(`/api/manual/${taskId}/save-draft`, {
      manual_data: { ...updatedData, _edit_version: manualData.value._edit_version }
    })
    ElMessage.success('保存成功')
  } catch (error: any) {
    if (error.response?.status === 409) {
      ElMessageBox.confirm(
        '数据已被其他用户修改，是否刷新页面获取最新数据？',
        '版本冲突',
        { type: 'warning' }
      ).then(() => location.reload())
    } else {
      ElMessage.error('保存失败: ' + error.message)
    }
  }
}
```

---

## 七、操作场景验证

### 7.1 场景1：在步骤2后插入新步骤

**操作前：**
```
步骤1 (order:1000): parts_used: [A]
步骤2 (order:2000): parts_used: [B]
步骤3 (order:3000): parts_used: [C]
```

**执行插入：**
```json
POST /api/manual/{task_id}/steps/insert
{
  "chapter_type": "component_assembly",
  "component_code": "组件图1",
  "after_step_id": "步骤2的ID",
  "new_step": {
    "action": "安装零件X",
    "parts_used": [{ "bom_code": "X", "node_name": ["NAUO_X"] }]
  }
}
```

**操作后：**
```
步骤1 (order:1000): parts_used: [A]
步骤2 (order:2000): parts_used: [B]
步骤3 (order:2500): parts_used: [X]  ← 新增，只存储X
步骤4 (order:3000): parts_used: [C]  ← 不需要修改！
```

**3D爆炸归位 + 高亮效果（在步骤4时）：**
```
初始（全爆炸）：  A   B   X   C   D   E   （全部散开，灰色半透明）
                 灰  灰  灰  灰  灰  灰

步骤1后：       [A*] B   X   C   D   E   （A归位+高亮，其他灰色爆炸）
                 黄  灰  灰  灰  灰  灰

步骤2后：       [A  B*]  X   C   D   E   （A B归位，B高亮）
                 蓝  黄  灰  灰  灰  灰

步骤3后：       [A   B  X*]  C   D   E   （A B X归位，X高亮）← X自动包含
                 蓝  蓝  黄  灰  灰  灰

步骤4后：       [A   B   X  C*]  D   E   （A B X C归位，C高亮）
                 蓝  蓝  蓝  黄  灰  灰

图例：黄=当前步骤高亮  蓝=已装配正常色  灰=未装配半透明
```

✅ **关键优势**：不需要修改原步骤3的任何数据，X自动出现在后续步骤的累积列表中

### 7.2 场景2：删除步骤2

**操作后：**
```
步骤1 (order:1000): parts_used: [A]
步骤2 (order:2500): parts_used: [X]  ← step_number自动变为2
步骤3 (order:3000): parts_used: [C]  ← step_number自动变为3
```

**3D爆炸归位效果（在步骤3时）：**
```
步骤1后：       [A]  B   X   C   D   E   （只有A归位）

步骤2后：       [A       X]  B   C   D   E   （A X归位，B不再归位！）

步骤3后：       [A       X   C]  B   D   E   （A X C归位）
```

⚠️ **注意**：零件B因为步骤被删除，不会在任何步骤归位，始终保持爆炸状态

### 7.3 场景3：修改步骤2，添加零件X

只需修改步骤2的 `parts_used: [B, X]`：

**3D爆炸归位效果：**
```
步骤2后：       [A   B   X]  C   D   E   （A B X一起归位）

步骤3后：       [A   B   X   C]  D   E   （后续步骤自动包含X）
```

✅ 后续步骤的累积列表自动包含X，无需任何修改

---

## 八、实施路线图（更新版）

> ⚠️ **重要**：请先完成 Phase 0 的前置调研，否则后续阶段可能返工。

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 0: 前置调研（预计2天）🔴 必须先完成                   │
│ ├─ [ ] 确认 GLB 节点命名与 node_name 的对应关系            │
│ │      → 检查是否存在 step3_glb_inventory.json            │
│ │      → 或手动导出GLB节点列表与BOM对比                   │
│ ├─ [ ] 确认新增零件的 3D 入口策略                         │
│ │      → 方案A: 仅支持已有GLB节点的零件                   │
│ │      → 方案B: 支持追加额外GLB文件                       │
│ │      → 方案C: 新零件无3D显示，仅文字描述                │
│ ├─ [ ] 梳理 step_number 的所有引用点                      │
│ │      → ManualViewer.vue 中的引用                        │
│ │      → 安全提示、质检列表等                             │
│ └─ [ ] 输出：《前置调研报告》，明确技术可行性              │
├─────────────────────────────────────────────────────────────┤
│                        │
├─────────────────────────────────────────────────────────────┤
│ Phase 2: 后端 API + 数据迁移（预计3天）                     │
│ ├─ [ ] storage.py 旧数据迁移                               │
│ │      → step_id 转 UUID（保留旧ID映射字段 _legacy_id）   │
│ │      → 添加 display_order                               │
│ ├─ [ ] simple_app.py 新增 API                              │
│ │      → POST /steps/insert                               │
│ │      → DELETE /steps/{step_id}                          │
│ │      → POST /steps/move                                 │
│ ├─ [ ] 乐观锁 _edit_version                                │
│ └─ [ ] 验证：插入/删除/移动 API 正常工作                   │
├─────────────────────────────────────────────────────────────┤
│ Phase 3: 前端基础适配（预计3天）                            │
│ ├─ [ ] allSteps 按 display_order 排序                      │
│ ├─ [ ] step_number 动态计算                                │
│ ├─ [ ] 修复所有 step_number 引用点                         │
│ ├─ [ ] 插入步骤对话框 UI                                   │
│ ├─ [ ] 删除步骤确认逻辑                                    │
│ └─ [ ] 验证：插入/删除后步骤序号正确                       │
├─────────────────────────────────────────────────────────────┤
│ Phase 4: 3D 累积归位 + 高亮（预计4天）                      │
│ ├─ [ ] 初始爆炸状态（所有零件散开）                        │
│ ├─ [ ] 逐步归位逻辑（累积计算已装配零件）                  │
│ ├─ [ ] 当前步骤高亮（黄色）                                │
│ ├─ [ ] 已装配正常色 + 未装配半透明灰色                     │
│ ├─ [ ] 支持多实例零件（同编码多数量）                      │
│ └─ [ ] 处理新增零件无 node_name 的情况                     │
├─────────────────────────────────────────────────────────────┤
│ Phase 5: 测试与收尾（预计2天）                              │
│ ├─ [ ] 旧数据迁移测试                                      │
│ ├─ [ ] 历史版本对比测试                                    │
│ ├─ [ ] 并发编辑冲突测试                                    │
│ └─ [ ] 完整流程端到端测试                                  │
└─────────────────────────────────────────────────────────────┘

总预计时间：17天（含 Phase 0 调研）
```

### 风险与备选方案

| 风险 | 备选方案 |
|------|---------|
| GLB节点与node_name不对应 | 需要先修复BOM映射或手动维护映射表 |
| 新增零件无法3D显示 | 限制为"仅支持已有GLB节点的零件"，新零件只显示文字描述 |
| 提示词改动影响现有生成质量 | 保留旧提示词作为回退，新旧并行验证 |
| 历史版本对比失效 | 在新数据中保留 `_legacy_step_id` 字段用于映射 |

---

## 九、兼容性与风险

### 9.1 向后兼容性

| 功能点 | 兼容性 | 说明 |
|-------|:------:|------|
| 旧数据读取 | ✅ | 自动迁移，添加 display_order 和新 step_id |
| 前端 step_number 显示 | ✅ | 动态计算，无感知变化 |
| 版本历史追溯 | ✅ | 新 step_id 稳定，可跨版本对比 |
| 草稿保存 | ✅ | 兼容新旧格式 |
| Agent 生成新手册 | ✅ | 整合阶段自动添加新字段 |

### 9.2 风险评估

| 风险 | 等级 | 应对措施 |
|------|------|---------|
| 数据迁移失败 | 低 | 迁移前自动备份，失败可回滚 |
| 精度问题 | 极低 | display_order用整数，间隔1000，可支持数百次插入 |
| 并发冲突 | 低 | 乐观锁 + 提示刷新 |
| 性能影响 | 无 | 排序在前端完成，O(n log n) |

---

## 十、相关文件清单

### 需要修改的文件

| 文件 | 修改内容 | 优先级 |
|------|---------|--------|
| `prompts/agent_3_component_assembly.py` | 增加 display_order，允许UUID step_id | Phase 1 |
| `prompts/agent_4_product_assembly.py` | 同上 | Phase 1 |
| `core/manual_integrator_v2.py` | `_add_step_ids()` 改用 UUID + display_order | Phase 1 |
| `core/storage.py` | 旧数据迁移，保留 `_legacy_step_id` | Phase 2 |
| `backend/simple_app.py` | 新增 insert/delete/move API + 乐观锁 | Phase 2 |
| `frontend/src/views/ManualViewer.vue` | display_order排序、累积归位、高亮逻辑 | Phase 3-4 |

### 需要确认/调研的文件

| 文件 | 调研内容 |
|------|---------|
| `step3_glb_inventory.json`（如存在） | 确认 GLB 节点与 node_name 的对应关系 |
| `output/.../assembly_manual.json` | 了解现有数据结构，验证迁移逻辑 |
| GLB 文件（component_x.glb 等） | 导出节点列表，与 BOM 映射对比 |

### 待确认的技术决策

| 决策点 | 选项 | 影响 |
|-------|------|------|
| 新增零件 3D 显示 | A: 仅支持已有节点 / B: 支持追加GLB / C: 无3D显示 | 决定 Phase 4 复杂度 |
| 历史版本对比 | A: 保留旧ID映射 / B: 放弃旧版本对比 | 决定迁移复杂度 |
| step_number 存储 | A: 完全动态计算 / B: 存储但可编辑 | 决定前端改动范围 |
