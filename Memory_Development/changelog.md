# 完整版本历史

**项目**: Mecagent
**最后更新**: 2025-01-14

---

## v1.1.7 (2025-01-14) - 三色高亮显示系统

### ✨ 新增功能

#### 🎨 三色高亮显示系统
- **黄色高亮**：当前步骤正在装配的零件（`color: 0xffff00`，发光强度0.8）
- **绿色高亮**：已完成装配的零件（`color: 0x4CAF50`，发光强度0.3）
- **灰色显示**：尚未装配的零件（`color: 0x808080`，半透明度0.3）

#### 📐 单零件步骤优化
- 每个装配步骤只涉及一个零件，避免操作混淆
- 自动计算新零件：`新零件 = 当前步骤零件 - 前面步骤零件`
- 智能处理焊接等特殊步骤（无新零件时继承上一步高亮）

#### 🔧 技术实现
- **前端高亮逻辑**：`highlightStepParts()` 函数（ManualViewer.vue 第2042行）
- **已装配零件计算**：`assembledMeshes` 计算属性（第945行）
- **后端3D高亮生成**：组件装配Agent自动生成`3d_highlight`字段
- **优先级规则**：黄色 > 绿色 > 灰色

### 🎯 视觉优化
- 高对比度材质设计，适合车间环境
- 发光效果（emissive）增强零件识别度
- 天蓝色基础材质（`0x4A90E2`），清晰锐利

### 🐛 Bug修复
- 修复组件切换时高亮状态不更新的问题
- 修复首次加载时已装配零件计算错误
- 优化GLB模型切换逻辑

### 📝 文档更新
- 更新README.md，添加v1.1.7功能说明
- 更新CHANGELOG.md，记录详细变更
- 创建RELEASE_v1.1.7.md发布说明
- 创建GIT_UPLOAD_v1.1.7.md上传指南
- 更新VERSION文件至1.1.7

### 🔍 已知限制
- 颜色暂不支持自定义（待v1.1.8实现）
- 装配步骤描述暂不支持在线编辑（待v1.1.8实现）
- 产品总图STEP文件如果简化组件表示，会导致部分零件无法高亮（建模问题，非代码问题）

---

## v1.1.6 (2025-01-13)

### 🐛 Bug修复
- 修复前端数据加载问题
- 优化WebSocket连接稳定性

---

## v1.1.5 (2025-01-12)

### ✨ 新增功能
- **管理员登录功能**：支持管理员登录后编辑说明书内容
- **在线编辑**：可直接修改焊接要求、安全警告、质检要求
- **组件名称修改**：支持修改组件名称并实时同步
- **数据持久化**：编辑内容自动保存到后端文件

---

## v1.5.0 (2025-11-15) - 产品装配重复组件检测与修正

### 🎯 核心功能

**问题背景**:
- AI生成的产品装配步骤中，步骤3和步骤4重复安装了步骤1中已经放置的子组件（滚轮组件、连接器总成组件）
- 导致3D高亮错误：步骤17和步骤18高亮了子组件内部的零件，而不是产品级别的零件

**根本原因**:
1. AI不稳定：即使提示词明确说明"步骤1放置所有子组件，步骤2-N只安装零件"，AI有时还是会违反规则
2. AI误解：
   - 看到图纸上的组件编号（②号滚轮组件、④号连接器总成组件），误以为需要单独安装
   - 理解"放置"和"安装"是两个不同的步骤（步骤1只是摆放位置，后续步骤需要固定连接）

**解决方案**:
1. **强化提示词**（治标）：
   - 明确说明步骤1的组件不需要再次安装
   - 添加"特别注意"部分，解释为什么AI会出错
   - 添加错误示例和正确示例
2. **后端验证和修正**（治本）：
   - 在`_auto_generate_3d_highlight`方法中添加检测逻辑
   - 自动删除重复的组件安装步骤
   - 重新编号所有步骤

### 📝 修改文件

