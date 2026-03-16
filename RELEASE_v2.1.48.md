# 🎉 Release v2.1.48 - AI智能装配指导平台

> **发布日期**: 2026-03-13  
> **版本范围**: v2.1.43 - v2.1.48  
> **重大更新**: HTTPS 证书改为部署时挂载、私钥泄露收口与证书轮换、内网扫码能力保留、PDF 文本层 BOM 与产品总装匹配收口

---

## 🎯 这个版本做了什么？（说人话版）

### 💡 这版最重要的变化

1. **把 HTTPS 私钥从仓库和镜像里彻底拿掉了** 🔐
   - 前端镜像不再内置 `frontend/ssl/*`
   - 证书和私钥只保留在部署机本地，通过 `docker-compose.yml` 运行时只读挂载
   - 后续即使重新构建镜像，也不会再把 `server.key` 顺手带进 Git 或 Docker build context

2. **已经泄露过的那套证书，整套换新了** ♻️
   - 重新生成了新的 `rootCA.crt / rootCA.cer / server.crt / server.key`
   - 旧的 `v2.1.47` tag 已删除
   - GitHub 主线历史已经改写，远端 `main` 现在切到安全版本 `v2.1.48`

3. **手机扫一扫功能保住了，没有因为安全处理被砍掉** 📱
   - 仍然保留 `3443` HTTPS 入口
   - Nginx 仍然使用本地挂载的 `server.crt + server.key`
   - Android 系统浏览器在信任证书后，依旧可以直接扫码回填物料代码

4. **之前 `v2.1.47` 的核心业务改动也都还在** 🧠
   - PDF 文本层 BOM 固定 6 列提取
   - 产品总装 BOM/3D 匹配收口
   - 步骤标题禁止带数量/规格
   - 同源 API / WebSocket / SSE + 内网 HTTPS 扫码链路

---

## 🐛 这次重点解决了什么问题

### 1. GitHub 私钥泄露风险

- 之前：`frontend/Dockerfile` 会直接 `COPY ssl /etc/nginx/ssl`
- 后果：`server.key` 既可能被提交到仓库，也可能被打进前端镜像层
- 现在：证书目录只保留在宿主机本地，仓库和镜像都不再包含私钥

### 2. Docker 构建上下文误带敏感文件

- 之前：`.gitignore` 和 Docker 忽略规则都没把 `frontend/ssl/` 完整挡住
- 后果：即使不提交 Git，也可能在构建时把私钥带进 build context
- 现在：根目录 `.dockerignore`、`.gitignore`、`frontend/.dockerignore` 同时排除 `frontend/ssl/`

### 3. 旧泄露提交仍被 tag 和主线引用

- 之前：泄露发生在 `release: v2.1.47`，而且 `v2.1.47` tag 直接指向这次提交
- 现在：远端 `main` 已重写到新的 `release: v2.1.48`，远端 `v2.1.47` 已删除，新的安全 tag 为 `v2.1.48`

### 4. 扫码需要 HTTPS，但不能因此继续内置私钥

- 之前：为了保住扫码，交付链路默认把证书目录直接塞进镜像
- 现在：扫码所需 HTTPS 仍保留，但改成“部署时挂载证书”，把运行时依赖和源码仓库边界彻底分开

---

## 🔧 这版具体包含哪些版本

### v2.1.48 (2026-03-13)

- **HTTPS 证书改为部署时挂载（私钥不再进仓库/镜像）**
- `frontend/Dockerfile` 去掉 `COPY ssl`
- `docker-compose.yml` 改为 `./frontend/ssl:/etc/nginx/ssl:ro`
- 删除 `frontend/ssl/*` 的 Git 跟踪
- 根目录 `.dockerignore`、`.gitignore`、`frontend/.dockerignore` 同时排除 `frontend/ssl/`
- 重签新的 `rootCA / server` 证书链
- 删除远端泄露 tag `v2.1.47`，发布新的 `v2.1.48`

### v2.1.47 (2026-03-11)

- **步骤标题去数量口径 + NewAPI 快捷模型补充**
- 统一组件/产品模式标题规则，禁止标题写数量、规格、括号
- 设置页 `NewAPI` 快捷模型新增 `qwen3.5-plus-2026-02-15`

### v2.1.46 (2026-03-10)

- **产品总装步骤归属锁定 + 重复节点高亮收口**
- 新增步骤级 `bom_seq` 归属收口，跨步骤串件会被清掉
- 查看器只高亮当前步骤首次出现的节点，颜色语义恢复正常

### v2.1.45 (2026-03-10)

- **BOM 匹配收口二次重构**
- 最终兜底从规则改成复用当前模型做 AI 补漏
- PDF 文本层 BOM 升级为固定 6 列提取：`seq/code/product_code/name/material/quantity`

### v2.1.44 (2026-03-10)

- **产品总装匹配收口修复**
- 修复最后一条 BOM 被尾部脏数据污染
- 层级匹配改为底座锁定
- 新增标准件异名兜底与未绑 3D 步骤告警

### v2.1.43 (2026-03-09)

- **Viewer 内网 HTTPS 扫码实装验证**
- 前端切到同源 API/WS/SSE
- Nginx 增加 `443 ssl`
- `docker-compose.yml` 暴露 `3443:443`
- 真机扫码验证通过

- **PDF 文本层 BOM 关键字段稳提 + `quantity` 文本纠偏**
- 先保证 `seq/code/product_code/name/quantity` 关键字段稳定拿到
- 文本层 `quantity` 允许覆盖 Vision 冲突值

---

## 📦 部署和升级提醒

1. **必须准备本地证书目录**

```text
frontend/ssl/
├── server.crt
├── server.key
├── rootCA.crt
└── rootCA.cer
```

2. **证书目录现在是运行时挂载，不再来自 Git**
   - `frontend/ssl/` 是宿主机本地目录
   - 容器通过 `docker-compose.yml` 只读挂载到 `/etc/nginx/ssl`
   - 如果这个目录缺文件，前端 HTTPS 容器会启动失败

3. **这次必须重新分发并重新信任新证书**
   - 旧的根证书和服务证书已经废弃
   - 客户手机/电脑需要重新安装新的 `rootCA.crt` / `rootCA.cer`

4. **建议直接重建并重启服务**

```bash
docker-compose down
docker-compose up -d --build
```

5. **访问地址**
   - HTTP：`http://localhost:3008`
   - HTTPS：`https://localhost:3443`

---

## 🔗 相关链接

- **GitHub 仓库**: https://github.com/xiaotang-12-ops/yilite.git
- **Tag**: `v2.1.48`
- **Compare**: https://github.com/xiaotang-12-ops/yilite/compare/v2.1.42...v2.1.48
- **详细技术变更**: `Memory_Development/changelog.md`

---

## 📝 一句话总结

这版最核心的价值不是“再加一个功能”，而是把 **HTTPS 扫码交付链路真正做成安全可交付的版本**：**私钥不再进仓库、不再进镜像、旧泄露已收口、扫一扫能力保留，客户现场仍可正常使用。**
