# 🔄 Agent重构任务 - 交接文档

**交接日期**: 2025-10-02  
**任务目标**: 调整Agent分工并重构提示词，确保装配步骤生成准确  
**优先级**: 🔴 高（核心功能不准确）

---

## 📋 任务概述

### 核心问题
当前Agent 3-1（装配步骤生成专家）生成的装配步骤**不准确**，需要重新设计Agent分工和提示词策略。

### 任务目标
1. **分析当前问题**：为什么装配步骤不准确？
2. **重新设计Agent分工**：是否需要调整Agent职责？
3. **重构提示词**：优化提示词以提高准确性
4. **验证效果**：确保新方案生成准确的装配步骤

---

## 🔍 当前问题分析

### 问题1：装配步骤不符合实际

**现象**：
- 生成的装配步骤与实际装配顺序不符
- 步骤过于简化或过于复杂
- 零件分组不合理

**示例**（来自 `test_output_three_agents/agent3_1_assembly_steps.json`）：
```json
{
  "step_number": 1,
  "title": "安装底部加强筋基准件",
  "description": "将底部加强筋作为基准件放置在工作平台上",
  "parts_used": [
    {
      "bom_seq": "1",
      "bom_code": "01.01.017678",
      "bom_name": "加强筋",
      "qty": 1
    }
  ]
}
```

**问题**：
- ❌ 基准件选择可能不正确（加强筋不一定是基准件）
- ❌ 缺少对产品整体结构的理解
- ❌ 没有考虑实际装配工艺

### 问题2：视觉信息利用不充分

**当前依赖**：
- `vision_channel.assembly_sequence_hints`（装配顺序线索）
- `vision_channel.assembly_connections`（装配连接关系）
- `vision_channel.spatial_relationships`（空间关系）

**问题**：
- ⚠️ Qwen-VL提取的信息可能不够详细
- ⚠️ DeepSeek推理时没有充分利用视觉信息
- ⚠️ 缺少对工程图纸的深度理解

### 问题3：提示词策略问题

**当前策略**：
- 使用5模块标准（角色、教育、经验、知识、SOP）
- Chain of Thought推理
- 输出JSON格式

**问题**：
- ⚠️ SOP步骤可能过于抽象
- ⚠️ 缺少具体的装配工艺知识
- ⚠️ 没有足够的示例和约束

---

## 📁 需要查看的关键文件

### 1. Agent架构文档
**文件**: `docs/AGENT_ARCHITECTURE.md`  
**重点关注**:
- 第54-75行：Agent 3-1的定义和职责
- 第144-197行：数据流架构和依赖关系
- 第218-231行：提示词文件结构标准

**为什么重要**：
- 理解当前Agent分工逻辑
- 了解Agent之间的依赖关系
- 掌握提示词设计规范

---

### 2. Agent 3-1提示词文件
**文件**: `prompts/agent_3_1_assembly_steps_prompts.py`  
**重点关注**:
- 第12-21行：角色定义（ASSEMBLY_STEPS_EXPERT_ROLE）
- 第54-78行：知识结构（装配原则、顺序规划方法）
- 第82-149行：工作SOP（Chain of Thought流程）
- 第220-300行：用户输入构建函数（build_assembly_steps_user_input）

**为什么重要**：
- 这是Agent 3-1的核心逻辑
- 需要重构的主要文件
- 理解当前提示词的优缺点

**当前问题**：
```python
# 第97-100行：基准件识别逻辑过于简单
行动：
1. 从BOM表中找到最大、最重的零件
2. 从视觉分析的"装配顺序线索"中找到基准件提示
3. 确定基准件（通常是底座、框架、后座等）
4. 基准件是第一个装配步骤
```
- ❌ 仅凭重量判断基准件不准确
- ❌ 没有考虑产品类型（推雪板 vs 其他机械）
- ❌ 缺少对装配工艺的深度理解

---

### 3. Agent 1视觉识别提示词
**文件**: `prompts/agent_1_vision_prompts.py`  
**重点关注**:
- 视觉模型提取的信息类型
- `assembly_sequence_hints`的生成逻辑
- `assembly_connections`的识别方法

**为什么重要**：
- Agent 3-1强依赖Agent 1的输出
- 如果Agent 1提取的信息不准确，Agent 3-1也无法生成准确结果
- 可能需要优化Agent 1的提示词

---

### 4. 测试输出文件
**文件**: `test_output_three_agents/agent3_1_assembly_steps.json`  
**重点关注**:
- 第1-100行：前两个装配步骤的详细内容
- 零件选择是否合理
- 步骤顺序是否符合工艺

**为什么重要**：
- 这是当前Agent 3-1的实际输出
- 可以直观看到问题所在
- 作为重构后的对比基准

**当前输出示例**：
```json
{
  "step_number": 1,
  "title": "安装底部加强筋基准件",
  "parts_used": [{"bom_code": "01.01.017678", "bom_name": "加强筋"}]
},
{
  "step_number": 2,
  "title": "安装左右侧框架",
  "parts_used": [
    {"bom_code": "01.01.011660", "bom_name": "左侧框架"},
    {"bom_code": "01.01.011515", "bom_name": "右侧框架"}
  ]
}
```

---

### 5. 视觉分析结果
**文件**: `test_output_three_agents/agent1_vision_result.json`  
**重点关注**:
- `vision_channel.product_overview`（产品总览）
- `vision_channel.assembly_sequence_hints`（装配顺序线索）
- `vision_channel.assembly_connections`（装配连接关系）
- `vision_channel.spatial_relationships`（空间关系）