**1. `prompts/agent_4_product_assembly.py`（第64-112行）**
- ✅ 添加"特别注意"部分：
  - 图纸上的组件编号只是用于识别，不代表需要单独安装
  - 步骤1放置的组件已经是最终位置，不需要再次安装
  - "放置"和"安装"不是两个不同的步骤
- ✅ 添加错误示例：
  ```
  步骤3: 安装滚轮组件  ❌ 错误！滚轮组件在步骤1中已经放置了
  ```
- ✅ 添加正确示例：
  ```
  步骤3: 安装耐磨刀板  ✅ 正确（part_bom_items中的零件）
  ```

**2. `agents/product_assembly_agent.py`（第334-423行）**
- ✅ 在`_auto_generate_3d_highlight`方法开头添加检测逻辑：
  1. 收集步骤1中的所有组件（bom_code和bom_name）
  2. 遍历步骤2-N，检查components中是否有重复的组件
  3. 删除重复的组件
  4. 如果步骤为空（components和fasteners都为空），删除整个步骤
  5. 重新编号所有步骤
  6. 继续原有的3d_highlight验证逻辑

### 🎨 预期效果

**修改前**（错误）:
```
步骤1: 放置所有子组件（固定座、滚轮、连接器）
步骤2: 安装带立式座轴承
步骤3: 安装滚轮组件  ❌ 重复！
步骤4: 安装连接器总成组件  ❌ 重复！
步骤5: 紧固螺栓M20*90
...
```

**修改后**（正确）:
```
步骤1: 放置所有子组件（固定座、滚轮、连接器）
步骤2: 安装带立式座轴承
步骤3: 紧固螺栓M20*90  ✅ 原步骤5，重新编号
步骤4: 紧固螺栓M20*70  ✅ 原步骤6，重新编号
...
```

### 💡 技术决策

1. **双重保险**：提示词强化（减少AI出错）+ 后端验证（确保100%正确）
2. **同时检查bom_code和bom_name**：确保即使数据不完整，也能检测到重复的组件
3. **详细日志**：每个检测和修正步骤都有日志输出，方便调试
4. **向后兼容**：如果旧数据中没有重复的组件，验证逻辑不会删除任何步骤

### 🔧 相关问题修复

- 修复了步骤17和步骤18的3D高亮错误（黄色高亮了子组件内部的零件）
- 确保产品装配步骤只包含产品级别的零件（螺栓、刀板、销轴、轴承等）

---

## v1.4.0 (2025-11-15) - 用户修改描述字段不影响3D高亮

### 🎯 核心功能

**问题背景**:
- 管理员模式允许用户修改步骤的`description`字段
- 前端会同时从`parts_used`和`description`中提取BOM序号来高亮零件
- 如果用户修改`description`，改变了BOM序号（如从"①号"改成"②号"），会导致3D高亮错误

**解决方案**:
- 修改前端逻辑：只有当`parts_used`为空时，才从`description`中提取BOM序号（作为备用方案）
- AI生成的新图纸都有`parts_used`字段，所以用户可以随意修改`description`，不会影响3D高亮

### 📝 修改文件

**`frontend/src/views/ManualViewer.vue`（第829-839行）**
```javascript
// 2. 组件装配步骤：parts_used
if (currentStepData.value?.parts_used) {
  allParts.push(...currentStepData.value.parts_used.filter((p: any) => p))
}

// ✅ 3. 从描述中提取BOM序号（备用方案：只有当allParts为空时才使用）
const description: string = (currentStepData.value as any)?.description || ''
if (allParts.length === 0 && description) {
  console.log('  ⚠️  parts_used为空，尝试从description中提取BOM序号（备用方案）')
  // 提取BOM序号...
}
```

### 🎨 预期效果

- ✅ 用户可以随意修改`description`字段，不会影响3D高亮
- ✅ 向后兼容：如果旧数据中`parts_used`为空，仍然可以从`description`中提取BOM序号

---

