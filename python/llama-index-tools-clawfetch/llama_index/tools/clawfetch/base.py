"""ClawFetch tool spec — pay-per-call web intelligence for AI agents (x402, USDC on Base)."""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional

from clawfetch import ClawFetch
from llama_index.core.tools.tool_spec.base import BaseToolSpec

DEFAULT_MAX_CHARS = 10_000


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated {len(text) - max_chars} chars]"


def _page(result: dict) -> str:
    return f"# {result.get('title') or ''}\nURL: {result.get('url') or ''}\n\n{result.get('text') or ''}"


class ClawFetchToolSpec(BaseToolSpec):
    """ClawFetch web tools. Each call is paid in USDC on Base via x402.

    Args:
        private_key: Base wallet private key holding USDC. Defaults to the
            ``CLAWFETCH_PRIVATE_KEY`` environment variable.
        client: An existing ``clawfetch.ClawFetch`` client (overrides private_key).
        max_chars: Maximum characters returned by each tool call.
    """

    spec_functions = [
        "fetch",
        "render",
        "extract",
        "research",
        "parse",
        "company",
        "domains_check",
        "domains_suggest",
    ]

    def __init__(
        self,
        private_key: Optional[str] = None,
        client: Optional[ClawFetch] = None,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> None:
        if client is None:
            key = private_key or os.environ.get("CLAWFETCH_PRIVATE_KEY")
            if not key:
                raise ValueError("Pass private_key=..., set CLAWFETCH_PRIVATE_KEY, or pass client=ClawFetch(...).")
            client = ClawFetch(private_key=key)
        self.client = client
        self.max_chars = max_chars

    def _json(self, result: Any) -> str:
        return _truncate(json.dumps(result, ensure_ascii=False), self.max_chars)

    def fetch(self, url: str) -> str:
        """Fetch a web page and return its title, URL and readable text. No JavaScript execution; use render for JS-heavy pages. Costs $0.001 USDC per call.

        Args:
            url: Absolute http(s) URL of the page to fetch.
        """
        return _truncate(_page(self.client.fetch(url, max_chars=self.max_chars)), self.max_chars)

    def render(self, url: str, wait_for: Optional[str] = None) -> str:
        """Render a JavaScript-heavy page in a headless browser and return its visible text. Use when fetch returns empty or incomplete content. Costs $0.005 USDC per call.

        Args:
            url: Absolute http(s) URL of the page.
            wait_for: Optional CSS selector to wait for before reading the page.
        """
        result = self.client.render(url, max_chars=self.max_chars, wait_for=wait_for)
        return _truncate(_page(result), self.max_chars)

    def extract(self, url: str, type: Optional[str] = None) -> str:
        """Extract typed structured data (JSON) from a page on a supported site: twitter, coingecko, github, news, npm, pypi, crates, hackernews, youtube, wikipedia, producthunt, imdb, amazon, crunchbase, sec-edgar, zillow, redfin. Costs $0.008 USDC per call.

        Args:
            url: URL on a supported site.
            type: Optional extractor name from the list above; auto-detected from the URL when omitted.
        """
        return self._json(self.client.extract(url, type=type))

    def research(self, query: str, max_results: Optional[int] = None) -> str:
        """Search the web for a query and return the text of the top sources with their URLs (for citations). Costs $0.02 USDC per call.

        Args:
            query: Research question or topic.
            max_results: Number of sources to read (1-10, default 5).
        """
        return self._json(self.client.research(query, max_results=max_results))

    def parse(self, url: str, format: Optional[str] = None) -> str:
        """Convert an office document or PDF at a URL (docx, pptx, xlsx, pdf, odt, rtf, epub, csv, ...) to Markdown. No OCR: scanned PDFs fail. Costs $0.005 USDC per call.

        Args:
            url: Absolute http(s) URL of the document.
            format: Optional format override (doc, docx, odt, pdf, ppt, pptx, rtf, epub, xlsx, ods, odp, csv).
        """
        return _truncate(self.client.parse(url, format=format).get("markdown") or "", self.max_chars)

    def company(self, domain: str) -> str:
        """Company profile from a domain: name, description, logo, social profiles, contact emails and phones, address, tech stack and key pages (about, careers, pricing, docs). Deterministic, no LLM. Costs $0.02 USDC per call.

        Args:
            domain: Company domain (e.g. "stripe.com") or any URL on the site.
        """
        return self._json(self.client.company(domain))

    def domains_check(self, domains: List[str]) -> str:
        """Check whether specific domain names are available to register. Returns JSON with a result per domain (available true/false, or null with an error). Costs $0.003 USDC per call.

        Args:
            domains: Fully qualified domain names, e.g. ["acme.ai", "acme.com"] (max 20).
        """
        return self._json(self.client.domains_check(domains))

    def domains_suggest(
        self,
        keywords: List[str],
        tlds: Optional[List[str]] = None,
        max_check: Optional[int] = None,
    ) -> str:
        """Generate domain names from keywords and check which are available. Returns JSON with the available domains and every checked result. Costs $0.003 USDC per call.

        Args:
            keywords: Keywords to combine into domain names, e.g. ["agent", "grid"].
            tlds: TLDs to try without dots, e.g. ["com", "ai"]. Default: com, ai, io.
            max_check: How many generated names to check (1-50, default 30).
        """
        return self._json(self.client.domains_suggest(keywords, tlds=tlds, max_check=max_check))
