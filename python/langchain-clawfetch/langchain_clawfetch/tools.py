"""LangChain tools for the ClawFetch web intelligence API (x402, USDC on Base)."""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional, Tuple, Type

from clawfetch import AsyncClawFetch, ClawFetch, ClawFetchError
from langchain_core.tools import BaseTool, BaseToolkit, ToolException
from pydantic import BaseModel, ConfigDict, Field, SecretStr

DEFAULT_MAX_CHARS = 10_000

EXTRACT_TYPES = (
    "twitter, coingecko, github, news, npm, pypi, crates, hackernews, youtube, "
    "wikipedia, producthunt, imdb, amazon, crunchbase, sec-edgar, zillow, redfin"
)


def _make_clients(private_key: Optional[SecretStr]) -> Tuple[ClawFetch, AsyncClawFetch]:
    key = private_key.get_secret_value() if private_key else os.environ.get("CLAWFETCH_PRIVATE_KEY")
    if not key:
        raise ValueError("Pass private_key=..., set CLAWFETCH_PRIVATE_KEY, or pass client=ClawFetch(...).")
    return ClawFetch(private_key=key), AsyncClawFetch(private_key=key)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...[truncated {len(text) - max_chars} chars]"


def _json(result: Any) -> str:
    return json.dumps(result, ensure_ascii=False)