## v1.3.1 (2025-11-14) - 产品装配3D高亮验证与修正

### 🎯 核心功能

**问题背景**:
- AI生成的`3d_highlight`字段有时不正确（包含错误的node_name或遗漏某些node_name）
- 导致3D高亮显示错误

**解决方案**:
- 在`product_assembly_agent.py`中添加`_auto_generate_3d_highlight`方法
- 强制验证所有步骤的`3d_highlight`字段
- 如果AI生成的不正确，自动从`components`和`fasteners`中提取正确的node_name

### 📝 修改文件

**`agents/product_assembly_agent.py`（第334-394行）**
- 添加`_auto_generate_3d_highlight`方法
- 从`components`和`fasteners`中收集所有node_name
- 对比AI生成的`3d_highlight`，如果不一致则自动修正

### 💡 技术决策

- 类似于组件装配的验证逻辑
- 确保`3d_highlight`字段100%正确

---

## v1.3.0 (2025-11-14) - 产品总装三色高亮优化

### 🎯 核心功能

**新功能**:
1. 产品总装添加`3d_highlight`字段，明确指定每个步骤应该高亮的零件
2. 修改产品总装规则：**第一步放置所有子组件，后续每个零件BOM项一个步骤**
3. 优化Agent 4提示词，要求生成3d_highlight字段
4. 添加3d_highlight自动生成逻辑（如果AI没生成）

**核心规则（产品总装）**:
- **步骤1：放置所有子组件**
  - `components`: [所有子组件]
  - `fasteners`: []
  - `3d_highlight`: [所有子组件的所有node_name]
- **步骤2-N：每个零件BOM项一个步骤**
  - `components`: []
  - `fasteners`: [当前零件BOM项的所有实例]
  - `3d_highlight`: [当前零件BOM项的所有node_name]

### 📝 修改文件

- `prompts/agent_4_product_assembly.py`
  - 第61-88行: 修改装配顺序规划规则
  - 第90-142行: 添加3D高亮标注章节
  - 第178-216行: 更新示例
  - 第310-419行: 更新Few-Shot示例
- `agents/product_assembly_agent.py`
  - 第141-151行: 添加3d_highlight验证逻辑
  - 第300-347行: 添加3d_highlight自动生成逻辑

### 🎨 预期效果

- 🟢 绿色：已装配的零件（前面步骤的零件）
- 🟡 黄色：正在装配的零件（3d_highlight中的零件）
- ⚪ 灰色：未装配的零件

### 💡 技术决策

- 采用"第一步放置所有子组件"的方案，简化装配逻辑
- 每个零件BOM项一个步骤，确保3D高亮清晰
- 和焊接场景的规则保持一致（每步一个新BOM项）

---

## v1.2.1 (2025-11-14) - 组件装配3D高亮验证与修正

### 🎯 核心功能

**问题背景**:
- AI生成的组件装配步骤中，`3d_highlight`字段有时不正确
- 例如：滚轮组件步骤4缺少NAUO35/NAUO36，步骤5的圆环板node_name错误
- 连接器组件步骤3-4的衬套node_name错误

**解决方案**:
- 在`component_assembly_agent.py`中修改`_add_mesh_ids_from_table`方法
- 强制验证所有步骤的`3d_highlight`字段
- 计算"新零件"（当前步骤零件 - 前面步骤零件），从`parts_used`中提取正确的node_name

### 📝 修改文件

**`agents/component_assembly_agent.py`（第298-354行）**
```python
def _add_mesh_ids_from_table(self, assembly_steps: List[Dict], bom_mapping_table: List[Dict]) -> List[Dict]:
    # 1. 收集当前步骤的BOM序号
    # 2. 收集前面步骤的BOM序号
    # 3. 计算新零件（当前 - 前面）
    # 4. 从parts_used中提取新零件的node_name
    # 5. 对比AI生成的3d_highlight，如果不一致则修正
```

### 🎨 预期效果

