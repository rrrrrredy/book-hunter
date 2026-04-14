#!/usr/bin/env python3
"""
图书猎手 v2 - 主入口
整合 Z-Library + Anna's Archive，带降级链（Camoufox → Jina → Exa/Web Search）

Tool priority for search fallback:
  mcporter/Exa (agent-reach ecosystem) → Jina Search API (free, no key)
"""

import sys
import re
import json
import shutil
import argparse
import subprocess
import requests
from typing import List, Dict, Optional

# 确保同目录下的模块可以 import
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from zlib_search import ZLibSearcher
from anna_search import AnnaSearcher

PROXY = {}
_proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("https_proxy")
if _proxy_url:
    PROXY = {"http": _proxy_url, "https": _proxy_url}

# Check if agent-reach tools are available
HAS_MCPORTER = shutil.which("mcporter") is not None


class BookHunter:

    def __init__(self):
        self.zlib = ZLibSearcher()
        self.anna = AnnaSearcher()

    # ------------------------------------------------------------------ #
    #  搜索
    # ------------------------------------------------------------------ #

    def search(self, query: str,
               format_filter: Optional[str] = None,
               lang_filter: Optional[str] = None,
               author_filter: Optional[str] = None,
               isbn: Optional[str] = None,
               limit: int = 10) -> Dict:

        results = {
            "query": query,
            "isbn": isbn,
            "format_filter": format_filter or "全部",
            "lang_filter": lang_filter or "全部",
            "author_filter": author_filter or "",
            "zlib_results": [],
            "anna_results": [],
            "exa_results": [],
            "total": 0,
        }

        # 1. Z-Library（含 Camoufox 降级）
        print(f"[Z-Library] 搜索: {query}...", file=sys.stderr)
        results["zlib_results"] = self.zlib.search_with_filters(
            query, format_filter=format_filter, lang_filter=lang_filter,
            author_filter=author_filter, limit=limit)

        # 2. Anna's Archive（含 Jina 降级）
        print(f"[Anna's Archive] 搜索: {query}...", file=sys.stderr)
        results["anna_results"] = self.anna.search_with_filters(
            query, format_filter=format_filter, lang_filter=lang_filter,
            author_filter=author_filter, isbn=isbn, limit=limit)

        # 3. 两站都没结果 → Exa/Web Search 终极降级
        if not results["zlib_results"] and not results["anna_results"]:
            print("[降级搜索] 两站无结果，启动 Exa/Web Search...", file=sys.stderr)
            results["exa_results"] = self._search_exa(query, limit)

        all_books = (results["zlib_results"] + results["anna_results"]
                     + results["exa_results"])
        results["total"] = len(self._deduplicate(all_books))

        return results

    def _search_exa(self, query: str, limit: int) -> List[Dict]:
        """Exa/Web 搜索作为终极降级
        Primary: mcporter + Exa (agent-reach ecosystem)
        Fallback: Jina Search API (free, no API key)
        """
        exa_query = f"{query} epub pdf download site:annas-archive.org OR site:z-library.sk"

        # 1. Primary: mcporter + Exa
        if HAS_MCPORTER:
            try:
                result = subprocess.run(
                    ["mcporter", "call",
                     f'exa.web_search_exa(query: "{exa_query}", numResults: {limit})'],
                    capture_output=True, text=True, timeout=20
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    items = data if isinstance(data, list) else data.get("results", [])
                    results = [
                        {
                            "source": "Exa搜索",
                            "title": item.get("title", ""),
                            "author": "Unknown",
                            "format": self._guess_format(item.get("url", "")),
                            "size": "Unknown",
                            "language": "Unknown",
                            "url": item.get("url", ""),
                        }
                        for item in items if item.get("url")
                    ]
                    if results:
                        return results
            except Exception as e:
                print(f"[⚠️ Exa] 搜索失败: {e}", file=sys.stderr)

        # 2. Fallback: Jina Search API
        try:
            jina_url = f"https://s.jina.ai/{requests.utils.quote(exa_query)}"
            proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
            proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

            r = requests.get(
                jina_url,
                headers={"Accept": "application/json", "X-Retain-Images": "none"},
                proxies=proxies, timeout=20
            )
            data = r.json()
            items = data.get("data", [])[:limit]
            return [
                {
                    "source": "Web Search",
                    "title": item.get("title", ""),
                    "author": "Unknown",
                    "format": self._guess_format(item.get("url", "")),
                    "size": "Unknown",
                    "language": "Unknown",
                    "url": item.get("url", ""),
                }
                for item in items if item.get("url")
            ]
        except Exception as e:
            print(f"[⚠️ Web search] Failed: {e}", file=sys.stderr)
        return []

    def _guess_format(self, url: str) -> str:
        for fmt in ["epub", "pdf", "mobi", "azw3"]:
            if fmt in url.lower():
                return fmt.upper()
        return "Unknown"

    def _deduplicate(self, books: List[Dict]) -> List[Dict]:
        seen = set()
        out = []
        for b in books:
            key = f"{b.get('title','')[:40].lower()}_{b.get('author','')[:20].lower()}"
            if key not in seen:
                seen.add(key)
                out.append(b)
        return out

    # ------------------------------------------------------------------ #
    #  Format output (list style, IM-friendly)
    # ------------------------------------------------------------------ #

    def format_output(self, results: Dict) -> str:
        lines = []
        query = results["query"]
        isbn = results.get("isbn")
        all_books = self._deduplicate(
            results["zlib_results"] + results["anna_results"] + results["exa_results"]
        )

        # 标题
        if isbn:
            lines.append(f"📚 图书猎手 — ISBN: {isbn}")
        else:
            lines.append(f"📚 图书猎手 — 「{query}」")

        filters = []
        if results["format_filter"] != "全部":
            filters.append(f"格式: {results['format_filter']}")
        if results["lang_filter"] != "全部":
            filters.append(f"语言: {results['lang_filter']}")
        if results["author_filter"]:
            filters.append(f"作者: {results['author_filter']}")
        if filters:
            lines.append("筛选: " + " | ".join(filters))

        lines.append(f"找到 {len(all_books)} 本（Z-Lib {len(results['zlib_results'])} + Anna {len(results['anna_results'])} + Exa {len(results['exa_results'])}）")
        lines.append("")

        if not all_books:
            lines.append("❌ 未找到相关图书")
            lines.append("")
            lines.append("建议：")
            lines.append("• 检查拼写，或尝试英文关键词")
            lines.append("• 搜书 --format epub --lang en 《书名》")
            lines.append("• 直接访问 annas-archive.org（需代理）")
            return "\n".join(lines)

        # 按来源分组输出
        for source_name, source_books in [
            ("Z-Library", results["zlib_results"]),
            ("Anna's Archive", results["anna_results"]),
            ("Exa 搜索结果", results["exa_results"]),
        ]:
            if not source_books:
                continue
            lines.append(f"━━ {source_name} ({len(source_books)}本) ━━")
            for i, b in enumerate(source_books[:8], 1):
                title = b.get("title", "Unknown")[:45]
                author = b.get("author", "Unknown")[:25]
                fmt = b.get("format", "?")
                size = b.get("size", "?")
                lang = b.get("language", "?")[:8]
                url = b.get("url", "")

                lines.append(f"{i}. 《{title}》")
                lines.append(f"   作者: {author}  格式: {fmt}  大小: {size}  语言: {lang}")
                lines.append(f"   🔗 {url}")
            lines.append("")

        lines.append("💡 点击链接前往站点，登录后下载")
        lines.append("⚠️ 请遵守当地版权法规")
        return "\n".join(lines)


# ------------------------------------------------------------------ #
#  CLI
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(description="图书猎手 v2 — 搜索电子书元数据")
    parser.add_argument("query", nargs="?", default="", help="搜索关键词（书名/作者/关键词）")
    parser.add_argument("--format", "-f", dest="fmt",
                        choices=["epub", "pdf", "mobi", "azw3"],
                        help="格式筛选")
    parser.add_argument("--lang", "-l", choices=["zh", "en"],
                        help="语言筛选 (zh=中文, en=英文)")
    parser.add_argument("--author", "-a", help="作者筛选")
    parser.add_argument("--isbn", "-i", help="ISBN 精确搜索（优先）")
    parser.add_argument("--limit", "-n", type=int, default=10,
                        help="每来源结果数（默认10，最多20）")

    args = parser.parse_args()

    if not args.query and not args.isbn:
        parser.print_help()
        sys.exit(1)

    limit = min(max(args.limit, 1), 20)
    query = args.query or (f"ISBN {args.isbn}" if args.isbn else "")

    hunter = BookHunter()
    results = hunter.search(
        query=query,
        format_filter=args.fmt,
        lang_filter=args.lang,
        author_filter=args.author,
        isbn=args.isbn,
        limit=limit,
    )
    print(hunter.format_output(results))


if __name__ == "__main__":
    main()
