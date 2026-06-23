---
name: book-hunter
description: 'Search public ebook metadata and source pages across Z-Library, Anna''s Archive, and web-search fallbacks. Supports title/author/ISBN queries, format (epub/pdf/mobi) and language (zh/en) filters, and bounded fallback when mirrors fail. Triggers: search books, find ebook metadata, book search, search ebook, zlib, anna, ISBN search. Not for: purchasing physical books; internal document search; bypassing paywalls, DRM, logins, or copyright restrictions; downloading files for the user.'
---

# 图书猎手 4.0.0

**一句话查询 Z-Library + Anna's Archive 的公开图书元数据和来源页面。** 8 镜像 + Camoufox + Jina + Exa 四层降级，失败时要明确报告原因。

---

## 首次使用

首次使用前请运行依赖检测脚本：
```bash
bash scripts/setup.sh
```
Windows 可使用 Git Bash 运行同一命令；若只使用 PowerShell，按 Quick Start 的 PowerShell 版本安装依赖并直接运行 Python 脚本。
> Agent 会在首次触发时自动执行此脚本，通常无需手动操作。
> 注意：Camoufox 浏览器二进制下载约 80-150MB，首次安装可能耗时几分钟。

---

## Quick Start

```bash
# 1. 安装依赖
pip install requests beautifulsoup4 lxml camoufox

# 2. 找到脚本路径（先验证脚本存在）
SKILL=$(find . -name "book_hunter.py" -path "*/scripts/*" 2>/dev/null | head -1)
if [ -z "$SKILL" ]; then
  echo "⚠️ book_hunter.py not found. Reinstall: git clone https://github.com/rrrrrredy/book-hunter && cd book-hunter"
else
  echo "✅ Script path: $SKILL"
fi

# 3. 验证（搜一本书）
python3 "$SKILL" "三体"
```

PowerShell:
```powershell
# 1. 安装依赖
python -m pip install requests beautifulsoup4 lxml camoufox

# 2. 找到脚本路径
$skill = Get-ChildItem -Recurse -Filter book_hunter.py | Where-Object { $_.FullName -match '\\scripts\\book_hunter\.py$' } | Select-Object -First 1
if (-not $skill) {
  Write-Error "book_hunter.py not found. Reinstall: git clone https://github.com/rrrrrredy/book-hunter"
} else {
  python $skill.FullName "三体"
}
```

---

## 场景映射表

| 用户说 | Agent 执行 |
|:---|:---|
| `搜书 三体` | `python3 $SKILL "三体"` |
| `找 Atomic Habits epub` | `python3 $SKILL "Atomic Habits" --format epub` |
| `搜中文机器学习书` | `python3 $SKILL "机器学习" --lang zh` |
| `作者 吴恩达 的书` | `python3 $SKILL "深度学习" --author 吴恩达` |
| `ISBN 9787536692930` | `python3 $SKILL --isbn 9787536692930` |
| `找 pdf 英文 LLM` | `python3 $SKILL "LLM" --format pdf --lang en` |

> `$SKILL` = `<install-dir>/scripts/book_hunter.py`

---

## 参数说明

| 参数 | 简写 | 说明 | 示例 |
|:---|:---|:---|:---|
| `--format` | `-f` | 格式筛选 (epub/pdf/mobi/azw3) | `-f epub` |
| `--lang` | `-l` | 语言筛选 (zh/en) | `-l zh` |
| `--author` | `-a` | 作者筛选（模糊匹配） | `-a 吴恩达` |
| `--isbn` | `-i` | ISBN 精确搜索（优先级最高） | `-i 9787536692930` |
| `--limit` | `-n` | 每来源结果数（默认10，最多20） | `-n 5` |

---

## 降级链

```
Z-Library（requests + 上游代理）
    ↓ 503 / 反爬
Z-Library（Camoufox 无头浏览器 + 上游代理）
    ↓ 解析无结果
Anna's Archive（requests + 上游代理，多域名轮询）
    ↓ 反爬 / 被封
Anna's Archive（Jina Reader r.jina.ai 文本代理）
    ↓ 两站均失败
mcporter/Exa (agent-reach ecosystem) → Jina Search API fallback
    ↓ 无结果
提示用户直接访问来源页 + 建议关键词调整
```

---

## 输出格式

List style, IM-friendly:

```
📚 图书猎手 — 「三体」
找到 8 本（Z-Lib 5 + Anna 3 + Exa 0）

━━ Z-Library（5本）━━
1. 《三体》
   作者: 刘慈欣  格式: EPUB  大小: 1.2MB  语言: Chinese
   🔗 https://z-library.sk/book/xxxxxx

2. 《三体II：黑暗森林》
   ...

━━ Anna's Archive（3本）━━
...

💡 点击链接查看来源页面；如需获取文件，请遵守站点规则和当地版权法律
⚠️ 请遵守当地版权法规
```

---

## 镜像与代理说明

