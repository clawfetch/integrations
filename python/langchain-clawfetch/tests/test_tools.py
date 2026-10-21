"""Unit tests — the ClawFetch client is mocked: no network, no payments."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from clawfetch import AsyncClawFetch, ClawFetch, PaymentError
from langchain_core.tools import ToolException

from langchain_clawfetch import (
    ClawFetchDomainsCheck,
    ClawFetchDomainsSuggest,
    ClawFetchExtract,
    ClawFetchFetch,
    ClawFetchParse,
    ClawFetchCompany,
    ClawFetchRender,
    ClawFetchResearch,
    ClawFetchToolkit,
)

DUMMY_KEY = "0x0000000000000000000000000000000000000000000000000000000000000001"
PAGE = {"url": "https://a.b", "title": "T", "text": "hello"}

# (tool class, tool input, sdk method, expected positional args, expected kwargs, sdk result, expected output)
CASES = [
    (ClawFetchFetch, {"url": "https://a.b"}, "fetch", ("https://a.b",), {"max_chars": 10_000},
     PAGE, "# T\nURL: https://a.b\n\nhello"),
    (ClawFetchRender, {"url": "https://a.b", "wait_for": "#app"}, "render", ("https://a.b",),
     {"max_chars": 10_000, "wait_for": "#app"}, PAGE, "# T\nURL: https://a.b\n\nhello"),
    (ClawFetchExtract, {"url": "https://github.com/a/b"}, "extract", ("https://github.com/a/b",),
     {"type": None}, {"type": "github", "stars": 1}, json.dumps({"type": "github", "stars": 1})),
    (ClawFetchResearch, {"query": "x402", "max_results": 3}, "research", ("x402",), {"max_results": 3},
     {"query": "x402", "sources": 0, "results": []}, json.dumps({"query": "x402", "sources": 0, "results": []})),
    (ClawFetchParse, {"url": "https://a.b/x.docx"}, "parse", ("https://a.b/x.docx",), {"format": None},
     {"markdown": "# Doc", "format": "docx", "chars": 5}, "# Doc"),
    (ClawFetchCompany, {"domain": "vercel.com"}, "company", ("vercel.com",), {},
     {"domain": "vercel.com", "name": "Vercel"}, json.dumps({"domain": "vercel.com", "name": "Vercel"})),
    (ClawFetchDomainsCheck, {"domains": ["a.ai"]}, "domains_check", (["a.ai"],), {},
     {"checked": 1, "available": 1, "taken": 0, "results": [{"domain": "a.ai", "available": True}]},
     json.dumps({"checked": 1, "available": 1, "taken": 0, "results": [{"domain": "a.ai", "available": True}]})),
    (ClawFetchDomainsSuggest, {"keywords": ["agent"], "tlds": ["ai"], "max_check": 5}, "domains_suggest",
     (["agent"],), {"tlds": ["ai"], "max_check": 5},
     {"keywords": ["agent"], "available": ["agent.ai"]}, json.dumps({"keywords": ["agent"], "available": ["agent.ai"]})),
]


def _clients():
    return MagicMock(spec=ClawFetch), MagicMock(spec=AsyncClawFetch)


@pytest.mark.parametrize("cls,tool_input,method,args,kwargs,result,expected", CASES)
def test_sync_tool_calls_sdk_and_formats(cls, tool_input, method, args, kwargs, result, expected):
    client, aclient = _clients()
    getattr(client, method).return_value = result
    tool = cls(client=client, async_client=aclient)
    assert tool.invoke(tool_input) == expected
    getattr(client, method).assert_called_once_with(*args, **kwargs)


@pytest.mark.parametrize("cls,tool_input,method,args,kwargs,result,expected", CASES)
async def test_async_tool_calls_async_sdk(cls, tool_input, method, args, kwargs, result, expected):
    client, aclient = _clients()
    setattr(aclient, method, AsyncMock(return_value=result))
    tool = cls(client=client, async_client=aclient)
    assert await tool.ainvoke(tool_input) == expected
    getattr(aclient, method).assert_awaited_once_with(*args, **kwargs)
    getattr(client, method).assert_not_called()


async def test_async_falls_back_to_sync_client():
    client = MagicMock(spec=ClawFetch)
    client.fetch.return_value = PAGE
    tool = ClawFetchFetch(client=client)
    assert await tool.ainvoke({"url": "https://a.b"}) == "# T\nURL: https://a.b\n\nhello"


def test_output_truncated_to_max_chars():
    client, aclient = _clients()
    client.parse.return_value = {"markdown": "x" * 50}
    out = ClawFetchParse(client=client, async_client=aclient, max_chars=10).invoke({"url": "https://a.b/x.pdf"})
    assert out == "x" * 10 + "\n...[truncated 40 chars]"


def test_sdk_error_becomes_tool_exception():
    client, aclient = _clients()
    client.research.side_effect = PaymentError("insufficient USDC", endpoint="/research")
    with pytest.raises(ToolException, match="clawfetch_research failed \\(PaymentError\\): insufficient USDC"):
        ClawFetchResearch(client=client, async_client=aclient).invoke({"query": "x"})


def test_sdk_error_returned_as_text_when_handle_tool_error():
    client, aclient = _clients()
    client.fetch.side_effect = PaymentError("insufficient USDC", endpoint="/fetch")
    tool = ClawFetchFetch(client=client, async_client=aclient, handle_tool_error=True)
    assert "insufficient USDC" in tool.invoke({"url": "https://a.b"})


def test_tool_metadata():
    client, aclient = _clients()
    tools = ClawFetchToolkit(client=client, async_client=aclient).get_tools()
    assert [t.name for t in tools] == [
        "clawfetch_fetch", "clawfetch_render", "clawfetch_extract", "clawfetch_research",
        "clawfetch_parse", "clawfetch_company", "clawfetch_domains_check", "clawfetch_domains_suggest",
    ]
    for t in tools:
        assert "$0." in t.description and "USDC" in t.description
        assert t.client is client and t.async_client is aclient


def test_toolkit_from_private_key():
    tools = ClawFetchToolkit(private_key=DUMMY_KEY, max_chars=500).get_tools()
    assert isinstance(tools[0].client, ClawFetch)
    assert isinstance(tools[0].async_client, AsyncClawFetch)
    assert tools[0].client is tools[-1].client
    assert all(t.max_chars == 500 for t in tools)


def test_toolkit_from_env(monkeypatch):
    monkeypatch.setenv("CLAWFETCH_PRIVATE_KEY", DUMMY_KEY)
    assert isinstance(ClawFetchFetch().client, ClawFetch)


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("CLAWFETCH_PRIVATE_KEY", raising=False)
    with pytest.raises(ValueError, match="CLAWFETCH_PRIVATE_KEY"):
        ClawFetchToolkit()


def test_private_key_not_serialized():
    tool = ClawFetchFetch(private_key=DUMMY_KEY)
    assert DUMMY_KEY not in repr(tool) and DUMMY_KEY not in str(tool.model_dump())
