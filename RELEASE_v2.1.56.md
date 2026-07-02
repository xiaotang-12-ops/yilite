# Release v2.1.56 - 用户部署线设置持久化与隐藏入口升级

> **发布日期**: 2026-07-02  
> **版本范围**: v2.1.55 - v2.1.56  
> **重大更新**: 用户部署线隐藏设置入口改为长按 5 秒、AI 配置改为跨重启持久化、镜像与部署口径升级到 `v2.1.56`

---

## 这版做了什么

1. **隐藏设置入口改为长按 5 秒**
   - 保留用户现场原 `logo.png` 和标题
   - 不再使用“10 秒内连点 10 次”进入 `/settings`
   - 改为品牌区鼠标左键长按 5 秒解锁
   - 额外补了 `touchstart / touchend / touchcancel`，避免后续移动端调试时完全进不去

2. **AI 设置改为后端落盘持久化**
   - `OpenRouter / DeepSeek / NewAPI` Key
   - 每个调用点的 `provider / model / fallback_model / custom_key`
   - 现在会写入 `runtime_settings/app_settings.json`
   - Docker 重启、后端重启、系统重启后会优先从该文件恢复

3. **空白保存不再误清空服务端 Key**
   - 设置页现在会区分：
     - 用户这次没有动过输入框
     - 用户明确把 Key 清空
   - 浏览器本地缓存丢失时，留空保存默认保留服务端已有 Key

4. **部署口径升级到 `v2.1.56`**
   - `docker-compose.yml` 的前后端镜像名与容器名同步改为 `v2.1.56`
   - 新增 `runtime_settings` 绑定挂载
   - 补齐 `DEEPSEEK_API_KEY / NEWAPI_API_KEY / ARK_API_KEY` 透传

---

## 这次重点解决了什么问题

### 1. 为什么之前一重启就丢配置

旧版 `v2.1.55` 的 `/api/settings` 只把设置放在：

- Python 进程内存 `app_settings`
- 当前进程的 `os.environ`

这两者都不会自动写回磁盘，所以：

- Docker 重启
- 后端进程重启
- 系统重启

之后，后端又会回到默认环境变量和默认 `openrouter` 调用点配置。

### 2. 为什么看起来像“本地存储也没了”

前端虽然会把设置页内容缓存到浏览器 `localStorage`，但页面重新打开时还会再请求后端 `/api/settings`。  
旧版后端一重启就回默认，前端又会把服务端返回的默认调用点盖回页面，所以看起来像“全部都清空了”。

---

## 这版的技术落点

- `frontend/src/App.vue`
  - 改隐藏入口解锁方式
- `frontend/src/views/Settings.vue`
  - 引入 `persistedKeyPresence / serverKeyPresenceKnown / keyFieldTouched`
  - 实现“未改动留空 = 保留服务端值”
- `backend/simple_app.py`
  - 新增 `runtime_settings/app_settings.json` 持久化
  - 启动优先读取
  - 保存先原子落盘、再切换内存和环境变量
  - 新增 `/api/settings/health`
- `docker-compose.yml`
  - 增加 `./runtime_settings:/app/runtime_settings`
- `tests/test_runtime_settings_persistence.py`
  - 覆盖“保留、局部调用点保留、清空、文件优先、失败回滚”五条回归

---

## 部署和升级提醒

1. **升级前先停掉旧容器**

如果当前机器上还在运行旧的 `v2.1.58` 本地测试容器，先执行：

```bash
docker compose down --remove-orphans
```

如果旧容器是手动启动的，也可以先：

```bash
docker stop assembly-backend-v2.1.58 assembly-frontend-v2.1.58
docker rm assembly-backend-v2.1.58 assembly-frontend-v2.1.58
```

2. **重建并启动 `v2.1.56`**

```bash
docker-compose up -d --build
```

3. **首次保存后会生成运行时设置文件**

```text
runtime_settings/
└── app_settings.json
```

这个文件包含 AI Key 和调用点配置，后续重启恢复就依赖它。

---

## 验证结论

已完成：

- `python -m py_compile backend/simple_app.py`
- `npm --prefix frontend run build`
- `docker compose config`
- `pytest tests/test_runtime_settings_persistence.py`
- `docker compose up -d --build`
- `docker compose restart backend frontend`
- 重启后再次访问 `http://127.0.0.1:8008/api/settings/health`，确认 `config_source = runtime_file`
- 用户已手测桌面端“长按 5 秒进入设置页”，反馈“没啥太大问题”

已确认通过外部代码审核。

仍需后续补齐：

- 若后续确实要在平板/手机上进入隐藏设置页，建议再做一次真实触屏长按验收

---

## 一句话结论

`v2.1.56` 的价值不是“再加一个设置按钮”，而是把**用户部署线最容易出现场故障的 AI 配置链路真正持久化了**：以后改完 Key、模型和兜底设置，不会再因为重启就回到默认 `openrouter`。