- ✅ 所有步骤的`3d_highlight`字段100%正确
- ✅ 只高亮当前步骤新增的零件，不高亮参照零件
- ✅ 修复了滚轮组件、连接器组件的3D高亮错误

### 💡 技术决策

- 使用"新零件 = 当前步骤零件 - 前面步骤零件"的算法
- 从`parts_used`中提取node_name，而不是从BOM映射表中查找
- 确保即使AI生成错误，后端也能自动修正

---

## v1.2.2 (2025-11-14) - 产品装配颜色显示修复

### 🎯 核心功能

**问题背景**:
- 产品装配视图中，所有子组件都显示为透明色，而不是绿色（已装配）
- 原因：前端的`assembledMeshes`从`component_assembly`中收集node_name（NAUO1-NAUO36）
- 但`product_total.glb`使用不同的node_name（NAUO38-NAUO84）

**解决方案**:
- 修改前端逻辑：从`product_assembly.steps[0].components`中收集子组件的node_name
- 这样可以获取到产品级别的node_name（NAUO38-NAUO84）

### 📝 修改文件

**`frontend/src/views/ManualViewer.vue`（第948-995行）**
```javascript
if (isProductAssembly.value) {
  console.log('  📦 [产品总装] 收集所有子组件的零件')

  const productSteps = manualData.value?.product_assembly?.steps || []
  const step1 = productSteps.find((s: any) => s.step_number === 1)

  if (step1 && step1.components) {
    console.log(`  ✅ [从步骤1收集子组件] 步骤1标题: ${step1.title}`)
    step1.components.forEach((comp: any) => {
      const compName = comp.bom_name || comp.name || '未知组件'
      const nodeCount = comp.node_name?.length || 0
      console.log(`    - ${compName}: ${nodeCount}个node_name`)

      if (comp.node_name && Array.isArray(comp.node_name)) {
        assembled.push(...comp.node_name)
      }
    })
    console.log(`  ✅ [子组件总计] 收集了${assembled.length}个子组件node_name`)
  }
}
```

### 🎨 预期效果

- ✅ 产品装配视图中，所有子组件显示为绿色（已装配）
- ✅ 当前步骤的零件显示为黄色（正在装配）
- ✅ 未装配的零件显示为透明/灰色

### 💡 技术决策

- Node name层级关系：
  - 组件级别GLB：NAUO1-NAUO36（用于组件装配视图）
  - 产品级别GLB：NAUO38-NAUO84（用于产品装配视图）
- 前端需要根据当前视图类型，使用对应的node_name

---

## v1.2.0 (2025-11-13) - 焊接场景三色高亮优化

### 🎯 核心功能

**问题描述**:
焊接场景下的三色高亮逻辑存在严重问题：
- 参照零件（已焊接）被错误高亮为黄色（正在焊接）
- 前端无法区分哪些是"参照零件"（应该绿色），哪些是"新零件"（应该黄色）
- 导致工人无法准确识别当前正在焊接的零件

**根本原因**:
- 焊接场景中，`parts_used`包含**参照零件 + 新零件**
- 前端的`currentStepHighlightMeshes`直接从`parts_used`提取所有零件
- 导致参照零件被错误高亮为黄色

**解决方案**:
1. 添加`3d_highlight`字段，明确指定每个步骤应该高亮的零件
2. 强制"每步一个新BOM项"规则（焊接场景）
3. **修复点焊/满焊步骤的parts_used为空问题**
4. 添加焊接/装配场景区分机制
5. 添加步骤数量验证逻辑
6. 添加parts_used不为空的验证逻辑

**核心规则**:
- **每个步骤只能引入1个新的BOM项**（不是1个实例）
- **如果BOM有N项，应该生成N个安装步骤**（不包括点焊/满焊）
- **一个BOM项可以有多个实例**（如2个侧板），这些实例在同一个步骤中安装
- **3d_highlight包含该BOM项的所有实例的node_name**

### 📝 修改文件

**prompts/agent_3_component_assembly.py**:

