# 🐛 系统Bug分析报告

**生成时间**: 2025-01-04  
**分析范围**: 文件上传、PDF处理、大模型配置  
**严重程度**: 🔴 高 | 🟡 中 | 🟢 低

---

## 📋 目录

1. [文件上传和重新上传问题](#1-文件上传和重新上传问题)
2. [PDF文件转换问题](#2-pdf文件转换问题)
3. [大模型硬编码问题](#3-大模型硬编码问题)
4. [修复优先级建议](#4-修复优先级建议)

---

## 1. 文件上传和重新上传问题

### 🔴 Bug #1: uploads目录文件累积问题

**严重程度**: 🔴 高  
**影响范围**: 文件上传、任务生成  
**文件位置**: `backend/simple_app.py` (行 90-133)

#### 问题描述
重新上传文件时，旧文件不会被清理，导致`uploads/`目录累积大量历史文件。系统在生成任务时可能会处理错误的文件集合。

#### 根本原因
```python
# backend/simple_app.py (行 101-127)
@app.post("/api/upload")
async def upload_files(
    pdf_files: List[UploadFile] = File(default=[]),
    model_files: List[UploadFile] = File(default=[])
):
    # ❌ 问题：直接覆盖同名文件，但不清理其他文件
    for file in pdf_files:
        if file.filename:
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)  # 直接覆盖
```

#### 复现步骤
1. 上传文件集A（产品总图.pdf, 组件1.pdf, 组件1.step）
2. 上传文件集B（产品总图.pdf, 组件2.pdf, 组件2.step）
3. 查看`uploads/`目录：会同时存在组件1和组件2的文件
4. 生成任务时，系统可能会处理混合的文件集

#### 影响
- ❌ 重新上传后，旧文件仍然存在
- ❌ 生成任务时可能处理错误的文件组合
- ❌ 磁盘空间浪费

#### 修复方案
**方案1: 上传前清空uploads目录（推荐）**
```python
@app.post("/api/upload")
async def upload_files(...):
    # ✅ 清空uploads目录
    import shutil
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    upload_dir.mkdir(exist_ok=True)
    
    # 然后再上传新文件
    for file in pdf_files:
        ...
```

**方案2: 使用会话ID隔离文件**
```python
@app.post("/api/upload")
async def upload_files(session_id: str = None):
    session_id = session_id or str(uuid.uuid4())
    session_dir = upload_dir / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    # 上传到session_dir
```

---

### 🔴 Bug #2: 前端文件上传逻辑不完整

**严重程度**: 🔴 高  
**影响范围**: 前端文件上传  
**文件位置**: `frontend/src/components/engineer/FileUploadSection.vue` (行 271-275)

#### 问题描述
`uploadFiles`函数是空实现，没有实际的上传逻辑，导致文件无法上传。

#### 根本原因
```javascript
// frontend/src/components/engineer/FileUploadSection.vue (行 271-275)
const uploadFiles = async (type) => {
  const uploadRef = type === 'pdf' ? 'pdfUpload' : 'modelUpload'
  // ❌ 这里应该调用实际的上传方法
  // ❌ 由于使用了 auto-upload="false"，需要手动触发上传
}
```

#### 影响
- ❌ 文件选择后无法上传到服务器
- ❌ `startUpload`函数调用`uploadFiles`但没有实际效果

#### 修复方案
```javascript
const uploadFiles = async (type) => {
  const uploadRef = type === 'pdf' ? pdfUpload : modelUpload
  
  if (!uploadRef.value) {
    throw new Error('Upload component not found')
  }
  
  // ✅ 手动触发上传
  uploadRef.value.submit()
}
```

---

### 🟡 Bug #3: 任务目录文件复制逻辑冗余

**严重程度**: 🟡 中  
**影响范围**: 任务生成性能  
**文件位置**: `backend/simple_app.py` (行 149-161)

#### 问题描述
每次生成任务时，都会从`uploads/`复制文件到`output/{task_id}/`，对于大文件会影响性能。

#### 根本原因
```python
# backend/simple_app.py (行 149-161)
# 复制文件到任务目录
import shutil
for pdf_file in request.pdf_files:
    src = upload_dir / pdf_file
    dst = pdf_dir / pdf_file
    if src.exists():
        shutil.copy2(src, dst)  # ❌ 每次都复制
```

#### 修复方案
**方案1: 使用符号链接（Linux/Mac）**
```python
if src.exists():
    os.symlink(src, dst)  # 创建符号链接而不是复制
```

**方案2: 直接使用uploads路径**
```python
# 不复制文件，直接传递uploads路径给pipeline
pipeline.run(
    pdf_dir=str(upload_dir),
    step_dir=str(upload_dir)
)
```

---

## 2. PDF文件转换问题

### 🟡 Bug #4: PDF转图片输出目录结构不一致

**严重程度**: 🟡 中  
**影响范围**: PDF图片访问  
**文件位置**: `core/file_classifier.py`, `backend/simple_app.py`

#### 问题描述
PDF转图片后，输出目录结构在不同版本中不一致，导致前端访问图片时路径错误。

#### 根本原因
```python
# core/file_classifier.py (行 268)
image_path = Path(output_dir) / f"page_{page_num + 1:03d}.png"

# backend/simple_app.py (行 476-487)
# 尝试两种路径
full_image_path = output_dir / "pdf_images" / image_path
fallback_path = output_dir / image_path  # 旧版本路径
```

#### 影响
- ⚠️ 前端需要尝试多个路径才能找到图片
- ⚠️ 代码维护困难

#### 修复方案
**统一输出目录结构**
```python
# 统一使用 output/{task_id}/pdf_images/{pdf_name}/page_001.png
def _pdf_to_images(self, pdf_path: str, output_dir: str):
    pdf_name = Path(pdf_path).stem
    image_dir = Path(output_dir) / "pdf_images" / pdf_name
    image_dir.mkdir(parents=True, exist_ok=True)
    
    for page_num in range(len(pdf_document)):
        image_path = image_dir / f"page_{page_num + 1:03d}.png"
        pix.save(str(image_path))
```

---

### 🟢 Bug #5: PDF处理缺少错误处理

**严重程度**: 🟢 低  
**影响范围**: PDF处理稳定性  
**文件位置**: `core/file_classifier.py` (行 256-275)

#### 问题描述
PDF转图片时缺少错误处理，如果PDF文件损坏或格式不支持，会导致整个流程崩溃。

#### 修复方案
```python
def _pdf_to_images(self, pdf_path: str, output_dir: str):
    try:
        pdf_document = fitz.open(pdf_path)
    except Exception as e:
        raise ValueError(f"无法打开PDF文件 {pdf_path}: {str(e)}")
    
    try:
        for page_num in range(len(pdf_document)):
            try:
                page = pdf_document[page_num]
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                image_path = Path(output_dir) / f"page_{page_num + 1:03d}.png"
                pix.save(str(image_path))
            except Exception as e:
                print(f"⚠️ 第{page_num+1}页转换失败: {str(e)}")
                continue
    finally:
        pdf_document.close()
```

---

## 3. 大模型硬编码问题

### 🔴 Bug #6: 模型名称硬编码

**严重程度**: 🔴 高  
**影响范围**: 所有AI模型调用  
**文件位置**: `models/gemini_model.py`, `models/vision_model.py`, `models/assembly_expert.py`

#### 问题描述
所有模型类都硬编码了模型名称，无法灵活切换模型。

#### 根本原因
```python
# models/gemini_model.py (行 33)
self.model_name = "google/gemini-2.5-flash-preview-09-2025"  # ❌ 硬编码

# models/vision_model.py (行 40)
self.model_name = "qwen-vl-plus"  # ❌ 硬编码

# models/assembly_expert.py (行 65)
self.model_name = "deepseek-chat"  # ❌ 硬编码
```

#### 影响
- ❌ 无法通过配置文件切换模型
- ❌ 无法A/B测试不同模型
- ❌ 模型升级需要修改代码

#### 修复方案
**方案1: 从环境变量读取（已部分实现）**
```python
# agents/base_gemini_agent.py (行 51-53) ✅ 已实现
@property
def model_name(self) -> str:
    return self._model_name_override or os.getenv("OPENROUTER_MODEL") or "google/gemini-2.0-flash-exp:free"
```

**方案2: 统一配置管理**
```python
# config.py
MODEL_CONFIG = {
    "gemini": os.getenv("GEMINI_MODEL", "google/gemini-2.5-flash-preview-09-2025"),
    "qwen": os.getenv("QWEN_MODEL", "qwen-vl-plus"),
    "deepseek": os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
}

# models/gemini_model.py
from config import MODEL_CONFIG
self.model_name = MODEL_CONFIG["gemini"]
```

---

### 🔴 Bug #7: API密钥硬编码在多个位置

**严重程度**: 🔴 高  
**影响范围**: API调用安全性  
**文件位置**: 多个模型文件

#### 问题描述
API密钥从环境变量读取，但缺少统一管理和验证机制。

#### 根本原因
```python
# 每个模型类都单独读取环境变量
self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
```

#### 修复方案
**统一API密钥管理**
```python
# config.py
class APIKeyManager:
    @staticmethod
    def get_key(service: str) -> str:
        key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "dashscope": "DASHSCOPE_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }
        key = os.getenv(key_map.get(service))
        if not key:
            raise ValueError(f"{service} API密钥未配置")
        return key

# 使用
from config import APIKeyManager
self.api_key = APIKeyManager.get_key("openrouter")
```

---

### 🟡 Bug #8: 提示词硬编码无法动态调整

**严重程度**: 🟡 中  
**影响范围**: 提示词优化和A/B测试  
**文件位置**: `prompts/` 目录下所有文件

#### 问题描述
所有提示词都硬编码在Python文件中，无法通过配置文件动态调整。

#### 根本原因
```python
# prompts/agent_1_vision_planning.py
ASSEMBLY_PLANNING_SYSTEM_PROMPT = """# 🎯 角色定位
你是一位资深的**装配工艺规划工程师**...
"""  # ❌ 硬编码在代码中
```

#### 影响
- ⚠️ 提示词优化需要修改代码并重启服务
- ⚠️ 无法进行A/B测试
- ⚠️ 无法根据用户反馈快速调整

#### 修复方案
**方案1: 使用YAML配置文件**
```yaml
# prompts/agent_1_vision_planning.yaml
system_prompt: |
  # 🎯 角色定位
  你是一位资深的**装配工艺规划工程师**...

user_query_template: |
  我提供了这个产品的工程图纸...
  {bom_data}
```

```python
# prompts/agent_1_vision_planning.py
import yaml

def load_prompt_config(agent_name: str):
    with open(f"prompts/{agent_name}.yaml") as f:
        return yaml.safe_load(f)

config = load_prompt_config("agent_1_vision_planning")
ASSEMBLY_PLANNING_SYSTEM_PROMPT = config["system_prompt"]
```

**方案2: 数据库存储（支持热更新）**
```python
# 从数据库读取提示词
def get_system_prompt(agent_name: str, version: str = "latest"):
    return db.query("SELECT prompt FROM prompts WHERE agent=? AND version=?", 
                    agent_name, version)
```

---

## 4. 修复优先级建议

### 🔥 P0 - 立即修复（阻塞功能）
1. **Bug #1**: uploads目录文件累积问题
2. **Bug #2**: 前端文件上传逻辑不完整
3. **Bug #6**: 模型名称硬编码

### ⚡ P1 - 高优先级（影响用户体验）
4. **Bug #7**: API密钥硬编码在多个位置
5. **Bug #4**: PDF转图片输出目录结构不一致

### 📌 P2 - 中优先级（优化改进）
6. **Bug #3**: 任务目录文件复制逻辑冗余
7. **Bug #8**: 提示词硬编码无法动态调整

### 🔧 P3 - 低优先级（增强稳定性）
8. **Bug #5**: PDF处理缺少错误处理

---

## 5. 总结

### 核心问题
1. **文件管理混乱**: uploads目录缺少清理机制
2. **配置硬编码**: 模型名称、API密钥、提示词都硬编码
3. **错误处理不足**: 缺少异常处理和降级方案

### 建议的重构方向
1. **统一配置管理**: 使用`config.py`集中管理所有配置
2. **文件生命周期管理**: 实现文件清理和会话隔离
3. **提示词外部化**: 使用YAML或数据库存储提示词
4. **增强错误处理**: 添加完善的异常处理和日志记录

---

**报告生成者**: AI Agent  
**审核状态**: 待用户确认

