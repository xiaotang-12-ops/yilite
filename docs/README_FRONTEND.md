# 🎨 智能装配说明书生成系统 - 前端界面

基于Vue3 + TypeScript + Element Plus + Three.js构建的现代化前端界面，提供科技感十足的用户体验。

## ✨ 特性亮点

### 🚀 现代化技术栈
- **Vue 3** - 最新的Vue框架，Composition API
- **TypeScript** - 类型安全的JavaScript
- **Vite** - 极速的构建工具
- **Element Plus** - 企业级UI组件库
- **Three.js** - 强大的3D渲染引擎
- **GSAP** - 专业的动画库

### 🎯 核心功能
- **智能文件上传** - 支持拖拽上传，实时进度显示
- **3D模型查看器** - 支持GLB/GLTF格式，爆炸视图，零件高亮
- **实时生成进度** - WebSocket实时状态更新
- **响应式设计** - 完美适配桌面、平板、手机
- **暗色主题** - 支持明暗主题切换
- **离线支持** - PWA技术，支持离线使用

### 🎨 视觉设计
- **科技感UI** - 渐变色彩，玻璃态效果
- **流畅动画** - 页面切换，元素交互动画
- **3D交互** - 模型旋转，缩放，爆炸视图
- **数据可视化** - 实时图表，进度指示器

## 📁 项目结构

```
frontend/
├── public/                 # 静态资源
│   ├── models/            # 3D模型文件
│   ├── images/            # 图片资源
│   └── animations/        # Lottie动画
├── src/
│   ├── components/        # 组件
│   │   ├── ThreeViewer.vue    # 3D查看器
│   │   ├── FileUploader.vue   # 文件上传器
│   │   └── ProgressTracker.vue # 进度跟踪器
│   ├── views/             # 页面
│   │   ├── Home.vue           # 首页
│   │   ├── Generator.vue      # 生成器
│   │   └── Viewer.vue         # 查看器
│   ├── api/               # API服务
│   │   └── index.ts           # API接口
│   ├── stores/            # 状态管理
│   │   └── app.ts             # 应用状态
│   ├── style/             # 样式
│   │   └── main.scss          # 全局样式
│   ├── utils/             # 工具函数
│   └── types/             # 类型定义
├── package.json           # 依赖配置
├── vite.config.ts         # Vite配置
└── tsconfig.json          # TypeScript配置
```

## 🚀 快速开始

### 环境要求
- Node.js >= 16.0.0
- npm >= 8.0.0

### 安装依赖
```bash
cd frontend
npm install
```

### 开发模式
```bash
npm run dev
```

### 构建生产版本
```bash
npm run build
```

### 预览生产版本
```bash
npm run preview
```

## 🎯 页面功能

### 🏠 首页 (Home)
- **英雄区域** - 产品介绍，特性展示
- **3D预览** - 实时3D模型展示
- **功能特性** - 核心功能介绍
- **工作流程** - 步骤说明
- **统计数据** - 动态数字展示

### 🔧 生成器 (Generator)
- **文件上传** - PDF和3D模型上传
- **配置选项** - 专业重点，质量等级设置
- **实时进度** - 生成过程可视化
- **结果展示** - 完成状态和统计信息

### 👁️ 查看器 (Viewer)
- **3D交互** - 模型查看，爆炸视图
- **步骤导航** - 装配步骤浏览
- **BOM清单** - 零件列表管理
- **技术图纸** - 工程图纸查看
- **质量检查** - 检查项目管理

## 🎨 3D查看器功能

### 基础功能
- **模型加载** - 支持GLB/GLTF格式
- **相机控制** - 旋转，缩放，平移
- **自动旋转** - 可选的自动旋转模式
- **网格显示** - 可选的参考网格

### 高级功能
- **爆炸视图** - 零件分解展示
- **零件高亮** - 鼠标悬停高亮
- **材质切换** - 线框，实体模式
- **环境设置** - 背景，光照调节
- **性能监控** - FPS，多边形数量显示

### 交互控制
- **鼠标操作**
  - 左键拖拽：旋转视角
  - 右键拖拽：平移视角
  - 滚轮：缩放视角
- **键盘快捷键**
  - 空格：播放/暂停动画
  - R：重置视角
  - F：全屏模式
  - 1-9：切换预设视角

## 🎭 主题和样式

### 颜色系统
```scss
// 主色调
--primary-color: #409eff;
--primary-light: #79bbff;
--primary-dark: #337ecc;

// 渐变色
--gradient-primary: linear-gradient(135deg, #409eff, #67c23a);
--gradient-secondary: linear-gradient(135deg, #e6a23c, #f56c6c);
```

### 动画效果
- **页面切换** - 淡入淡出，滑动效果
- **元素交互** - 悬浮，点击反馈
- **加载状态** - 骨架屏，进度条
- **3D动画** - 模型旋转，爆炸动画

### 响应式设计
- **桌面端** - 1200px以上，三栏布局
- **平板端** - 768-1200px，两栏布局
- **移动端** - 768px以下，单栏布局

## 🔧 配置说明

### 环境变量
```bash
# API基础URL
VITE_API_BASE_URL=http://localhost:8000/api

# 是否启用开发模式
VITE_DEV_MODE=true

# 3D模型基础路径
VITE_MODEL_BASE_URL=/models
```

### Vite配置
```typescript
export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
    }),
    Components({
      resolvers: [ElementPlusResolver()],
    })
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

## 📱 PWA支持

### 离线功能
- **缓存策略** - 静态资源缓存
- **离线页面** - 网络断开时的备用页面
- **后台同步** - 网络恢复时的数据同步

### 安装提示
- **桌面安装** - 支持安装到桌面
- **移动端添加** - 添加到主屏幕
- **更新提醒** - 新版本更新通知

## 🚀 性能优化

### 代码分割
- **路由懒加载** - 按需加载页面组件
- **组件懒加载** - 大型组件异步加载
- **第三方库分割** - 独立打包第三方库

### 资源优化
- **图片压缩** - 自动压缩图片资源
- **字体优化** - 字体子集化
- **3D模型优化** - 模型压缩，LOD技术

### 运行时优化
- **虚拟滚动** - 大列表性能优化
- **防抖节流** - 事件处理优化
- **内存管理** - 及时清理3D资源

## 🐛 调试和测试

### 开发工具
- **Vue DevTools** - Vue组件调试
- **Three.js Inspector** - 3D场景调试
- **Network Monitor** - 网络请求监控

### 错误处理
- **全局错误捕获** - 统一错误处理
- **API错误处理** - 接口异常处理
- **3D渲染错误** - WebGL错误处理

## 📚 相关文档

- [Vue 3 官方文档](https://vuejs.org/)
- [Element Plus 文档](https://element-plus.org/)
- [Three.js 文档](https://threejs.org/docs/)
- [Vite 文档](https://vitejs.dev/)
- [TypeScript 文档](https://www.typescriptlang.org/)

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