- **Proxy** (optional): Set `HTTP_PROXY` env var if needed
- **Timeouts** (optional): `BOOK_HUNTER_MIRROR_TIMEOUT`, `BOOK_HUNTER_SEARCH_TIMEOUT`, `BOOK_HUNTER_JINA_TIMEOUT`, `BOOK_HUNTER_WEB_TIMEOUT`, `BOOK_HUNTER_BROWSER_TIMEOUT`, `BOOK_HUNTER_BROWSER_PROCESS_TIMEOUT`. Defaults are intentionally short for agent use; raise them only when the network is slow but reachable. Set `BOOK_HUNTER_BROWSER_ENABLED=0` for fast network diagnostics that skip Camoufox.
- **Z-Library 镜像**：探测结果缓存 `~/.book-hunter/mirrors.json`，6小时有效，下次不重复探测
- **Anna's Archive 域名**：annas-archive.org / .gs / .se 轮询
- **Camoufox**: Auto-invoked when Z-Library blocks requests (pip install camoufox)

> 镜像缓存格式、完整域名列表及 Exa 兜底机制详见 `references/mirror-status.md`。

---

## 依赖

```bash
pip install requests beautifulsoup4 lxml camoufox
```

Web search fallback: **mcporter/Exa** (agent-reach ecosystem, best results) → **Jina Search API** (free, no key). Install: `pip install agent-reach && agent-reach install --env=auto --safe` then `npm i -g mcporter && mcporter config add exa https://mcp.exa.ai/mcp`

---

## Gotchas

以下是已知高频踩坑，遇到问题优先对照检查：

⚠️ Z-Library 8个镜像全部 503 → 先清除镜像缓存 `rm ~/.book-hunter/mirrors.json`，重新探测；若仍失败说明当前网络无法访问 Z-Lib，降级到 Anna's Archive

⚠️ Camoufox 启动失败（`ModuleNotFoundError`）→ 需先 `pip install camoufox` 并运行 `python3 -m camoufox fetch` 下载浏览器二进制，缺少这一步会直接报错

⚠️ Anna's Archive 三个域名（.org/.gs/.se）均不可达 → Jina Reader 文本代理：`r.jina.ai/https://annas-archive.org/...`，但 Jina 有速率限制，不要连续大量请求

⚠️ Exa 兜底搜索返回无关结果 → Exa 是通用搜索，不专精图书；结果质量差时应告知用户手动搜索，不要把低质量结果当作答案返回

⚠️ 镜像缓存 `mirrors.json` 过期未清除 → 缓存有效期 6 小时，若搜索持续失败超过 6 小时，先手动删除缓存再重试

PowerShell cache cleanup:
```powershell
Remove-Item -ErrorAction SilentlyContinue "$HOME\.book-hunter\mirrors.json"
```

⚠️ ISBN 搜索无结果但书确实存在 → ISBN 格式检查：13位（978开头）或10位，确认没有多余空格；部分旧书只有10位 ISBN，需两种格式都尝试

⚠️ Proxy not available → Set `HTTP_PROXY` env var to a working proxy, or remove proxy config for direct access

⚠️ Windows console shows `UnicodeEncodeError` → run with UTF-8 mode (`PYTHONUTF8=1`) or use the bundled script version that configures UTF-8 stdout/stderr.

---

## Hard Stop

**同一工具调用失败超过 3 次，立即停止，不再尝试。**

列出所有失败方案及原因，标记 **"需要人工介入"**，等待人工确认。

常见需要介入的场景：
- Z-Library 全部镜像失效 + Anna's Archive 三域名均封 + Exa 无结果 → 所有降级路径耗尽，停止并报告已尝试的路径、超时设置和是否使用代理
- `book_hunter.py` 脚本不存在（skill 未正确安装）→ 报告安装路径错误，提示重新安装
- Camoufox 安装失败（pip 网络错误）→ 报告依赖安装失败，停止尝试

---

## 限制说明

- 仅搜索元数据和来源页面，**不登录不下载不存储凭证**
- 不代表用户绕过付费、DRM、登录门槛或版权限制
- 部分来源页面可能失效、被封锁或需要用户自行判断合法性
- 请遵守当地版权法律法规

---

## ⚠️ 安全声明

本 Skill 不收集任何账户信息，不执行任何登录操作，不存储下载文件。所有操作仅限元数据查询。

---

## Changelog

### 4.0.0（2026-04-08）
- description 从多行 block scalar `>` 改为单行（符合 description 设计原则）
- 新增 `tags`（[book, ebook, zlibrary, annas-archive, search]）
- 同步 `scripts/`（book_hunter.py / anna_search.py / zlib_search.py）从安装版到 workspace 版
- 新建 `references/mirror-status.md`（镜像缓存格式、域名列表、Exa 兜底说明）
- frontmatter version V3 → V4，H1 标题同步为 V4
- description 补充触发词：`找电子书`

### v3（历史版本）
- 新增 Gotchas（7 条高频踩坑：镜像缓存、Camoufox 安装、Jina 限速、Exa 降级等）
- 新增 Hard Stop
- 新增降级链（4 层：Z-Lib requests → Z-Lib Camoufox → Anna's Archive → Exa）
- 明确安全声明：不登录不下载不存储凭证

### v2（历史版本）
- 新增 Anna's Archive 三域名轮询 + Jina Reader 绕反爬
- 新增 Exa 全网搜索兜底

### v1（初始版本）
- 初版：Z-Library 镜像探测 + 基础搜索
