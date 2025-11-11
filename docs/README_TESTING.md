# 测试指南

## 分层依赖架构测试

### 架构概述

系统采用**分层依赖架构**，将Agent分为两层：

#### **第一层：强依赖视觉（必须有Qwen-VL输出）**
- ✅ **Agent 3-1**：装配步骤生成
- ✅ **Agent 3-2**：焊接工艺翻译
- ✅ **Agent 3-3**：质量控制

#### **第二层：弱依赖视觉（可选的视觉信息）**
- ⚠️ **Agent 3-4**：安全与FAQ生成
  - 主要依赖：Agent 3-1、Agent 3-2的输出
  - 可选依赖：vision_channel（图纸上的安全警告）

---

## 测试步骤

### 步骤1：运行BOM-3D匹配测试（生成基础数据）

```bash
python test_multi_pdf_matching.py
```

**生成文件：**
- `test_output_three_agents/all_pdfs_bom.json` - 合并的BOM数据
- `test_output_three_agents/multi_pdf_matching_result.json` - 匹配结果
- `test_output_three_agents/step_parts_list.json` - 3D零件列表

**预期结果：**
- BOM项数：87项
- 3D零件数：414个
- 匹配率：61.8%（代码47.6% + AI 14.2%）

---

### 步骤2：运行完整三智能体流程（生成vision_channel）

```bash
python test_three_agents_pipeline.py
```

**生成文件：**
- `test_output_three_agents/vision_channel.json` - 视觉分析结果
- `test_output_three_agents/agent3_1_assembly_steps.json` - 装配步骤

**注意：** 这一步会调用Qwen-VL，需要较长时间（约2-5分钟）

---

### 步骤3：测试所有4个子Agent

```bash
python test_all_agents.py
```

**生成文件：**
- `test_output_three_agents/agent3_1_assembly_steps.json` - 装配步骤
- `test_output_three_agents/agent3_2_welding_requirements.json` - 焊接要求
- `test_output_three_agents/agent3_3_quality_control.json` - 质量检验
- `test_output_three_agents/agent3_4_safety_faq.json` - 安全与FAQ
- `test_output_three_agents/final_assembly_manual.json` - 最终装配手册

**预期结果：**
- Agent 3-1：3-5个装配步骤
- Agent 3-2：3-5个焊接要求
- Agent 3-3：5-10个质量检验点
- Agent 3-4：5-10个安全警告 + 5-10个FAQ

---

## 依赖关系验证

### 测试场景1：完整视觉信息

**前提条件：**
- `vision_channel.json` 存在且完整

**预期行为：**
- ✅ Agent 3-1：正常运行
- ✅ Agent 3-2：正常运行
- ✅ Agent 3-3：正常运行
- ✅ Agent 3-4：正常运行（使用视觉信息）

---

### 测试场景2：缺少视觉信息

**前提条件：**
- `vision_channel.json` 不存在或为空

**预期行为：**
- ❌ Agent 3-1：抛出 `ValueError("❌ Agent 3-1 强依赖视觉：缺少视觉分析结果")`
- ❌ Agent 3-2：抛出 `ValueError("❌ Agent 3-2 强依赖视觉：缺少视觉分析结果")`
- ❌ Agent 3-3：抛出 `ValueError("❌ Agent 3-3 强依赖视觉：缺少视觉分析结果")`
- ⚠️ Agent 3-4：如果有assembly_steps，仍可运行（降级模式）

---

### 测试场景3：部分视觉信息

**前提条件：**
- `vision_channel.json` 存在但某些字段缺失

**预期行为：**
- Agent 3-1：如果缺少 `assembly_sequence` 或 `assembly_connections`，抛出错误
- Agent 3-2：如果缺少 `welding_info`，可能返回空列表
- Agent 3-3：如果缺少 `critical_dimensions`，可能返回空列表
- Agent 3-4：正常运行（弱依赖）

---

## 错误处理验证

### 验证点1：强依赖Agent的错误提示

运行以下代码验证错误提示：

```python
from prompts.agent_3_1_assembly_steps_prompts import build_assembly_steps_user_input

try:
    build_assembly_steps_user_input(None, [])
except ValueError as e:
    print(e)  # 应该输出: ❌ Agent 3-1 强依赖视觉：缺少视觉分析结果
```

### 验证点2：弱依赖Agent的降级行为

```python
from prompts.agent_3_4_safety_faq_prompts import build_safety_faq_user_input

# 没有vision_result，但有assembly_steps
result = build_safety_faq_user_input(
    assembly_steps=[{"title": "测试步骤"}],
    welding_requirements=None,
    vision_result=None  # 可选
)
# 应该正常运行，不抛出错误
```

---

## 性能指标

### BOM-3D匹配性能

| 指标 | 数值 |
|------|------|
| BOM项数 | 87项 |
| 3D零件数 | 414个 |
| 代码匹配率 | 47.6% |
| AI匹配率 | 14.2% |
| **总匹配率** | **61.8%** |
| AI调用次数 | 1次 |
| AI成本 | ~￥0.08 |

### Agent生成性能

| Agent | 预计耗时 | Token消耗 | 成本 |
|-------|---------|----------|------|
| Agent 3-1 | 10-20秒 | ~3000 | ~￥0.03 |
| Agent 3-2 | 5-10秒 | ~1500 | ~￥0.015 |
| Agent 3-3 | 5-10秒 | ~1500 | ~￥0.015 |
| Agent 3-4 | 5-10秒 | ~1500 | ~￥0.015 |
| **总计** | **25-50秒** | **~7500** | **~￥0.075** |

---

## 常见问题

### Q1: Agent 3-1 报错"缺少视觉分析结果"

**原因：** 没有运行步骤2生成 `vision_channel.json`

**解决：** 先运行 `python test_three_agents_pipeline.py`

---

### Q2: AI匹配率低于预期

**原因：** 可能是prompt需要优化，或者BOM表质量问题

**解决：** 
1. 检查 `all_pdfs_bom.json` 是否完整
2. 检查未匹配零件列表，分析原因
3. 调整 `agent_2_ai_bom_matcher_prompts.py` 中的prompt

---

### Q3: Agent 3-4 生成的FAQ不够实用

**原因：** Agent 3-4 主要依赖前3个Agent的输出

**解决：**
1. 确保Agent 3-1生成了详细的装配步骤
2. 确保Agent 3-2生成了焊接要求
3. 提供vision_result以获取图纸上的安全警告

---

## 下一步

1. ✅ 完成所有4个子Agent的实现
2. ✅ 实现分层依赖架构
3. ⏳ 端到端测试
4. ⏳ 前端集成
5. ⏳ 性能优化