def _page(result: dict) -> str:
    """Format a /fetch or /render result as markdown-ish text."""
    title = result.get("title") or ""
    url = result.get("url") or ""
    text = result.get("text") or ""
    return f"# {title}\nURL: {url}\n\n{text}"


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
    """Shared client wiring, error mapping and output formatting."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    private_key: Optional[SecretStr] = Field(default=None, exclude=True)
    client: Optional[ClawFetch] = Field(default=None, exclude=True)
    async_client: Optional[AsyncClawFetch] = Field(default=None, exclude=True)
    max_chars: int = DEFAULT_MAX_CHARS

    def model_post_init(self, __context: Any) -> None:
        if self.client is None and self.async_client is None:
            self.client, self.async_client = _make_clients(self.private_key)

    def _invoke(self, client: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def _format(self, result: Any) -> str:
        return _json(result)

    def _run(self, run_manager: Any = None, **kwargs: Any) -> str:
        if self.client is None:
            raise ToolException(f"{self.name}: no sync ClawFetch client configured; use the async API.")
        try:
            result = self._invoke(self.client, **kwargs)
        except ClawFetchError as exc:
            raise ToolException(f"{self.name} failed ({type(exc).__name__}): {exc}") from exc
        return _truncate(self._format(result), self.max_chars)

    async def _arun(self, run_manager: Any = None, **kwargs: Any) -> str:
        if self.async_client is None:
            return await super()._arun(**kwargs)
        try:
            result = await self._invoke(self.async_client, **kwargs)
        except ClawFetchError as exc:
            raise ToolException(f"{self.name} failed ({type(exc).__name__}): {exc}") from exc
        return _truncate(self._format(result), self.max_chars)


class ClawFetchFetch(_ClawFetchTool):
    name: str = "clawfetch_fetch"
    description: str = (
        "Fetch a web page and return its readable text with title and URL. "
        "Fast, no JavaScript execution; use clawfetch_render for JS-heavy pages. "
        "Costs $0.001 USDC per call."
    )
    args_schema: Type[BaseModel] = FetchInput

    def _invoke(self, client: Any, url: str) -> Any:
        return client.fetch(url, max_chars=self.max_chars)

    def _format(self, result: Any) -> str:
        return _page(result)


class ClawFetchRender(_ClawFetchTool):
    name: str = "clawfetch_render"
    description: str = (
        "Render a JavaScript-heavy page in a headless browser and return its visible text. "
        "Use when clawfetch_fetch returns empty or incomplete content. Costs $0.005 USDC per call."
    )
    args_schema: Type[BaseModel] = RenderInput

    def _invoke(self, client: Any, url: str, wait_for: Optional[str] = None) -> Any:
        return client.render(url, max_chars=self.max_chars, wait_for=wait_for)

    def _format(self, result: Any) -> str:
        return _page(result)


class ClawFetchExtract(_ClawFetchTool):
    name: str = "clawfetch_extract"
    description: str = (
        "Extract typed structured data (JSON) from a page on a supported site: "
        f"{EXTRACT_TYPES}. Costs $0.008 USDC per call."
    )
    args_schema: Type[BaseModel] = ExtractInput

    def _invoke(self, client: Any, url: str, type: Optional[str] = None) -> Any:
        return client.extract(url, type=type)


class ClawFetchResearch(_ClawFetchTool):
    name: str = "clawfetch_research"
    description: str = (
        "Search the web for a query and return the text of the top sources with their URLs "
        "(for citations). Costs $0.02 USDC per call."
    )
    args_schema: Type[BaseModel] = ResearchInput

    def _invoke(self, client: Any, query: str, max_results: Optional[int] = None) -> Any:
        return client.research(query, max_results=max_results)


class ClawFetchParse(_ClawFetchTool):
    name: str = "clawfetch_parse"
    description: str = (
        "Convert an office document or PDF at a URL (docx, pptx, xlsx, pdf, odt, rtf, epub, csv, ...) "
        "to Markdown. No OCR: scanned PDFs fail. Costs $0.005 USDC per call."
    )
    args_schema: Type[BaseModel] = ParseInput

    def _invoke(self, client: Any, url: str, format: Optional[str] = None) -> Any:
        return client.parse(url, format=format)

    def _format(self, result: Any) -> str:
        return result.get("markdown") or ""


class ClawFetchDomainsCheck(_ClawFetchTool):
    name: str = "clawfetch_domains_check"
    description: str = (
        "Check whether specific domain names are available to register. Returns JSON with a "
        "result per domain (available true/false, or null with an error). Costs $0.003 USDC per call."
    )
    args_schema: Type[BaseModel] = DomainsCheckInput

    def _invoke(self, client: Any, domains: List[str]) -> Any:
        return client.domains_check(domains)


class ClawFetchDomainsSuggest(_ClawFetchTool):
    name: str = "clawfetch_domains_suggest"
    description: str = (
        "Generate domain names from keywords and check which are available. Returns JSON with the "
        "list of available domains and every checked result. Costs $0.003 USDC per call."
    )
    args_schema: Type[BaseModel] = DomainsSuggestInput

    def _invoke(
        self,
        client: Any,
        keywords: List[str],
        tlds: Optional[List[str]] = None,
        max_check: Optional[int] = None,
    ) -> Any:
        return client.domains_suggest(keywords, tlds=tlds, max_check=max_check)


TOOL_CLASSES = (
    ClawFetchFetch,
    ClawFetchRender,
    ClawFetchExtract,
    ClawFetchResearch,
    ClawFetchParse,
    ClawFetchDomainsCheck,
    ClawFetchDomainsSuggest,
)


class ClawFetchToolkit(BaseToolkit):
    """All ClawFetch tools sharing one sync and one async client.

    Build from ``private_key=`` (or the ``CLAWFETCH_PRIVATE_KEY`` env var), or
    pass existing ``client=`` / ``async_client=`` instances.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    private_key: Optional[SecretStr] = Field(default=None, exclude=True)
    client: Optional[ClawFetch] = Field(default=None, exclude=True)
    async_client: Optional[AsyncClawFetch] = Field(default=None, exclude=True)
    max_chars: int = DEFAULT_MAX_CHARS

    def model_post_init(self, __context: Any) -> None:
        if self.client is None and self.async_client is None:
            self.client, self.async_client = _make_clients(self.private_key)

    def get_tools(self) -> List[BaseTool]:
        return [
            cls(client=self.client, async_client=self.async_client, max_chars=self.max_chars)
            for cls in TOOL_CLASSES
        ]
