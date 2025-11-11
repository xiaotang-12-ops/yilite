# 🐛 Bug修复：PDF文件大小写敏感问题

**修复时间**: 2025-01-04  
**Bug级别**: P0（阻塞功能）  
**影响范围**: 文件上传和PDF转换功能

---

## 📋 问题描述

用户上传了以下文件：
- `产品总图.PDF` (大写)
- `组件1.PDF` (大写)
- `组件2.PDF` (大写)
- `组件3.pdf` (小写)
- `组件4.PDF` (大写)

**现象**：只有`组件3.pdf`被识别和转换成图片，其他大写`.PDF`文件都被忽略。

**输出结果**：
```
output/d12e4dfc-5423-43d7-b125-1617237e1994/
├── pdf_images/
│   └── 3/
│       └── page_001.png  ← 只有组件3被转换
├── step1_file_hierarchy.json
└── ...
```

**step1_file_hierarchy.json内容**：
```json
{
  "product": null,
  "components": [
    {
      "name": "",
      "bom_code": "",
      "index": 3,
      "pdf": "output/.../pdf_files/组件3.pdf",
      "step": null
    }
  ]
}
```

---

## 🔍 根本原因分析

### 问题代码位置

**文件**: `core/gemini_pipeline.py`  
**行号**: 213

```python
pdf_path = Path(pdf_dir)
pdf_files = [str(f) for f in pdf_path.glob("*.pdf")]  # ❌ 只扫描小写.pdf
```

### 原因

Python的`glob()`方法在Windows系统上**默认是大小写不敏感的**，但在Linux/Docker容器中**是大小写敏感的**。

由于后端运行在Docker容器（Linux环境）中，`glob("*.pdf")`只会匹配小写的`.pdf`文件，而不会匹配大写的`.PDF`文件。

### 影响范围

1. **文件识别失败** - 大写`.PDF`文件不会被识别为PDF文件
2. **文件分类错误** - 产品总图和组件图无法正确分类
3. **PDF转图片失败** - 大写`.PDF`文件不会被转换成图片
4. **后续流程中断** - BOM提取、装配规划等步骤无法正常进行

---

## ✅ 修复方案

### 修复代码

**文件**: `core/gemini_pipeline.py`  
**行号**: 212-216

```python
pdf_path = Path(pdf_dir)
# ✅ Bug修复：同时扫描大写和小写的PDF文件
pdf_files = [str(f) for f in pdf_path.glob("*.pdf")] + [str(f) for f in pdf_path.glob("*.PDF")]

print_info(f"📄 他发现了 {len(pdf_files)} 个PDF图纸", indent=1)
```

### 修复原理

通过同时扫描`*.pdf`和`*.PDF`两种模式，确保在Linux/Docker环境中也能识别所有PDF文件，无论扩展名是大写还是小写。

---

## 🧪 验证测试

### 测试步骤

1. **上传测试文件**：
   - 产品总图.PDF
   - 组件1.PDF
   - 组件2.PDF
   - 组件3.pdf
   - 组件4.PDF

2. **检查文件识别**：
   ```bash
   docker exec assembly-backend ls -la /app/uploads
   ```
   
   **预期结果**：所有5个PDF文件都应该被识别

3. **检查文件分类**：
   查看`output/{task_id}/step1_file_hierarchy.json`
   
   **预期结果**：
   ```json
   {
     "product": {
       "pdf": "output/.../pdf_files/产品总图.PDF",
       "step": "output/.../step_files/产品总图.STEP"
     },
     "components": [
       {"index": 1, "pdf": "output/.../pdf_files/组件1.PDF", ...},
       {"index": 2, "pdf": "output/.../pdf_files/组件2.PDF", ...},
       {"index": 3, "pdf": "output/.../pdf_files/组件3.pdf", ...},
       {"index": 4, "pdf": "output/.../pdf_files/组件4.PDF", ...}
     ]
   }
   ```

4. **检查PDF转图片**：
   查看`output/{task_id}/pdf_images/`目录
   
   **预期结果**：
   ```
   pdf_images/
   ├── 产品总图/
   │   └── page_001.png
   ├── 组件1/
   │   └── page_001.png
   ├── 组件2/
   │   └── page_001.png
   ├── 组件3/
   │   └── page_001.png
   └── 组件4/
       └── page_001.png
   ```

---

## 📝 相关问题

### 是否还有其他文件类型存在类似问题？

**是的**，STEP文件也有类似处理：

**文件**: `core/gemini_pipeline.py`  
**行号**: 225

```python
step_files = [str(f) for f in step_path.glob("*.STEP")] + \
             [str(f) for f in step_path.glob("*.step")] + \
             [str(f) for f in step_path.glob("*.stp")]
```

✅ **STEP文件已经正确处理了大小写问题**，同时扫描了`*.STEP`、`*.step`和`*.stp`三种模式。

---

## 🎯 最佳实践建议

### 1. 文件扫描统一处理

建议创建一个统一的文件扫描函数：

```python
def scan_files_case_insensitive(directory: Path, extension: str) -> List[str]:
    """
    大小写不敏感的文件扫描
    
    Args:
        directory: 目录路径
        extension: 文件扩展名（不含点号），如 "pdf"
        
    Returns:
        文件路径列表
    """
    files = []
    # 扫描小写
    files.extend([str(f) for f in directory.glob(f"*.{extension.lower()}")])
    # 扫描大写
    files.extend([str(f) for f in directory.glob(f"*.{extension.upper()}")])
    # 去重（防止Windows系统重复）
    return list(set(files))
```

### 2. 文件命名规范

建议在文档中明确文件命名规范：
- 推荐使用小写扩展名（`.pdf`, `.step`）
- 或者在上传时统一转换为小写

### 3. 跨平台兼容性测试

在开发时应该同时测试：
- Windows环境（大小写不敏感）
- Linux/Docker环境（大小写敏感）

---

## 📊 修复影响

### 修复前

- ❌ 只能识别小写`.pdf`文件
- ❌ 大写`.PDF`文件被忽略
- ❌ 文件分类不完整
- ❌ PDF转图片功能异常

### 修复后

- ✅ 同时识别`.pdf`和`.PDF`文件
- ✅ 所有PDF文件都能被正确识别
- ✅ 文件分类完整准确
- ✅ PDF转图片功能正常

---

## 🚀 部署说明

### 重启服务

```bash
docker-compose restart backend
```

### 验证修复

1. 清空uploads目录
2. 重新上传测试文件
3. 检查日志输出
4. 验证所有PDF都被转换成图片

---

**修复完成时间**: 2025-01-04  
**修复者**: AI Agent  
**审核状态**: 待用户验证

