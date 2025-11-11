# 快速修复指南

**目标**: 快速修复3个核心问题，让系统正常运行

---

## 🔴 问题1: Qwen-VL JSON解析失败 + 添加重试机制

### 修复位置
文件: `core/dual_channel_parser.py`  
方法: `_call_assembly_expert_model()`  
行数: 约第300-464行

### 修复代码

在方法开头添加重试循环：

```python
def _call_assembly_expert_model(
    self,
    image_paths: List[str],
    bom_context: str,
    page_count: int
) -> Dict[str, Any]:
    """调用装配专家模型（Qwen-VL）进行视觉分析 - 带重试机制"""
    
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            self._log(f"🤖 Qwen-VL视觉智能体启动（尝试 {attempt+1}/{max_retries}），分析{page_count}页图纸...", "info")
            
            # 调用Qwen-VL
            response = self.vision_model.analyze_with_context(
                image_paths=image_paths,
                context_text=bom_context,
                max_tokens=4000  # ✅ 限制返回长度
            )
            
            # ... 原有的JSON解析代码 ...
            
            # 如果成功解析，返回结果
            if parsed_result:
                self._log(f"✅ Qwen-VL视觉分析完成（第{attempt+1}次尝试成功）", "success")
                return parsed_result
                
        except json.JSONDecodeError as e:
            last_error = e
            self._log(f"⚠️ JSON解析失败（尝试 {attempt+1}/{max_retries}）: {str(e)}", "warning")
            
            if attempt < max_retries - 1:
                # 还有重试机会
                import time
                time.sleep(2)  # 等待2秒后重试
                continue
            else:
                # 最后一次失败
                error_msg = f"Qwen-VL调用失败（已重试{max_retries}次）: {str(e)}"
                self._log(f"❌ {error_msg}", "error")
                raise Exception(error_msg)
                
        except Exception as e:
            last_error = e
            self._log(f"⚠️ Qwen-VL调用异常（尝试 {attempt+1}/{max_retries}）: {str(e)}", "warning")
            
            if attempt < max_retries - 1:
                import time
                time.sleep(2)
                continue
            else:
                error_msg = f"Qwen-VL调用失败（已重试{max_retries}次）: {str(e)}"
                self._log(f"❌ {error_msg}", "error")
                raise Exception(error_msg)
    
    # 理论上不会到这里
    raise Exception(f"Qwen-VL调用失败: {str(last_error)}")
```

### 关键改动
1. ✅ 添加 `max_retries = 3` 重试循环
2. ✅ 添加 `max_tokens=4000` 限制返回长度
3. ✅ 失败时等待2秒后重试
4. ✅ 最后一次失败时抛出异常（不返回空数据）

---

## 🔴 问题2: DeepSeek匹配结果显示0

### 调试步骤

#### 步骤1: 查看实际返回数据

在 `core/parallel_pipeline.py` 的 `_generate_assembly_specification()` 方法中添加调试日志：

```python
# 在第437行（调用DeepSeek后）添加
result = self.assembly_expert.generate_assembly_specification(...)

# ✅ 添加调试日志
print("\n" + "="*80)
print("[DEBUG] DeepSeek完整返回结构:")
print(json.dumps(result, indent=2, ensure_ascii=False))
print("="*80 + "\n")

# 检查是否成功
if not result or not result.get("success"):
    ...
```

#### 步骤2: 根据实际结构调整

查看打印的JSON结构，找到实际的字段名，然后修改提取逻辑：

```python
# 提取结果数据
parsed_result = result.get("result", {})

# ✅ 添加调试日志
print(f"[DEBUG] parsed_result类型: {type(parsed_result)}")
print(f"[DEBUG] parsed_result键: {list(parsed_result.keys()) if isinstance(parsed_result, dict) else 'Not a dict'}")

# 统计结果 - 根据实际结构调整
if parsed_result and isinstance(parsed_result, dict):
    # 尝试多种可能的字段名
    steps = (
        parsed_result.get("assembly_steps") or 
        parsed_result.get("steps") or 
        parsed_result.get("装配步骤") or 
        []
    )
    
    parts = (
        parsed_result.get("parts") or 
        parsed_result.get("components") or 
        parsed_result.get("零件列表") or 
        []
    )
    
    bom_mapping = (
        parsed_result.get("bom_mapping") or 
        parsed_result.get("mapping") or 
        parsed_result.get("零件对应") or 
        []
    )
    
    # ✅ 添加调试日志
    print(f"[DEBUG] 提取结果: steps={len(steps)}, parts={len(parts)}, bom_mapping={len(bom_mapping)}")
    
    # 计算匹配率
    matched_count = len([m for m in bom_mapping if m.get("matched", False)]) if bom_mapping else 0
    match_rate = (matched_count / bom_total * 100) if bom_total > 0 else 0
    
    self._log(
        f"✅ DeepSeek匹配完成: {len(parts)}个零件, {len(steps)}个装配步骤, "
        f"匹配率{match_rate:.1f}% ({matched_count}/{bom_total})", 
        "success"
    )
```

#### 步骤3: 检查debug_output文件

查看 `debug_output/assembly_expert_output_*.json` 文件，确认DeepSeek实际返回的数据结构。

---

