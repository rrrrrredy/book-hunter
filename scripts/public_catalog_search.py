#!/usr/bin/env python3
"""
Public catalog metadata fallback.

Uses Internet Archive's public advancedsearch API for book metadata/source pages.
This module returns catalog records only; it does not fetch or expose downloadable
files.
"""

import os
import re
from typing import Dict, List, Optional

import requests


def _env_timeout(name: str, default: float) -> float:
    try:
        return max(1.0, float(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


CATALOG_TIMEOUT = _env_timeout("BOOK_HUNTER_CATALOG_TIMEOUT", 8)

HEADERS = {
    "User-Agent": "book-hunter/1.0 metadata search (contact: luosongred@gmail.com)",
    "Accept": "application/json",
}


class PublicCatalogSearcher:
    """Search public catalog metadata pages."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last_errors: list[str] = []

    def search_with_filters(
        self,
        query: str,
        format_filter: Optional[str] = None,
        lang_filter: Optional[str] = None,
        author_filter: Optional[str] = None,
        isbn: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        self.last_errors = []
        if format_filter:
            self.last_errors.append(
                f"public catalog skipped because it cannot verify {format_filter.upper()} availability"
            )
            return []

        raw = self.search(isbn or query, limit=min(limit * 2, 20), isbn=isbn)

        if lang_filter:
            kws = {"zh": ["chi", "中文", "chinese", "zh"], "en": ["eng", "english", "en"]}.get(
                lang_filter.lower(), [lang_filter.lower()]
            )
            raw = [r for r in raw if any(k in r["language"].lower() for k in kws)]
        if author_filter:
            raw = [r for r in raw if author_filter.lower() in r["author"].lower()]

        return raw[:limit]

    def search(self, query: str, limit: int = 10, isbn: Optional[str] = None) -> List[Dict]:
        try:
            q = self._build_query(query, isbn)
            resp = self.session.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": q,
                    "fl[]": ["title", "creator", "identifier", "language", "year"],
                    "rows": limit,
                    "output": "json",
                },
                timeout=CATALOG_TIMEOUT,
            )
            if resp.status_code != 200:
                self.last_errors.append(f"Internet Archive returned HTTP {resp.status_code}")
                return []
            docs = resp.json().get("response", {}).get("docs", [])
        except Exception as e:
            self.last_errors.append(f"Internet Archive request failed: {e}")
            return []

        results: List[Dict] = []
        for doc in docs:
            item = self._record_to_result(doc)
            if not item:
                continue
            if not self._looks_relevant(query, item["title"], isbn=isbn):
                continue
            results.append(item)
        if not results:
            self.last_errors.append("Internet Archive returned no relevant catalog records")
        return results

    def _build_query(self, query: str, isbn: Optional[str]) -> str:
        cleaned = (isbn or query).strip()
        if isbn:
            return f'(isbn:"{cleaned}" OR identifier:"{cleaned}") AND mediatype:texts'
        return f'title:("{cleaned}") AND mediatype:texts'

    def _record_to_result(self, doc: Dict) -> Optional[Dict]:
        identifier = str(doc.get("identifier") or "").strip()
        title = self._first(doc.get("title"))
        if not identifier or not title:
            return None

        author = self._first(doc.get("creator")) or "Unknown"
        language = self._first(doc.get("language")) or "Unknown"
        year = self._first(doc.get("year"))
        if year and language != "Unknown":
            language = f"{language} / {year}"
        elif year:
            language = str(year)

        return {
            "source": "Public Catalog",
            "title": title,
            "author": author,
            "format": "Metadata",
            "size": "N/A",
            "language": language,
            "url": f"https://archive.org/details/{identifier}",
        }

    def _looks_relevant(self, query: str, title: str, isbn: Optional[str] = None) -> bool:
        if isbn:
            return True
        q = self._normalize(query)
        t = self._normalize(title)
        if not q or not t:
            return False
        if q == t:
            return True

        # Avoid noisy CJK catalog matches such as fan fiction titles containing
        # the requested book name. Exact title is required for short CJK queries.
        if re.search(r"[\u4e00-\u9fff]", query):
            return False

        q_tokens = {tok for tok in q.split() if len(tok) > 1}
        t_tokens = set(t.split())
        if not q_tokens:
            return False
        return len(q_tokens & t_tokens) / len(q_tokens) >= 0.75

    @staticmethod
    def _first(value) -> str:
        if isinstance(value, list):
            return str(value[0]).strip() if value else ""
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _normalize(value: str) -> str:
        value = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", value.lower())
        return re.sub(r"\s+", " ", value).strip()
