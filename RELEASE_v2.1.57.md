# Release v2.1.57 - ManualViewer 模型与网格位置调整

> **发布日期**：2026-07-20
> **版本范围**：v2.1.56 - v2.1.57
> **核心更新**：网格自动基线、按 GLB 独立位置配置、右侧无蒙层实时调整面板

---

## 用户可见变化

1. **网格默认位置适配不同模型**
   - 不再为所有 GLB 固定使用 `y=-5`。
   - 默认网格会根据模型归位后的包围盒底部和模型尺寸自动计算。

2. **桌面管理员可直接“调整位置”**
   - 入口位于手册 3D 控制区。
   - 可调整“网格上下位置”“模型左右位置”“模型上下位置”。
   - 拖动滑块只做本地实时预览，点击保存时才写入一笔手册草稿。

3. **调整时模型始终可见**
   - 面板固定覆盖右侧说明区域，不使用居中弹窗或全屏灰色遮罩。
   - 中间 3D 画布不重排，管理员可以继续旋转、缩放并观察实时效果。

4. **每个 GLB 独立保存**
   - 配置按 `glb_file` 隔离，同一手册中的多个模型不会串值。
   - 普通查看者读取手册已发布配置；历史版本和移动端不显示编辑入口。

5. **旧手册直接兼容**
   - 没有新字段的旧手册自动使用默认位置，不需要批量迁移 JSON。
   - “恢复默认”会移除当前 GLB 的手动值并重新使用自动计算。

---

## 技术落点

- `frontend/src/views/ManualViewer.vue`
  - 缓存归位包围盒与当前 GLB key。
  - 使用唯一网格 Group 更新网格和边界位置。
  - 同步平移相机与 `OrbitControls.target`，不移动模型世界坐标。
  - 复用现有 `save-draft` 数据链并保持取消回退、失败重试逻辑。
- `frontend/src/views/manual-viewer/sceneCalibration.ts`
  - 提供 schema v1、归一化偏移、按 GLB 读写、旧数据和非法包围盒回退。
- `frontend/src/views/manual-viewer/components/SceneCalibrationPanel.vue`
  - 提供右侧无蒙层面板和用户可理解的控制文案。
- `frontend/tests/sceneCalibration*.test.mjs`
  - 覆盖纯数据、按 GLB 隔离、恢复默认、非模态呈现和事件契约。

持久化字段：

```text
metadata.viewer_settings.scene_calibration_by_glb[glb_file]
```

该版本不新增数据库、后端接口或独立设置文件。

---

## 验证结果

- `npm.cmd run build`：通过，Vite 构建 `1856 modules`。
- `node --test tests/sceneCalibration.test.mjs tests/sceneCalibrationPanel.test.mjs`：`9/9` 通过。
- `git diff --check`：通过。
- 核心 Three.js 状态和手册数据流：完成两轮有效外部代码审查。
- 页面验收：小糖自行重建最新容器后反馈“验收好了没啥问题”。

已知非阻塞边界：项目当前 `vue-tsc@1.8.27` 与 `typescript@5.9.3` 不兼容，独立类型检查仍无法运行；生产构建通过。

---

## 升级方式

```bash
git fetch --tags origin
git checkout v2.1.57
docker compose build
docker compose up -d
```

升级前请按实际部署环境备份手册数据，并停止占用 `8008/3008/3443` 端口的旧版容器。`docker-compose.yml` 中前后端镜像与容器名已经切换为 `v2.1.57`。

---

## 回滚

```bash
git checkout v2.1.56
docker compose build
docker compose up -d
```

本次只扩展手册 JSON 的可选元数据字段。旧版本会忽略该附加字段，不需要数据库回滚。