## 🔴 问题3: 错误时立即停止流程

### 修复位置
文件: `core/parallel_pipeline.py`  
行数: 第162-169行

### 修复代码

```python
# ❌ 原代码（不要用）
try:
    parallel_results["vision"] = future_vision.result()
    if not parallel_results["vision"]:
        self._log("⚠️ 视觉分析未返回结果，将使用空数据继续", "warning")
        parallel_results["vision"] = []
except Exception as e:
    self._log(f"⚠️ 视觉分析失败: {str(e)}，将使用空数据继续", "warning")
    parallel_results["vision"] = []

# ✅ 新代码（应该用）
try:
    parallel_results["vision"] = future_vision.result()
    if not parallel_results["vision"]:
        raise Exception("视觉分析未返回结果")
except Exception as e:
    error_msg = f"视觉分析失败: {str(e)}"
    self._log(f"❌ {error_msg}", "error")
    raise Exception(error_msg)  # ✅ 立即停止，不继续执行
```

### 前端修改

在 `frontend/src/views/Generator.vue` 的 `updateStepByLog()` 方法中添加错误处理：

```typescript
const updateStepByLog = (message: string, level: string) => {
  const msg = message.toLowerCase()
  
  // ✅ 如果是错误日志，立即停止
  if (level === 'error') {
    processingStatus.value = 'exception'
    processingText.value = '处理失败'
    isGenerating.value = false
    
    // 显示错误对话框
    ElMessageBox.alert(message, '处理失败', {
      type: 'error',
      confirmButtonText: '确定'
    })
    
    return  // 不再继续更新步骤
  }
  
  // ... 原有的步骤更新逻辑 ...
}
```

---

## 测试流程

### 1. 启动后端
```bash
cd e:\装修说明书项目
python backend/app.py
```

### 2. 访问前端
打开浏览器: `http://localhost:3000`

### 3. 配置API密钥
- 点击"API设置"
- 输入DashScope API Key
- 输入DeepSeek API Key
- 保存

### 4. 上传文件测试
- 上传PDF工程图纸
- 上传STEP 3D模型
- 点击"开始生成"

### 5. 观察日志
- 查看实时日志
- 查看步骤进度
- 检查是否有错误

### 6. 检查结果
- [ ] Qwen-VL是否成功（不再有JSON解析失败）
- [ ] DeepSeek匹配率是否正确显示（不再是0%）
- [ ] 错误时是否立即停止（不再继续执行）

---

## 常见问题

### Q1: 如何查看详细的错误信息？
A: 查看后端控制台输出，或者查看 `debug_output/` 目录下的JSON文件。

### Q2: 如何重置测试？
A: 删除 `output/` 目录下的所有文件，重新上传。

### Q3: API密钥在哪里获取？
A: 
- DashScope: https://dashscope.console.aliyun.com/
- DeepSeek: https://platform.deepseek.com/

### Q4: 如何查看WebSocket消息？
A: 打开浏览器开发者工具 → Network → WS → 选择连接 → Messages

---

## 修复后的预期效果

### 成功的日志示例
```
📄 开始PDF文本提取
✅ PDF文本提取完成: 53个BOM项
🔄 开始STEP→GLB转换，共1个文件
✅ STEP→GLB转换完成: 1个文件, 共414个零件
🤖 Qwen-VL视觉智能体启动（尝试 1/3），分析2页图纸...
✅ Qwen-VL视觉分析完成（第1次尝试成功）: 11个装配关系, 5个技术要求
🤖 DeepSeek开始匹配BOM和GLB零件...
✅ DeepSeek匹配完成: 53个零件, 11个装配步骤, 匹配率79.2% (42/53)
💥 生成GLB爆炸动画数据...
✅ 成功生成414个零件的爆炸动画数据
📖 生成HTML装配说明书...
✅ 处理完成！
```

### 失败时的日志示例（应该立即停止）
```
📄 开始PDF文本提取
✅ PDF文本提取完成: 53个BOM项
🔄 开始STEP→GLB转换，共1个文件
✅ STEP→GLB转换完成: 1个文件, 共414个零件
🤖 Qwen-VL视觉智能体启动（尝试 1/3），分析2页图纸...
⚠️ JSON解析失败（尝试 1/3）: Expecting ',' delimiter
🤖 Qwen-VL视觉智能体启动（尝试 2/3），分析2页图纸...
⚠️ JSON解析失败（尝试 2/3）: Expecting ',' delimiter
🤖 Qwen-VL视觉智能体启动（尝试 3/3），分析2页图纸...
⚠️ JSON解析失败（尝试 3/3）: Expecting ',' delimiter
❌ Qwen-VL调用失败（已重试3次）: Expecting ',' delimiter
❌ 视觉分析失败: Qwen-VL调用失败（已重试3次）
[流程停止，不再继续]
```

---

## 下一步优化建议

修复完这3个问题后，可以考虑：

1. **优化Qwen-VL的prompt** - 减少返回数据量，提高JSON格式正确率
2. **优化DeepSeek的prompt** - 提高匹配准确率
3. **添加进度百分比** - 更精确的进度显示
4. **优化前端UI** - 更美观的步骤展示
5. **添加结果预览** - 生成完成后直接预览HTML

---

**祝修复顺利！** 🚀