1. **第117-128行**: 修改分组装配步骤规则
   - 焊接场景：每个步骤只能引入1个新的BOM项（不是1个实例）
   - 如果BOM有N项，应该生成N个安装步骤
   - 一个BOM项可以有多个实例，这些实例在同一个步骤中安装
   - 装配场景：每个步骤可以包含1-3个零件

2. **第197-249行**: 添加3D高亮规则章节
   - 识别新BOM项
   - 提取该BOM项的所有实例的node_name
   - 生成3d_highlight字段
   - 提供详细示例（包含多实例情况）
   - **强制要求点焊/满焊步骤的parts_used不能为空**

3. **第266-284行**: JSON输出格式添加3d_highlight字段
   ```json
   "3d_highlight": ["NAUO1", "NAUO2"]
   ```

4. **第480-495行**: 添加3D高亮要求
   - 每个步骤必须包含3d_highlight字段
   - 3d_highlight生成逻辑说明

5. **第505-519行**: 添加3D高亮自检清单
   - 验证每个步骤都包含3d_highlight字段
   - 验证3d_highlight的值是否正确

6. **第538-548行**: JSON模板添加3d_highlight字段

**agents/component_assembly_agent.py**:

1. **第135-155行**: 添加验证逻辑
   - 验证每个步骤是否包含3d_highlight字段
   - **验证每个步骤的parts_used不为空**
   ```python
   # 验证3d_highlight
   missing_highlight_steps = []
   for step in assembly_steps:
       if "3d_highlight" not in step or not step["3d_highlight"]:
           missing_highlight_steps.append(step.get("step_number", "?"))

   # 验证parts_used不为空
   empty_parts_steps = []
   for step in assembly_steps:
       if not step.get("parts_used"):
           empty_parts_steps.append(step.get("step_number", "?"))
   ```

2. **第287-337行**: 添加3d_highlight自动生成逻辑
   - 识别新BOM项（当前步骤 - 前面步骤）
   - 提取新BOM项的所有实例的node_name
   - 如果没有新BOM项（点焊步骤），使用上一个步骤的3d_highlight

### 🎨 数据结构变化

**装配步骤新增字段**:
```json
{
  "step_number": 2,
  "action": "安装侧板",
  "parts_used": [
    {"bom_seq": "1", "bom_name": "方形板-机加", "node_name": ["NAUO1"]},
    {"bom_seq": "2", "bom_name": "侧板", "quantity": 2, "node_name": ["NAUO3", "NAUO2"]}
  ],
  "3d_highlight": ["NAUO3", "NAUO2"]  // ← 新增：包含新BOM项的所有实例
}
```

**说明**:
- BOM序号2是"侧板"，有2个实例（NAUO3和NAUO2）
- 这2个实例在同一个步骤中安装
- 3d_highlight包含这2个实例的所有node_name

### 🎯 预期效果

**修改前**（步骤2）:
- 🟡 黄色：NAUO1（方形板-机加）← 错误！应该是绿色
- 🟡 黄色：NAUO2, NAUO3（侧板）← 正确
- ⚪ 灰色：其他零件

**修改后**（步骤2）:
- 🟢 绿色：NAUO1（方形板-机加）← 正确！
- 🟡 黄色：NAUO2, NAUO3（侧板）← 正确
- ⚪ 灰色：其他零件

### 🔍 技术细节

**3d_highlight生成规则**:
1. **第一步**：3d_highlight = 基准件的所有node_name
2. **安装步骤**：3d_highlight = 新引入BOM项的所有实例的node_name
3. **点焊步骤**：3d_highlight = 上一个安装步骤引入的BOM项的所有node_name
4. **满焊步骤**：3d_highlight = []

**重要**：如果一个BOM项有多个实例（如2个侧板），3d_highlight必须包含所有实例的node_name

