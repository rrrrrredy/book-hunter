#!/usr/bin/env python3
"""
Anna's Archive 搜索模块 v2
- 全量走上游代理
- 直连失败改用 Jina Reader 绕过反爬
- 支持 ISBN 精确搜索
- 支持多备用域名
"""

import requests
import json
import re
import os
import sys
from typing import List, Dict, Optional
from urllib.parse import quote

PROXY = {}
_proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("https_proxy")
if _proxy_url:
    PROXY = {"http": _proxy_url, "https": _proxy_url}

ANNA_MIRRORS = [
    "https://annas-archive.org",
    "https://annas-archive.gs",
    "https://annas-archive.se",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class AnnaSearcher:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.working_mirror: Optional[str] = None

    def _find_mirror(self) -> Optional[str]:
        for mirror in ANNA_MIRRORS:
            try:
                r = self.session.get(mirror, proxies=PROXY, timeout=8)
                if r.status_code < 500:
                    self.working_mirror = mirror
                    return mirror
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------ #
    #  搜索入口
    # ------------------------------------------------------------------ #

    def search(self, query: str, limit: int = 10,
               isbn: Optional[str] = None) -> List[Dict]:
        """搜索图书，支持 ISBN 精确搜索"""
        if isbn:
            q_param = f"isbn:{isbn}"
        else:
            q_param = query

        mirror = self.working_mirror or self._find_mirror()
        if not mirror:
            print("[⚠️ Anna's Archive] 所有镜像不可达，尝试 Jina Reader", file=sys.stderr)
            return self._search_via_jina(q_param, limit)

        # 方案1: 直连（带代理）
        try:
            url = f"{mirror}/search?q={quote(q_param)}&content=book"
            resp = self.session.get(url, proxies=PROXY, timeout=15)
            if resp.status_code == 200:
                results = self._parse_html(resp.text, mirror, limit)
                if results:
                    return results
            print(f"[⚠️ Anna's Archive] HTTP {resp.status_code}，降级 Jina", file=sys.stderr)
        except Exception as e:
            print(f"[⚠️ Anna's Archive] 请求失败: {e}，降级 Jina", file=sys.stderr)

        # 方案2: Jina Reader 绕过反爬
        return self._search_via_jina(q_param, limit, mirror)

    # ------------------------------------------------------------------ #
    #  Jina Reader 降级
    # ------------------------------------------------------------------ #

    def _search_via_jina(self, query: str, limit: int,
                          mirror: Optional[str] = None) -> List[Dict]:
        base = mirror or ANNA_MIRRORS[0]
        jina_url = f"https://r.jina.ai/{base}/search?q={quote(query)}&content=book"
        try:
            resp = self.session.get(jina_url, proxies=PROXY, timeout=20,
                                    headers={"Accept": "text/markdown"})
            if resp.status_code == 200 and resp.text.strip():
                return self._parse_jina_markdown(resp.text, base, limit)
            print(f"[⚠️ Anna's Archive/Jina] HTTP {resp.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"[⚠️ Anna's Archive/Jina] 失败: {e}", file=sys.stderr)
        return []

    # ------------------------------------------------------------------ #
    #  HTML 解析（精确定位书目 div）
    # ------------------------------------------------------------------ #

    def _parse_html(self, html: str, mirror: str, limit: int) -> List[Dict]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # 精确查找含 /md5/ 链接的条目
        for a in soup.find_all("a", href=re.compile(r"/md5/[a-f0-9]{32}"))[:limit]:
            try:
                md5_m = re.search(r"/md5/([a-f0-9]{32})", a["href"])
                if not md5_m:
                    continue
                md5 = md5_m.group(1)

                # 书名：a 自身文字或 h3 子元素
                h3 = a.find("h3")
                title = h3.get_text(strip=True) if h3 else a.get_text(strip=True)
                if not title or len(title) < 2:
                    continue

                # 从 a 的兄弟/父容器提取元数据
                container = a.find_parent("div") or a
                text_blob = container.get_text(" ", strip=True)

                # 作者（常在"· 作者名 ·"或"by 作者"格式）
                author = "Unknown"
                auth_m = re.search(
                    r"(?:by\s+|·\s*)([A-Z][\w\s,\.]+?)(?:\s*[·,]|\s{2}|$)",
                    text_blob)
                if auth_m:
                    author = auth_m.group(1).strip()[:40]

                fmt_m = re.search(r"\b(EPUB|PDF|MOBI|AZW3|DJVU|FB2)\b",
                                  text_blob, re.I)
                size_m = re.search(r"(\d+\.?\d*\s*(?:MB|KB|GB))", text_blob, re.I)
                lang_m = re.search(
                    r"\b(English|Chinese|中文|Deutsch|Français|Japanese|Russian|Spanish)\b",
                    text_blob, re.I)

                results.append({
                    "source": "Anna",
                    "title": title,
                    "author": author,
                    "format": fmt_m.group(1).upper() if fmt_m else "Unknown",
                    "size": size_m.group(1) if size_m else "Unknown",
                    "language": lang_m.group(1) if lang_m else "Unknown",
                    "url": f"{mirror}/md5/{md5}",
                })
            except Exception:
                continue

        return results

    def _parse_jina_markdown(self, md: str, mirror: str, limit: int) -> List[Dict]:
        """解析 Jina 返回的 Markdown 内容"""
        results = []
        # 找 md5 链接
        for m in re.finditer(r"\[([^\]]+)\]\([^)]*md5/([a-f0-9]{32})[^)]*\)", md):
            if len(results) >= limit:
                break
            title = m.group(1).strip()
            md5 = m.group(2)
            if not title or title.startswith("http"):
                continue
            results.append({
                "source": "Anna",
                "title": title,
                "author": "Unknown",
                "format": "Unknown",
                "size": "Unknown",
                "language": "Unknown",
                "url": f"{mirror}/md5/{md5}",
            })
        return results

    # ------------------------------------------------------------------ #
    #  带筛选的搜索
    # ------------------------------------------------------------------ #

    def search_with_filters(self, query: str, format_filter: Optional[str] = None,
                            lang_filter: Optional[str] = None,
                            author_filter: Optional[str] = None,
                            isbn: Optional[str] = None,
                            limit: int = 10) -> List[Dict]:
        fetch_limit = min(limit * 3, 30)
        results = self.search(query, limit=fetch_limit, isbn=isbn)

        if format_filter:
            results = [r for r in results if r["format"].lower() == format_filter.lower()]
        if lang_filter:
            kws = {"zh": ["chinese", "中文", "汉"], "en": ["english", "英"]}.get(
                lang_filter.lower(), [lang_filter.lower()])
            results = [r for r in results if any(k in r["language"].lower() for k in kws)]
        if author_filter:
            results = [r for r in results if author_filter.lower() in r["author"].lower()]

        return results[:limit]
