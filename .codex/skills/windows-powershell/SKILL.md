---
name: win-ps-ops
description: 用户需要使用 Windows 环境下的 PowerShell 命令/脚本、rg 搜索、文件读取、或 PowerShell + Docker 组合命令时，这里记录很多用户曾经跌倒过的坑：提供“可复制即用”的稳健写法（here-string 落盘执行即删、-LiteralPath、UTF8 JSON 解析、rg -F、Docker exec 引号与 $ 变量转义等）。
---

## 核心规约
- 规则1：凡是超过 1 行逻辑的脚本（node/python/sh）一律：here-string 写临时文件 → 执行 → 立刻删除
- 规则2：rg 默认是正则，不是“包含查找”：遇到括号/反斜杠等字符很容易触发 regex parse error（比如 unclosed group）；想按字面量搜就用 rg -F 'literal'（或 --fixed-strings），并尽量用单引号包住 pattern。
- 规则3：涉及中文路径/中文内容时，优先用 PowerShell 原生 JSON 解析：用 Get-Content -LiteralPath xxx -Raw -Encoding UTF8 | ConvertFrom-Json 代替“把脚本通过管道喂给 python -”，避免中文路径在管道/编码转换时变成 ???? 导致 OSError: Invalid argument。
- 规则4：读文件路径永远用 -LiteralPath：路径里有括号、方括号、中文等时，Get-Content/Select-String 用 -LiteralPath，避免被当成通配符或被错误解析。
- 规则5：rg/命令参数里路径和 pattern 分开：当 pattern/路径容易混淆时，加 --（例如 rg -n 'pattern' -- path），减少“把路径当 pattern”的误判。
- 规则6：先黑盒做分流：优先用 Network/状态码/关键字段把问题定位到层级；若“成功但结果不对”或超时仍无法分流，再升级白盒；同一命令失败 2 次立刻换方案（PowerShell 必须用 here-string 落盘脚本）
- 规则7：写临时验证脚本可以，但验证完立刻删除：避免仓库堆“测试脚本垃圾”
- 规则8：在 PowerShell 里执行 docker exec ... sh -c 这类命令时，凡是包含 $?/$VAR 的脚本片段必须用单引号包住（或转义 $），否则会被 PowerShell 提前展开，导致拿不到容器内真实的变量/退出码。
- 规则9：在 PowerShell + Docker 场景下，尽量避免多层引号/重定向 heredoc；优先“here-string 落盘脚本 + python 执行”，pip 安装遇到 hash/mirror 异常时允许临时切换 PIP_INDEX_URL 做一次性验证。
- 规则10：在 PowerShell 里跑 docker 的复杂多层引号命令时，优先“落盘临时脚本/或 python -c + subprocess”，避免 sh -lc 多层引号导致的语法错误与低效排查。
