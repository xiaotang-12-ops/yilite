# API密钥配置指南

## 🎯 功能说明

现在你可以在前端界面直接配置API密钥，不需要每次修改代码了！

---

## 📝 使用步骤

### **1. 访问设置页面**

有两种方式：

**方式1：从首页进入**
1. 打开首页 `http://localhost:3000`
2. 点击 **"API设置"** 按钮

**方式2：直接访问**
- 直接访问 `http://localhost:3000/settings`

---

### **2. 获取API密钥**

#### **DashScope API Key（阿里云）**

1. 访问 [阿里云DashScope控制台](https://dashscope.console.aliyun.com/)
2. 登录/注册账号
3. 点击 **"API-KEY管理"**
4. 创建新的API Key
5. 复制API Key（格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

**用途：** Qwen-VL视觉模型，用于图纸分析

---

#### **DeepSeek API Key**

1. 访问 [DeepSeek开放平台](https://platform.deepseek.com/)
2. 登录/注册账号
3. 点击 **"API Keys"**
4. 创建新的API Key
5. 复制API Key（格式：`sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

**用途：** 装配专家推理模型，用于生成装配规范

---

### **3. 配置API密钥**

1. 在设置页面，将复制的API Key粘贴到对应的输入框：
   - **DashScope API Key** → 第一个输入框
   - **DeepSeek API Key** → 第二个输入框

2. 点击 **"保存设置"** 按钮

3. 等待提示 **"设置保存成功！"**

---

### **4. 测试连接**

点击 **"测试连接"** 按钮，验证：
- ✅ 后端服务是否正常运行
- ✅ API密钥是否配置正确

---

## 🔒 安全说明

### **密钥存储**

- **前端：** 密钥保存在浏览器的 `localStorage` 中
- **后端：** 密钥保存在内存中（重启后需要重新配置）

### **安全建议**

1. ⚠️ **不要在公共电脑上保存密钥**
2. ⚠️ **定期更换API密钥**
3. ⚠️ **不要将密钥分享给他人**
4. ⚠️ **生产环境建议使用环境变量**

---

## 🛠️ 高级配置

### **环境变量（推荐生产环境）**

如果你不想每次都在前端输入密钥，可以设置环境变量：

**Windows (PowerShell):**
```powershell
$env:DASHSCOPE_API_KEY="sk-your-dashscope-key"
$env:DEEPSEEK_API_KEY="sk-your-deepseek-key"
python backend/app.py
```

**Linux/Mac:**
```bash
export DASHSCOPE_API_KEY="sk-your-dashscope-key"
export DEEPSEEK_API_KEY="sk-your-deepseek-key"
python backend/app.py
```

**优先级：**
1. 前端设置的密钥（最高优先级）
2. 环境变量
3. 默认值（空）

---

## 🔍 故障排查

### **问题1：保存后仍然报错 "Incorrect API key"**

**原因：** API密钥格式错误或已过期

**解决方案：**
1. 检查密钥格式是否正确（应该以 `sk-` 开头）
2. 确认密钥没有多余的空格
3. 重新生成新的API密钥

---

### **问题2：测试连接失败**

**原因：** 后端服务未启动

**解决方案：**
1. 确认后端服务正在运行：`http://localhost:8000/api/docs`
2. 检查控制台是否有错误信息
3. 重启后端服务

---

### **问题3：刷新页面后密钥丢失**

**原因：** 浏览器清除了 `localStorage`

**解决方案：**
1. 不要使用无痕模式
2. 不要清除浏览器缓存
3. 或者使用环境变量方式

---

## 📊 API密钥查看

### **查看当前配置**

访问 `http://localhost:8000/api/settings` 可以查看当前配置的密钥（脱敏显示）：

```json
{
  "dashscope_api_key": "sk-c4...e0a",
  "deepseek_api_key": "sk-ea...2b4",
  "has_dashscope": true,
  "has_deepseek": true
}
```

---

## 🎉 完成！

配置完成后，你就可以：
1. 上传PDF和STEP文件
2. 生成装配说明书
3. 实时查看处理进度

**不需要再修改代码了！** 🚀

