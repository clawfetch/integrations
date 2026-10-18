"""CrewAI tools for the ClawFetch web intelligence API (x402, USDC on Base)."""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional, Type

from clawfetch import ClawFetch
from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MAX_CHARS = 10_000

EXTRACT_TYPES = (
    "twitter, coingecko, github, news, npm, pypi, crates, hackernews, youtube, "
    "wikipedia, producthunt, imdb, amazon, crunchbase, sec-edgar, zillow, redfin"
)


def _make_client(private_key: Optional[str]) -> ClawFetch:
    key = private_key or os.environ.get("CLAWFETCH_PRIVATE_KEY")
    if not key:
        raise ValueError("Pass private_key=..., set CLAWFETCH_PRIVATE_KEY, or pass client=ClawFetch(...).")
    return ClawFetch(private_key=key)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated {len(text) - max_chars} chars]"


def _page(result: dict) -> str:
    return f"# {result.get('title') or ''}\nURL: {result.get('url') or ''}\n\n{result.get('text') or ''}"


# ─── Input schemas ────────────────────────────────────────────────


class FetchInput(BaseModel):
    url: str = Field(description="Absolute http(s) URL of the page to fetch.")


class RenderInput(BaseModel):
    url: str = Field(description="Absolute http(s) URL of the JavaScript-heavy page.")
    wait_for: Optional[str] = Field(
        default=None, description="Optional CSS selector to wait for before reading the page."
    )


class ExtractInput(BaseModel):
    url: str = Field(description="URL on a supported site (e.g. a GitHub repo or CoinGecko coin page).")
    type: Optional[str] = Field(
        default=None,
        description=f"Optional extractor name; auto-detected from the URL when omitted. One of: {EXTRACT_TYPES}.",
    )


class ResearchInput(BaseModel):
    query: str = Field(description="Research question or topic.")
    max_results: Optional[int] = Field(
        default=None, ge=1, le=10, description="Number of sources to read (1-10, default 5)."
    )


class ParseInput(BaseModel):
    url: str = Field(description="Absolute http(s) URL of an office document or PDF.")
    format: Optional[str] = Field(
        default=None,
        description="Optional format override (doc, docx, odt, pdf, ppt, pptx, rtf, epub, xlsx, ods, odp, csv).",
    )


class DomainsCheckInput(BaseModel):
    domains: List[str] = Field(description="Fully qualified domain names to check, e.g. ['acme.ai', 'acme.com'] (max 20).")


class DomainsSuggestInput(BaseModel):
    keywords: List[str] = Field(description="Keywords to combine into domain names, e.g. ['agent', 'grid'].")
    tlds: Optional[List[str]] = Field(
        default=None, description="TLDs to try without dots, e.g. ['com', 'ai']. Default: com, ai, io."
    )
    max_check: Optional[int] = Field(
        default=None, ge=1, le=50, description="How many generated names to check for availability (1-50, default 30)."
    )


# ─── Tools ────────────────────────────────────────────────────────