**为什么重要**：
- 这是Agent 3-1的输入数据
- 评估视觉信息的质量和完整性
- 判断是否需要优化Agent 1

**关键数据示例**：
```json
{
  "product_overview": {
    "product_name": "T-SPV1830-EURO",
    "product_type": "推雪板",
    "main_structure": "框架+铲板+液压系统+连接组件"
  },
  "assembly_sequence_hints": [
    "建议先安装连接器后座作为基准件",
    "然后安装左右侧框架",
    "最后安装铲板和液压系统"
  ]
}
```

---

### 6. 数据集成模块
**文件**: `core/manual_integrator.py`  
**重点关注**:
- 第11-53行：`generate_3d_params`函数（自动生成3D参数）
- 第56-91行：`generate_product_overview`函数（产品总览生成）
- 第143-276行：`integrate_manual_data`函数（数据整合）

**为什么重要**：
- 理解装配步骤如何与3D模型关联
- 了解最终JSON的生成逻辑
- 可能需要调整3D参数生成策略

---

### 7. 测试流水线
**文件**: `test_three_agents_pipeline.py`  
**重点关注**:
- 第345-401行：`step4_1_assembly_steps_generation`函数
- 第575-680行：完整流水线执行逻辑

**为什么重要**：
- 理解Agent调用流程
- 了解数据如何在Agent之间传递
- 测试重构后的效果

---

### 8. 其他Agent提示词（参考）
**文件**: 
- `prompts/agent_3_2_welding_prompts.py`（焊接工艺翻译）
- `prompts/agent_3_3_quality_control_prompts.py`（质量控制）
- `prompts/agent_3_4_safety_faq_prompts.py`（安全FAQ）

**为什么重要**：
- 参考其他Agent的提示词设计
- 保持提示词风格一致
- 学习成功的提示词模式

---

## 🎯 重构建议方向

### 方向1：增强视觉信息提取（Agent 1优化）

**问题**：
- Qwen-VL可能没有提取足够详细的装配顺序信息

**建议**：
1. 优化Agent 1的提示词，要求更详细的装配顺序分析
2. 增加"装配工艺分析"字段
3. 要求识别"基准件"、"主要组件"、"辅助零件"

**修改文件**：
- `prompts/agent_1_vision_prompts.py`

---

### 方向2：细化Agent 3-1的推理逻辑

**问题**：
- 当前SOP过于抽象，缺少具体的装配工艺知识

**建议**：
1. 增加"产品类型识别"步骤（推雪板、挖掘机、起重机等）
2. 根据产品类型应用不同的装配策略
3. 增加"装配工艺知识库"（常见产品的装配顺序模式）
4. 增加"自检机制"（生成后验证步骤合理性）

**修改文件**：
- `prompts/agent_3_1_assembly_steps_prompts.py`

---

### 方向3：引入Few-Shot示例

**问题**：
- 缺少具体的装配步骤示例

**建议**：
1. 在提示词中增加2-3个典型产品的装配步骤示例
2. 示例包含：推雪板、框架结构、液压系统等
3. 让模型学习正确的步骤粒度和描述方式

**修改文件**：
- `prompts/agent_3_1_assembly_steps_prompts.py`

---

### 方向4：增加Agent 3-0（装配工艺规划专家）

**问题**：
- Agent 3-1直接生成步骤，缺少整体规划

**建议**：
1. 新增Agent 3-0：装配工艺规划专家
   - 输入：vision_channel + BOM
   - 输出：装配策略（基准件、主要组件、装配顺序框架）
2. Agent 3-1基于Agent 3-0的规划生成详细步骤

**新增文件**：
- `prompts/agent_3_0_assembly_planning_prompts.py`

---

## 📊 验证标准

重构完成后，需要验证以下指标：

### 1. 装配步骤准确性
- ✅ 基准件选择正确
- ✅ 装配顺序符合工艺
- ✅ 零件分组合理

### 2. 步骤完整性
- ✅ 包含所有主要零件
- ✅ 步骤数量合理（5-10个）
- ✅ 每个步骤详细可操作

### 3. 工人友好性
- ✅ 语言通俗易懂
- ✅ 包含具体数值
- ✅ 有质量检查点

---

## 🚀 下一步行动

### 第一步：深入分析（1-2小时）
1. 阅读所有关键文件
2. 理解当前Agent分工逻辑
3. 分析视觉信息质量
4. 确定重构方向

### 第二步：设计方案（2-3小时）
1. 选择重构方向（方向1-4中的一个或多个）
2. 设计新的提示词结构
3. 编写Few-Shot示例
4. 设计验证测试用例

### 第三步：实施重构（3-4小时）
1. 修改提示词文件
2. 如需新增Agent，创建新文件
3. 更新测试流水线
4. 运行测试验证

### 第四步：验证优化（1-2小时）
1. 对比新旧输出
2. 检查准确性指标
3. 调整优化
4. 文档更新

---

## 📝 注意事项

1. **保持向后兼容**：不要破坏其他Agent的功能
2. **遵循5模块标准**：保持提示词结构一致
3. **充分测试**：每次修改后都要运行完整流水线
4. **记录变更**：更新`AGENT_ARCHITECTURE.md`

---

**交接完成**  
**祝重构顺利！** 🎉

