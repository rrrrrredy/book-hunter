# book-hunter

Search Z-Library and Anna's Archive for ebook download links — multi-layer automatic fallback.

> OpenClaw Skill — works with [OpenClaw](https://github.com/openclaw/openclaw) AI agents

## What It Does

Searches for ebooks across Z-Library (8 mirrors) and Anna's Archive (3 domains) with multi-layer automatic degradation: Z-Lib requests → Z-Lib Camoufox → Anna's Archive requests → Anna's Archive Jina Reader → mcporter/Exa → Jina Search API. Supports filtering by format (epub/pdf/mobi/azw3), language (zh/en), author, and ISBN. Returns metadata and download page links — no login, no file downloads, no credential storage.

## Quick Start

```bash
openclaw skill install book-hunter
# Or:
git clone https://github.com/rrrrrredy/book-hunter.git ~/.openclaw/skills/book-hunter
```

## Features

- 📚 **Dual-source Search** — Z-Library (8 mirrors) + Anna's Archive (3 domains)
- 🔄 **Multi-layer Fallback** — Z-Lib requests → Z-Lib Camoufox → Anna requests → Anna Jina Reader → mcporter/Exa → Jina Search API
- 🎯 **Precise Filtering** — By format, language, author, or ISBN
- 🪞 **Mirror Auto-detection** — Probes and caches working Z-Lib mirrors (6h TTL)
- 🔒 **Safe by Design** — Metadata search only; no login, no downloads, no credentials

## Usage

```
搜书 三体                       # Basic search
找书 Atomic Habits epub         # Filter by format
搜电子书 机器学习                 # Search ebook
图书搜索 深度学习                 # Book search
找电子书 reinforcement learning  # Find ebook download
搜中文机器学习书                  # Filter by language
ISBN 9787536692930              # Exact ISBN lookup
找 pdf 英文 LLM                 # Combined filters
zlib transformer                # Z-Library search
anna deep learning              # Anna's Archive search
```

## Project Structure

```
book-hunter/
├── SKILL.md
├── scripts/
│   ├── book_hunter.py
│   ├── anna_search.py
│   ├── zlib_search.py
│   └── setup.sh
└── references/
    └── mirror-status.md
```

## Requirements

- OpenClaw agent runtime
- Python 3.8+
- `requests`, `beautifulsoup4`, `lxml`
- Optional: `camoufox` (for anti-scraping bypass)
- Optional: `mcporter` via agent-reach (for Exa fallback search)

## License

[MIT](LICENSE)
