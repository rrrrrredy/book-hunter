#!/usr/bin/env python3
"""
Z-Library 搜索模块 v2
- 全量走上游代理
- 反爬失败自动降级 Camoufox
- 镜像探测结果缓存到 ~/.book-hunter/mirrors.json
"""

import requests
import json
import re
import os
import sys
import time
from typing import List, Dict, Optional
from urllib.parse import quote

PROXY = {}
_proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("https_proxy")
if _proxy_url:
    PROXY = {"http": _proxy_url, "https": _proxy_url}
CACHE_FILE = os.path.expanduser("~/.book-hunter/mirrors.json")
CACHE_TTL = 3600 * 6  # 6小时

ZLIB_MIRRORS = [
    "https://z-library.sk",
    "https://z-library.se",
    "https://z-lib.id",
    "https://z-lib.fm",
    "https://1lib.dev",
    "https://lib-boc.net",
    "https://z-library.rs",
    "https://z-library.gs",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class ZLibSearcher:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.working_mirror: Optional[str] = self._load_cached_mirror()

    # ------------------------------------------------------------------ #
    #  镜像缓存
    # ------------------------------------------------------------------ #

    def _load_cached_mirror(self) -> Optional[str]:
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE) as f:
                    data = json.load(f)
                if time.time() - data.get("ts", 0) < CACHE_TTL:
                    return data.get("mirror")
        except Exception:
            pass
        return None

    def _save_mirror(self, mirror: str):
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump({"mirror": mirror, "ts": time.time()}, f)
        except Exception:
            pass

    def _find_working_mirror(self) -> Optional[str]:
        for mirror in ZLIB_MIRRORS:
            try:
                resp = self.session.get(mirror, proxies=PROXY, timeout=8,
                                        allow_redirects=True)
                if resp.status_code in (200, 301, 302):
                    self._save_mirror(mirror)
                    self.working_mirror = mirror
                    return mirror
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------ #
    #  搜索入口
    # ------------------------------------------------------------------ #

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        mirror = self.working_mirror or self._find_working_mirror()
        if not mirror:
            print("[⚠️ Z-Library] 无可用镜像，降级到 Camoufox", file=sys.stderr)
            return self._search_via_camoufox(query, limit)

        try:
            url = f"{mirror}/s/{quote(query)}"
            resp = self.session.get(url, proxies=PROXY, timeout=15)
            if resp.status_code == 200:
                results = self._parse_html(resp.text, mirror, limit)
                if results:
                    return results
            print(f"[⚠️ Z-Library] HTTP {resp.status_code}，降级 Camoufox", file=sys.stderr)
        except Exception as e:
            print(f"[⚠️ Z-Library] requests 失败: {e}，降级 Camoufox", file=sys.stderr)

        return self._search_via_camoufox(query, limit)

    # ------------------------------------------------------------------ #
    #  Camoufox 降级
    # ------------------------------------------------------------------ #

    def _search_via_camoufox(self, query: str, limit: int) -> List[Dict]:
        mirror = self.working_mirror or "https://z-library.sk"
        try:
            from camoufox.sync_api import Camoufox
            url = f"{mirror}/s/{quote(query)}"
            with Camoufox(headless=True,
                          proxy={"server": os.environ.get("HTTP_PROXY", "")} if os.environ.get("HTTP_PROXY") else {}) as browser:
                page = browser.new_page()
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                html = page.content()
            results = self._parse_html(html, mirror, limit)
            if results:
                return results
            print("[⚠️ Z-Library] Camoufox 解析无结果", file=sys.stderr)
        except Exception as e:
            print(f"[⚠️ Z-Library] Camoufox 失败: {e}", file=sys.stderr)
        return []

    # ------------------------------------------------------------------ #
    #  HTML 解析（两套选择器，互为备用）
    # ------------------------------------------------------------------ #

    def _parse_html(self, html: str, mirror: str, limit: int) -> List[Dict]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        results = self._parse_v1(soup, mirror, limit)
        if not results:
            results = self._parse_v2(soup, mirror, limit)
        return results

    def _parse_v1(self, soup, mirror: str, limit: int) -> List[Dict]:
        """class=resItemBox 方式（经典版）"""
        results = []
        for item in soup.find_all("div", class_="resItemBox")[:limit]:
            try:
                title_el = item.find("h3", itemprop="name") or item.find("h3")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                author_el = item.find("a", class_="author")
                author = author_el.get_text(strip=True) if author_el else "Unknown"

                link_el = item.find("a", href=re.compile(r"/book/"))
                book_url = ""
                if link_el:
                    m = re.search(r"/book/(\d+)", link_el.get("href", ""))
                    if m:
                        book_url = f"{mirror}/book/{m.group(1)}"

                fmt, size, lang = "Unknown", "Unknown", "Unknown"
                for prop in item.find_all("div", class_=re.compile(r"property")):
                    text = prop.get_text(strip=True)
                    m_fmt = re.search(r"\b(EPUB|PDF|MOBI|AZW3|DJVU|FB2)\b", text, re.I)
                    m_size = re.search(r"(\d+\.?\d*\s*(?:MB|KB|GB))", text, re.I)
                    if m_fmt:
                        fmt = m_fmt.group(1).upper()
                    if m_size:
                        size = m_size.group(1)
                    if re.search(r"(English|Chinese|中文|Deutsch|Français)", text, re.I):
                        lang = text[:20]

                if book_url:
                    results.append({"source": "Z-Lib", "title": title,
                                    "author": author, "format": fmt,
                                    "size": size, "language": lang,
                                    "url": book_url})
            except Exception:
                continue
        return results

    def _parse_v2(self, soup, mirror: str, limit: int) -> List[Dict]:
        """通用 h3+链接 方式（站点改版备用）"""
        results = []
        for a in soup.find_all("a", href=re.compile(r"/book/\d+"))[:limit]:
            try:
                title = a.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                m = re.search(r"/book/(\d+)", a["href"])
                if not m:
                    continue
                book_url = f"{mirror}/book/{m.group(1)}"
                # 从父元素提取格式信息
                parent_text = a.find_parent().get_text(" ", strip=True) if a.find_parent() else ""
                fmt_m = re.search(r"\b(EPUB|PDF|MOBI|AZW3)\b", parent_text, re.I)
                results.append({"source": "Z-Lib", "title": title,
                                "author": "Unknown", "format": fmt_m.group(1).upper() if fmt_m else "Unknown",
                                "size": "Unknown", "language": "Unknown",
                                "url": book_url})
            except Exception:
                continue
        return results

    # ------------------------------------------------------------------ #
    #  带筛选的搜索
    # ------------------------------------------------------------------ #

    def search_with_filters(self, query: str, format_filter: Optional[str] = None,
                            lang_filter: Optional[str] = None,
                            author_filter: Optional[str] = None,
                            limit: int = 10) -> List[Dict]:
        fetch_limit = min(limit * 3, 30)
        results = self.search(query, limit=fetch_limit)

        if format_filter:
            results = [r for r in results if r["format"].lower() == format_filter.lower()]
        if lang_filter:
            kws = {"zh": ["chinese", "中文", "汉"], "en": ["english", "英"]}.get(
                lang_filter.lower(), [lang_filter.lower()])
            results = [r for r in results if any(k in r["language"].lower() for k in kws)]
        if author_filter:
            results = [r for r in results if author_filter.lower() in r["author"].lower()]

        return results[:limit]
