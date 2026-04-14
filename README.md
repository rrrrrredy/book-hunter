# book-hunter

Search Z-Library and Anna's Archive for ebook download links, with 4-layer automatic fallback.

An [OpenClaw](https://github.com/openclaw/openclaw) Skill for searching ebook metadata across multiple sources.

## Installation

### Option A: OpenClaw (recommended)
```bash
# Clone to OpenClaw skills directory
git clone https://github.com/rrrrrredy/book-hunter ~/.openclaw/skills/book-hunter

# Run setup (installs Python dependencies)
bash ~/.openclaw/skills/book-hunter/scripts/setup.sh
```

### Option B: Standalone
```bash
git clone https://github.com/rrrrrredy/book-hunter
cd book-hunter
bash scripts/setup.sh
```

## Dependencies

### Python packages
- `requests`
- `beautifulsoup4`
- `lxml`
- `camoufox` (optional, auto-invoked when Z-Library blocks requests)

### Other Skills (optional)
None

## Usage

```bash
# Search by title
python3 scripts/book_hunter.py "三体"

# Search by format
python3 scripts/book_hunter.py "Atomic Habits" --format epub

# Search by language
python3 scripts/book_hunter.py "机器学习" --lang zh

# Search by ISBN
python3 scripts/book_hunter.py --isbn 9787536692930

# Combined filters
python3 scripts/book_hunter.py "LLM" --format pdf --lang en --limit 5
```

### Parameters

| Param | Short | Description | Example |
|:---|:---|:---|:---|
| `--format` | `-f` | Format filter (epub/pdf/mobi/azw3) | `-f epub` |
| `--lang` | `-l` | Language filter (zh/en) | `-l zh` |
| `--author` | `-a` | Author filter (fuzzy match) | `-a "Liu Cixin"` |
| `--isbn` | `-i` | ISBN exact search (highest priority) | `-i 9787536692930` |
| `--limit` | `-n` | Results per source (default 10, max 20) | `-n 5` |

### Fallback Chain

```
Z-Library (requests + proxy)
    ↓ 503 / anti-bot
Z-Library (Camoufox headless browser)
    ↓ no results
Anna's Archive (requests, multi-domain rotation)
    ↓ blocked
Anna's Archive (Jina Reader bypass)
    ↓ both sites fail
Web search fallback (optional, requires exa CLI)
    ↓ no results
Manual search suggestion
```

## Project Structure

```
book-hunter/
├── SKILL.md              # Main skill definition
├── scripts/
│   ├── setup.sh          # Installation script
│   ├── book_hunter.py    # Main entry point
│   ├── zlib_search.py    # Z-Library search module
│   └── anna_search.py    # Anna's Archive search module
├── references/
│   └── mirror-status.md  # Mirror & domain documentation
└── README.md
```

## Limitations

- Searches metadata only — **does not login, download, or store credentials**
- Links require user login on the respective site to download
- Some books may only have paid versions; free links may expire
- Please comply with local copyright laws

## License

MIT