**前端三色逻辑**（已存在，不需要修改）:
```javascript
const currentNodes = currentStepData.value['3d_highlight'] || currentStepHighlightMeshes.value
```
- 优先使用`3d_highlight`字段
- 如果不存在，回退到`currentStepHighlightMeshes`

### ⚠️ 重要注意事项

1. **向后兼容**: 旧的装配说明书没有`3d_highlight`字段，前端会自动回退到旧逻辑
2. **AI兜底**: 如果AI没有生成`3d_highlight`，后端会自动生成
3. **验证机制**: 后端会验证每个步骤是否包含`3d_highlight`字段

---

## v1.1.6 (2025-11-13) - 修复焊接模块组件名称同步问题

### 🐛 Bug 修复

**问题描述**:
- 修改焊接模块的组件名称无法同步到 `component_name`
- 安全警告模块可以同步，但焊接模块不行
- 导致前端显示的组件名称与编辑的不一致

**根本原因**:
保存时执行顺序导致数据覆盖：
1. 焊接模块先更新 `component.component_name = updatedComponentName`（新值 ✅）
2. 安全警告模块后更新 `component.component_name = updatedComponentNameFromSafety`（旧值 ❌）
3. 因为用户只修改了焊接模块的组件名称，安全警告模块的 `warning.component` 还是旧值
4. 导致安全警告模块用旧值覆盖了焊接模块的更新

**修复方案**:
采用**实时同步**方案：
1. 添加 `watch` 监听焊接模块的组件名称变化
2. 自动同步到安全警告模块的所有警告
3. 安全警告模块的组件名称设为只读（灰色背景）
4. 焊接模块增加醒目的警告提示（橙色 + 图标）

### 📝 修改文件

**frontend/src/views/ManualViewer.vue**:

1. **第383-392行**: 焊接模块组件名称提示增强
   ```vue
   <el-text type="warning" size="small">
     <el-icon><Warning /></el-icon>
     修改组件名称会同步更新到当前步骤和安全警告模块
   </el-text>
   ```

2. **第484-494行**: 安全警告模块组件名称设为只读
   ```vue
   <el-input
     v-model="warning.component"
     disabled
     style="background-color: #f5f7fa;"
   />
   <el-text type="info" size="small">
     组件名称由焊接模块自动同步，不可单独修改
   </el-text>
   ```

3. **第587-592行**: 导入 Warning 图标
   ```javascript
   import { Warning } from '@element-plus/icons-vue'
   ```

4. **第1206-1220行**: 添加 watch 监听逻辑
   ```javascript
   watch(
     () => editData.value.welding_requirements.length > 0
       ? editData.value.welding_requirements[0].component
       : null,
     (newComponentName) => {
       if (newComponentName && editData.value.safety_warnings.length > 0) {
         editData.value.safety_warnings.forEach(warning => {
           warning.component = newComponentName
         })
         console.log('🔄 [组件名称同步] 焊接模块 → 安全警告模块:', newComponentName)
       }
     }
   )
   ```

### 🎯 用户体验提升

- ✅ 视觉提示: 焊接模块有醒目的橙色警告提示
- ✅ 自动同步: 修改焊接模块时，安全警告模块实时同步
- ✅ 防止混淆: 安全警告模块的组件名称设为只读（灰色）
- ✅ 调试友好: 控制台会输出同步日志

### ⚠️ 注意事项

1. **只读限制**: 现在只能通过焊接模块修改组件名称，安全警告模块是只读的
2. **同步条件**: 只有当焊接模块有数据时才会触发同步
3. **多个警告**: 如果一个步骤有多个安全警告，所有警告的组件名称都会同步更新

---

## v1.1.5 (2025-11-10) - 支持组件名称修改

### ✨ 新功能

1. **组件名称编辑**
   - ✅ 支持修改组件名称
   - ✅ 使用唯一 `step_id` 精确匹配，避免误更新
   - ✅ 修改后实时同步到前端显示
   - ✅ 自动保存到后端 JSON 文件

