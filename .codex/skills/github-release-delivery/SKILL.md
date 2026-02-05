---
name: github-release-delivery
description: 当用户准备“推到 GitHub等平台/做版本发布/打 tag/做 GitHub Release/补交付文档”时启用：提供与 GitHub 强绑定的发版交付清单（VERSION、tag、release、README、DEPLOYMENT 等），并说明每步目的与风险点。
---

## 核心交付清单（按需执行）
- `VERSION` 文件更新（或等价版本源）
- 创建 Git tag 并推送
- 创建 GitHub Release（附变更摘要）
- 更新 `README.md`（安装/运行/常见问题）
- 更新 `DEPLOYMENT.md`（部署方式/环境变量/回滚）
- 若涉及容器：检查 compose 镜像命名与版本策略（可与 docker 规范 skill 联动）

- 准备上传代码到github等平台时，需要检查项目使用说明**README.md**
- 记得检查项目的docker-compose.yml文件，确保每个镜像和容器都有一个独一无二的契合版本号的镜像名字，例如image: assembly-manual-frontend:v1.1.6（避免不同版本号用同一镜像）
- 上传GitHub时必须包含完整的版本控制体系：创建（修改）VERSION文件、打Git标签、推送标签、创建GitHub Release、更新README和DEPLOYMENT文档