class _ClawFetchTool(BaseTool):
    """Shared client wiring and output formatting.

    Construct with ``private_key=`` (or the ``CLAWFETCH_PRIVATE_KEY`` env var)
    or an existing ``client=ClawFetch(...)``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    private_key: Optional[str] = Field(default=None, exclude=True, repr=False)
    client: Optional[ClawFetch] = Field(default=None, exclude=True)
    max_chars: int = DEFAULT_MAX_CHARS

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        if self.client is None:
            self.client = _make_client(self.private_key)

    def _json(self, result: Any) -> str:
        return _truncate(json.dumps(result, ensure_ascii=False), self.max_chars)


class ClawFetchFetchTool(_ClawFetchTool):
    name: str = "clawfetch_fetch"
    description: str = (
        "Fetch a web page and return its readable text with title and URL. "
        "Fast, no JavaScript execution; use clawfetch_render for JS-heavy pages. "
        "Costs $0.001 USDC per call."
    )
    args_schema: Type[BaseModel] = FetchInput

    def _run(self, url: str) -> str:
        return _truncate(_page(self.client.fetch(url, max_chars=self.max_chars)), self.max_chars)


class ClawFetchRenderTool(_ClawFetchTool):
    name: str = "clawfetch_render"
    description: str = (
        "Render a JavaScript-heavy page in a headless browser and return its visible text. "
        "Use when clawfetch_fetch returns empty or incomplete content. Costs $0.005 USDC per call."
    )
    args_schema: Type[BaseModel] = RenderInput

    def _run(self, url: str, wait_for: Optional[str] = None) -> str:
        result = self.client.render(url, max_chars=self.max_chars, wait_for=wait_for)
        return _truncate(_page(result), self.max_chars)


class ClawFetchExtractTool(_ClawFetchTool):
    name: str = "clawfetch_extract"
    description: str = (
        "Extract typed structured data (JSON) from a page on a supported site: "
        f"{EXTRACT_TYPES}. Costs $0.008 USDC per call."
    )
    args_schema: Type[BaseModel] = ExtractInput

    def _run(self, url: str, type: Optional[str] = None) -> str:
        return self._json(self.client.extract(url, type=type))


class ClawFetchResearchTool(_ClawFetchTool):
    name: str = "clawfetch_research"
    description: str = (
        "Search the web for a query and return the text of the top sources with their URLs "
        "(for citations). Costs $0.02 USDC per call."
    )
    args_schema: Type[BaseModel] = ResearchInput

    def _run(self, query: str, max_results: Optional[int] = None) -> str:
        return self._json(self.client.research(query, max_results=max_results))


class ClawFetchParseTool(_ClawFetchTool):
    name: str = "clawfetch_parse"
    description: str = (
        "Convert an office document or PDF at a URL (docx, pptx, xlsx, pdf, odt, rtf, epub, csv, ...) "
        "to Markdown. No OCR: scanned PDFs fail. Costs $0.005 USDC per call."
    )
    args_schema: Type[BaseModel] = ParseInput

    def _run(self, url: str, format: Optional[str] = None) -> str:
        return _truncate(self.client.parse(url, format=format).get("markdown") or "", self.max_chars)


class ClawFetchDomainsCheckTool(_ClawFetchTool):
    name: str = "clawfetch_domains_check"
    description: str = (
        "Check whether specific domain names are available to register. Returns JSON with a "
        "result per domain (available true/false, or null with an error). Costs $0.003 USDC per call."
    )
    args_schema: Type[BaseModel] = DomainsCheckInput

    def _run(self, domains: List[str]) -> str:
        return self._json(self.client.domains_check(domains))


class ClawFetchDomainsSuggestTool(_ClawFetchTool):
    name: str = "clawfetch_domains_suggest"
    description: str = (
        "Generate domain names from keywords and check which are available. Returns JSON with the "
        "list of available domains and every checked result. Costs $0.003 USDC per call."
    )
    args_schema: Type[BaseModel] = DomainsSuggestInput

    def _run(
        self,
        keywords: List[str],
        tlds: Optional[List[str]] = None,
        max_check: Optional[int] = None,
    ) -> str:
        return self._json(self.client.domains_suggest(keywords, tlds=tlds, max_check=max_check))


TOOL_CLASSES = (
    ClawFetchFetchTool,
    ClawFetchRenderTool,
    ClawFetchExtractTool,
    ClawFetchResearchTool,
    ClawFetchParseTool,
    ClawFetchDomainsCheckTool,
    ClawFetchDomainsSuggestTool,
)


def clawfetch_tools(
    private_key: Optional[str] = None,
    client: Optional[ClawFetch] = None,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> List[BaseTool]:
    """Return every ClawFetch tool, sharing one client.

    Args:
        private_key: Base wallet private key holding USDC. Defaults to the
            ``CLAWFETCH_PRIVATE_KEY`` environment variable.
        client: An existing ``clawfetch.ClawFetch`` client (overrides private_key).
        max_chars: Maximum characters returned by each tool call.
    """
    client = client or _make_client(private_key)
    return [cls(client=client, max_chars=max_chars) for cls in TOOL_CLASSES]