2. **焊接要求管理**
   - ✅ 添加/删除焊接要求
   - ✅ 编辑焊接类型、焊缝尺寸、焊接位置
   - ⚠️ 限制每个步骤只能添加一个焊接要求

3. **安全警告管理**
   - ✅ 添加/删除安全警告
   - ✅ 编辑警告内容

4. **数据持久化**
   - ✅ 所有编辑内容自动保存到 `output/{task_id}/assembly_manual.json`
   - ✅ 自动递增版本号（格式：`major.minor`）
   - ✅ 添加 `lastUpdated` 时间戳
   - ✅ 支持刷新页面后数据保持

### 🐛 Bug 修复

1. **组件名称更新问题**
   - **问题**: 修改组件名称后，前端显示没有更新
   - **原因**: 前端显示的是 `component.component_name`（组件级别），但代码只更新了 `step.component_name`（步骤级别）
   - **修复**: 同时更新组件级别和步骤级别的 `component_name`

2. **焊接要求添加问题**
   - **问题**: 添加第二个焊接要求后无法保存
   - **原因**: 后端数据结构 `step.welding` 是单个对象，不支持数组
   - **修复**: 限制每个步骤只能添加一个焊接要求，并在 UI 上提示用户

3. **质检显示问题**
   - **问题**: 质检标签页显示了所有步骤的质检要求
   - **原因**: 计算属性返回了所有步骤的质检
   - **修复**: 新增 `currentStepQualityCheck` 计算属性，只返回当前步骤的质检

### 📝 修改文件

**frontend/src/views/ManualViewer.vue**:
- 第1277-1340行: 焊接模块保存逻辑（更新组件名称）
- 第1342-1382行: 安全警告模块保存逻辑（更新组件名称）

---

## v1.1.4 (2025-11-10) - 修复组件步骤过滤BUG

### 🐛 严重BUG修复（组件步骤数据混乱问题）

**严重级别**: 🔴 严重（会导致数据显示错误和混乱）

**问题描述**:
1. 编辑页面显示有内容（可以看到编辑器里有数据）
2. 但前端页面没有渲染这些内容（页面显示为空或显示其他内容）
3. 不同组件的相同步骤号数据混在一起显示
4. 例如：主框架组件的步骤1 显示了 挂架组件的步骤1 的焊接数据

**根本原因**:
- 每个组件都有独立的步骤序列（例如：主框架组件有步骤1-13，挂架组件有步骤1-7）
- v1.1.3 的修复中，为了解决"编辑后数据不显示"的问题，把过滤逻辑改为只按步骤号过滤
- 这导致不同组件的相同步骤号数据混乱
- 用户可以手动修改组件名称，导致数据不一致

**解决方案**:
1. **恢复双重过滤逻辑**: 必须同时匹配 `step_number` 和 `component`
2. **编辑对话框中组件名称设为只读**: 步骤号和组件名称都由系统自动确定
3. **添加数据时自动填充正确的组件名称**: 使用 `currentStep.component_name` 而不是 `currentStep.action`
4. **保存时强制使用当前步骤的组件名称**: 避免用户手动修改导致的数据不一致

### 📝 修改文件

**frontend/src/views/ManualViewer.vue**:
- 第957-996行: 恢复焊接数据双重过滤逻辑
- 第400-422行: 焊接数据编辑表单 - 组件名称设为只读
- 第501-524行: 安全警告编辑表单 - 组件名称设为只读
- 第1183-1220行: 修复添加函数使用正确的字段
- 第1252-1287行: 保存焊接数据时强制使用正确的值

---

## v1.1.3 及更早版本

详细历史请参考项目根目录下的 `RELEASE_v*.md` 文件。

---

## 🔄 版本号规则

- **主版本号（major）**: 重大功能更新或架构变更
- **次版本号（minor）**: 新功能添加或重要 Bug 修复
- **修订号（patch）**: 小 Bug 修复或文档更新

---

## 📞 问题反馈

如果遇到问题，请在 GitHub 上提交 Issue。

