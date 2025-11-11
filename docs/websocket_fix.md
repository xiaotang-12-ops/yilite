# WebSocket事件循环错误修复

## 🐛 问题描述

### **错误信息**
```
no running event loop
```

### **原因分析**
`ProgressReporter`在同步代码（`DualChannelParser`）中调用异步方法时，使用了`asyncio.create_task()`，但这个函数只能在异步上下文中调用。

**错误代码：**
```python
def report_progress(self, stage, progress, message, data=None):
    loop = self._get_loop()
    if loop.is_running():
        # ❌ 错误：create_task只能在async函数中调用
        asyncio.create_task(
            self.manager.send_progress(self.task_id, stage, progress, message, data)
        )
```

---

## ✅ 修复方案

### **使用`asyncio.run_coroutine_threadsafe()`**

这个函数可以从**任何线程**（包括同步代码）安全地调度协程到事件循环中执行。

**修复后的代码：**
```python
def report_progress(self, stage, progress, message, data=None):
    """报告进度（同步方法，可在处理流程中调用）"""
    try:
        loop = asyncio.get_running_loop()
        # ✅ 正确：从同步代码调度协程到事件循环
        asyncio.run_coroutine_threadsafe(
            self.manager.send_progress(self.task_id, stage, progress, message, data),
            loop
        )
    except RuntimeError:
        # 没有运行的事件循环，忽略
        print(f"[WARNING] 无法发送进度: {message}")
```

---

## 📝 修改的文件

### **1. `backend/websocket_manager.py`**

修改了`ProgressReporter`类的三个方法：

#### **`report_progress()`**
```python
def report_progress(self, stage, progress, message, data=None):
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(
            self.manager.send_progress(self.task_id, stage, progress, message, data),
            loop
        )
    except RuntimeError:
        print(f"[WARNING] 无法发送进度: {message}")
```

#### **`report_parallel()`**
```python
def report_parallel(self, parallel_data):
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(
            self.manager.send_parallel_progress(self.task_id, parallel_data),
            loop
        )
    except RuntimeError:
        print(f"[WARNING] 无法发送并行进度")
```

#### **`log()`**
```python
def log(self, message, level="info"):
    try:
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(
            self.manager.send_log(self.task_id, message, level),
            loop
        )
    except RuntimeError:
        print(f"[WARNING] 无法发送日志: {message}")
```

### **2. `frontend/src/views/Generator.vue`**

修改了`updateProcessingData()`函数，添加了对新阶段的支持：

```typescript
const updateProcessingData = (stage: string, taskData: any) => {
  console.log('更新处理数据:', stage, taskData)
  
  const data = { ...processingData.value }

  switch (stage) {
    case 'pdf_bom':
      // 阶段1: PDF解析 - 提取BOM表
      data.pdf_bom = {
        ...data.pdf_bom,
        ...taskData
      }
      break
    case 'parallel':
      // 阶段2: 并行处理
      data.pdf_deep = taskData.pdf_deep
      data.step_extract = taskData.step_extract
      break
    case 'matching':
      // 阶段3: BOM-STEP匹配
      data.matching = {
        ...data.matching,
        ...taskData
      }
      break
    case 'generate':
      // 阶段4: 生成说明书
      data.generate = {
        ...data.generate,
        ...taskData
      }
      break
  }

  processingData.value = data
}
```

---

## 🔍 技术细节

### **`asyncio.run_coroutine_threadsafe()` vs `asyncio.create_task()`**

| 特性 | `run_coroutine_threadsafe()` | `create_task()` |
|------|------------------------------|-----------------|
| **调用位置** | 任何线程（同步/异步） | 只能在async函数中 |
| **参数** | 需要传入loop对象 | 自动使用当前loop |
| **返回值** | `concurrent.futures.Future` | `asyncio.Task` |
| **用途** | 跨线程调度协程 | 在同一事件循环中创建任务 |

### **为什么需要这个修复？**

1. **同步代码调用异步方法**：
   - `DualChannelParser.parse_pdf()` 是同步方法
   - 它调用 `self._report_progress()` 也是同步方法
   - 但 `_report_progress()` 需要调用异步的 `manager.send_progress()`

2. **事件循环在另一个线程**：
   - FastAPI的WebSocket运行在主事件循环中
   - PDF处理运行在后台线程中
   - 需要线程安全的方式来调度协程

3. **`run_coroutine_threadsafe()` 的作用**：
   - 从后台线程安全地调度协程到主事件循环
   - 返回一个Future对象（我们不需要等待结果）
   - 不会阻塞当前线程

---

## ✅ 测试验证

### **预期行为**
1. ✅ 不再出现"no running event loop"错误
2. ✅ WebSocket消息正常发送
3. ✅ 前端能收到进度更新
4. ✅ 日志正常显示

### **测试步骤**
1. 重启后端服务器
2. 刷新前端页面
3. 上传PDF和STEP文件
4. 观察：
   - 阶段卡片是否显示关键数据
   - 日志是否正常显示
   - 是否有错误信息

---

## 📚 参考资料

- [asyncio.run_coroutine_threadsafe() 文档](https://docs.python.org/3/library/asyncio-task.html#asyncio.run_coroutine_threadsafe)
- [asyncio.create_task() 文档](https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task)
- [FastAPI WebSocket 文档](https://fastapi.tiangolo.com/advanced/websockets/)

