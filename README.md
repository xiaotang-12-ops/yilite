# 智能装配说明书生成系统

[![Version](https://img.shields.io/badge/version-v2.0.0-blue.svg)](https://github.com/xiaotang-12-ops/yilite/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](DOCKER_DEPLOYMENT.md)

> **让普通工人看完说明书也能进行加工**

一个基于AI的智能装配说明书生成系统，能够自动解析PDF工程图纸和3D模型，生成工人友好的交互式HTML装配说明书。

**当前版本**: v2.0.0 | [查看版本历史](https://github.com/xiaotang-12-ops/yilite/releases) | [部署指南](DOCKER_DEPLOYMENT.md)

## 🆕 v2.0.0 更新

- ✅ 管理员编辑：组件名称统一入口，保存时同步到步骤与组件并落盘 `assembly_manual.json`。
- ✅ 查看端优化：手册“预计时间”模块隐藏展示（字段仍保留数据）。
- ✅ 品牌与文档：导航品牌图标改为 `public/image.png`；新增管理员修改流程简明文档，完善 Memory 记录。

## ✨ 核心特性

- 🤖 **AI驱动**: 使用Qwen3-VL视觉模型解析工程图纸，DeepSeek专家模型生成装配工艺
- 📱 **工人友好**: 专为车间环境设计，支持移动设备和离线使用
- 🎯 **3D交互**: 集成Three.js 3D模型显示，支持爆炸视图和步骤导航
- 📖 **即开即用**: 生成的HTML说明书无需额外软件，浏览器直接打开
- 🔧 **专业工艺**: 基于20年工程经验的AI专家，生成符合工业标准的装配规程

## 🏗️ 系统架构

```
PDF工程图纸 + 3D模型 → AI解析引擎 → 装配规程生成 → HTML说明书
     ↓              ↓           ↓            ↓
  Qwen3-VL      DeepSeek     工艺专家     工人友好界面
```

## 🚀 快速开始

### 使用 Docker 部署（推荐）⭐

**只需 3 步，5 分钟完成部署！**

```bash
# 1. 克隆项目
git clone https://github.com/xiaotang-12-ops/Mecagent.git
cd Mecagent

# 2. 配置 API 密钥
cp .env.example .env
# 编辑 .env 文件，填入你的 OPENROUTER_API_KEY

# 3. 启动服务
docker-compose up -d
```

**访问系统**：
- 🌐 前端界面: http://localhost:3008
- 📚 API 文档: http://localhost:8008/api/docs

**详细部署说明**: 请查看 [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### 本地开发环境

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/xiaotang-12-ops/Mecagent.git
cd Mecagent

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DASHSCOPE_API_KEY="your_dashscope_api_key"
export DEEPSEEK_API_KEY="your_deepseek_api_key"
export BLENDER_EXE="/path/to/blender"  # 可选
```

### 2. 准备输入文件

- **PDF工程图纸**: 包含BOM表格、技术要求、装配图的PDF文件
- **3D模型文件**: STL或STEP格式的3D模型文件

### 3. 生成装配说明书

```bash
python main.py \
  --pdf 图纸1.pdf 图纸2.pdf \
  --models 模型1.step 模型2.stl \
  --output ./output \
  --focus welding
```

### 4. 查看结果

生成的文件结构：
```
output/
├── assembly_manual.html      # 主要的装配说明书
├── assembly_data.json        # 装配数据
├── models/                   # 转换后的GLB模型
│   ├── model_001.glb
│   └── model_002.glb
├── static/                   # 静态资源
│   ├── style.css
│   └── app.js
└── processing_result.json    # 完整处理结果
```

用浏览器打开 `assembly_manual.html` 即可查看装配说明书。

## 📋 使用说明

### 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--pdf` | PDF工程图纸文件 (必需) | `--pdf 图纸1.pdf 图纸2.pdf` |
| `--models` | 3D模型文件 (必需) | `--models 模型.step 零件.stl` |
| `--output` | 输出目录 | `--output ./output` |
| `--focus` | 专业重点类型 | `--focus welding` |
| `--requirements` | 特殊要求描述 | `--requirements "高精度装配"` |

### 专业重点类型

- `general`: 通用装配 (默认)
- `welding`: 焊接重点
- `precision`: 精密装配  
- `heavy`: 重型装配

### 环境变量

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `DASHSCOPE_API_KEY` | 阿里云DashScope API密钥 | ✅ |
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | ✅ |
| `BLENDER_EXE` | Blender可执行文件路径 | ❌ |

## 🎯 输出说明书特性

### 工人友好设计
- **大字体高对比度**: 适合车间环境
- **步骤导航**: 清晰的进度条和上下步按钮
- **移动端适配**: 支持手机、平板、工业显示屏
- **离线使用**: PWA技术，无需网络连接

### 3D模型交互
- **模型查看**: 360度旋转、缩放、平移
- **爆炸视图**: 可调节的零件分离显示
- **步骤关联**: 每步高亮相关零件

### 装配指导内容
- **操作说明**: 详细的文字描述
- **零件清单**: 每步涉及的零件
- **工具要求**: 所需工具和设备
- **关键要点**: 重要的技术要求
- **安全提醒**: 安全注意事项
- **质量检查**: 质检要点和标准

## 🔧 技术栈

### AI模型
- **Qwen3-VL**: 阿里云视觉大模型，用于工程图纸解析
- **DeepSeek-Chat**: DeepSeek对话模型，装配工艺专家

### 核心技术
- **Python**: 后端处理引擎
- **Three.js**: 3D模型渲染
- **Jinja2**: HTML模板引擎
- **PyMuPDF**: PDF处理
- **Blender**: 3D模型转换

### 前端技术
- **HTML5/CSS3**: 响应式界面
- **JavaScript ES6+**: 交互逻辑
- **PWA**: 离线支持

## 📁 项目结构

```
装修说明书项目/
├── main.py                   # 主程序入口
├── requirements.txt          # 依赖包列表
├── README.md                # 项目说明
├── prompts/                 # 提示词模块
│   ├── vision_prompts.py    # 视觉模型提示词
│   └── assembly_expert_prompts.py  # 装配专家提示词
├── models/                  # AI模型调用
│   ├── vision_model.py      # Qwen3-VL模型
│   └── assembly_expert.py   # DeepSeek专家模型
├── processors/              # 文件处理器
│   └── file_processor.py    # PDF和3D模型处理
├── core/                    # 核心处理流水线
│   └── pipeline.py          # 主处理流程
├── generators/              # 生成器
│   ├── html_generator.py    # HTML说明书生成器
│   └── templates/           # HTML模板
└── step-stl文件/           # 测试用3D模型文件
```

## 🎨 自定义和扩展

### 提示词定制
提示词采用模块化设计，可以轻松调整：

```python
# 修改视觉模型提示词
from prompts.vision_prompts import build_vision_prompt

custom_prompt = build_vision_prompt(focus_areas=['welding', 'quality'])
```

### HTML模板定制
可以修改 `generators/templates/` 中的模板文件来自定义界面。

### 添加新的专业领域
在 `prompts/assembly_expert_prompts.py` 中添加新的专业知识库。

## 🔍 故障排除

### 常见问题

1. **API密钥错误**
   ```bash
   ❌ 错误: 请设置DASHSCOPE_API_KEY环境变量
   ```
   解决: 确保正确设置了API密钥环境变量

2. **Blender转换失败**
   ```bash
   转换失败: 找不到Blender可执行文件
   ```
   解决: 安装Blender并设置BLENDER_EXE环境变量

3. **模型加载失败**
   ```bash
   加载模型失败: models/model_001.glb
   ```
   解决: 检查3D模型文件格式和完整性

### 调试模式

使用 `-v` 参数启用详细输出：
```bash
python main.py --pdf test.pdf --models test.step --output ./debug -v
```

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📞 支持

如有问题或建议，请提交Issue或联系项目维护者。
