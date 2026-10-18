"""Unit tests — the ClawFetch client is mocked: no network, no payments."""

import json
from unittest.mock import MagicMock

import pytest
from clawfetch import ClawFetch
from crewai.tools import BaseTool

from crewai_clawfetch import (
    ClawFetchDomainsCheckTool,
    ClawFetchDomainsSuggestTool,
    ClawFetchExtractTool,
    ClawFetchFetchTool,
    ClawFetchParseTool,
    ClawFetchRenderTool,
    ClawFetchResearchTool,
    clawfetch_tools,
)

DUMMY_KEY = "0x0000000000000000000000000000000000000000000000000000000000000001"
PAGE = {"url": "https://a.b", "title": "T", "text": "hello"}

# (tool class, tool input, sdk method, expected args, expected kwargs, sdk result, expected output)
CASES = [
    (ClawFetchFetchTool, {"url": "https://a.b"}, "fetch", ("https://a.b",), {"max_chars": 10_000},
     PAGE, "# T\nURL: https://a.b\n\nhello"),
    (ClawFetchRenderTool, {"url": "https://a.b", "wait_for": "#app"}, "render", ("https://a.b",),
     {"max_chars": 10_000, "wait_for": "#app"}, PAGE, "# T\nURL: https://a.b\n\nhello"),
    (ClawFetchExtractTool, {"url": "https://github.com/a/b"}, "extract", ("https://github.com/a/b",),
     {"type": None}, {"type": "github", "stars": 1}, json.dumps({"type": "github", "stars": 1})),
    (ClawFetchResearchTool, {"query": "x402", "max_results": 3}, "research", ("x402",), {"max_results": 3},
     {"query": "x402", "sources": 0, "results": []}, json.dumps({"query": "x402", "sources": 0, "results": []})),
    (ClawFetchParseTool, {"url": "https://a.b/x.docx"}, "parse", ("https://a.b/x.docx",), {"format": None},
     {"markdown": "# Doc", "format": "docx", "chars": 5}, "# Doc"),
    (ClawFetchDomainsCheckTool, {"domains": ["a.ai"]}, "domains_check", (["a.ai"],), {},
     {"checked": 1, "results": [{"domain": "a.ai", "available": True}]},
     json.dumps({"checked": 1, "results": [{"domain": "a.ai", "available": True}]})),
    (ClawFetchDomainsSuggestTool, {"keywords": ["agent"], "tlds": ["ai"], "max_check": 5}, "domains_suggest",
     (["agent"],), {"tlds": ["ai"], "max_check": 5},
     {"keywords": ["agent"], "available": ["agent.ai"]}, json.dumps({"keywords": ["agent"], "available": ["agent.ai"]})),
]


@pytest.mark.parametrize("cls,tool_input,method,args,kwargs,result,expected", CASES)
def test_tool_run_calls_sdk_and_formats(cls, tool_input, method, args, kwargs, result, expected):
    client = MagicMock(spec=ClawFetch)
    getattr(client, method).return_value = result
    tool = cls(client=client)
    assert tool.run(**tool_input) == expected
    getattr(client, method).assert_called_once_with(*args, **kwargs)


def test_args_schema_validation_rejects_bad_input():
    tool = ClawFetchResearchTool(client=MagicMock(spec=ClawFetch))
    with pytest.raises(Exception):
        tool.run(query="x", max_results=99)


def test_output_truncated_to_max_chars():
    client = MagicMock(spec=ClawFetch)
    client.parse.return_value = {"markdown": "x" * 50}
    out = ClawFetchParseTool(client=client, max_chars=10).run(url="https://a.b/x.pdf")
    assert out == "x" * 10 + "\n...[truncated 40 chars]"


def test_clawfetch_tools_shares_client_and_metadata():
    client = MagicMock(spec=ClawFetch)
    tools = clawfetch_tools(client=client, max_chars=500)
    assert [t.name for t in tools] == [
        "clawfetch_fetch", "clawfetch_render", "clawfetch_extract", "clawfetch_research",
        "clawfetch_parse", "clawfetch_domains_check", "clawfetch_domains_suggest",
    ]
    for t in tools:
        assert isinstance(t, BaseTool)
        assert t.client is client and t.max_chars == 500
        assert "$0." in t.description and "USDC" in t.description


def test_clawfetch_tools_from_private_key_and_env(monkeypatch):
    tools = clawfetch_tools(private_key=DUMMY_KEY)
    assert isinstance(tools[0].client, ClawFetch) and tools[0].client is tools[-1].client
    monkeypatch.setenv("CLAWFETCH_PRIVATE_KEY", DUMMY_KEY)
    assert isinstance(clawfetch_tools()[0].client, ClawFetch)
    assert isinstance(ClawFetchFetchTool().client, ClawFetch)


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("CLAWFETCH_PRIVATE_KEY", raising=False)
    with pytest.raises(ValueError, match="CLAWFETCH_PRIVATE_KEY"):
        clawfetch_tools()


def test_private_key_not_serialized():
    tool = ClawFetchFetchTool(private_key=DUMMY_KEY)
    assert DUMMY_KEY not in repr(tool) and DUMMY_KEY not in str(tool.model_dump())
