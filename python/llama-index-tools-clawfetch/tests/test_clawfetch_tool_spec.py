"""Unit tests — the ClawFetch client is mocked: no network, no payments."""

import json
from unittest.mock import MagicMock

import pytest
from clawfetch import ClawFetch
from llama_index.core.tools import FunctionTool
from llama_index.core.tools.tool_spec.base import BaseToolSpec

from llama_index.tools.clawfetch import ClawFetchToolSpec

DUMMY_KEY = "0x0000000000000000000000000000000000000000000000000000000000000001"
PAGE = {"url": "https://a.b", "title": "T", "text": "hello"}

# (spec function, call kwargs, sdk method, expected args, expected kwargs, sdk result, expected output)
CASES = [
    ("fetch", {"url": "https://a.b"}, "fetch", ("https://a.b",), {"max_chars": 10_000},
     PAGE, "# T\nURL: https://a.b\n\nhello"),
    ("render", {"url": "https://a.b", "wait_for": "#app"}, "render", ("https://a.b",),
     {"max_chars": 10_000, "wait_for": "#app"}, PAGE, "# T\nURL: https://a.b\n\nhello"),
    ("extract", {"url": "https://github.com/a/b", "type": "github"}, "extract", ("https://github.com/a/b",),
     {"type": "github"}, {"type": "github", "stars": 1}, json.dumps({"type": "github", "stars": 1})),
    ("research", {"query": "x402"}, "research", ("x402",), {"max_results": None},
     {"query": "x402", "sources": 0, "results": []}, json.dumps({"query": "x402", "sources": 0, "results": []})),
    ("parse", {"url": "https://a.b/x.docx"}, "parse", ("https://a.b/x.docx",), {"format": None},
     {"markdown": "# Doc", "format": "docx", "chars": 5}, "# Doc"),
    ("company", {"domain": "vercel.com"}, "company", ("vercel.com",), {},
     {"domain": "vercel.com", "name": "Vercel"}, json.dumps({"domain": "vercel.com", "name": "Vercel"})),
    ("domains_check", {"domains": ["a.ai"]}, "domains_check", (["a.ai"],), {},
     {"checked": 1, "results": [{"domain": "a.ai", "available": None, "error": "timeout"}]},
     json.dumps({"checked": 1, "results": [{"domain": "a.ai", "available": None, "error": "timeout"}]})),
    ("domains_suggest", {"keywords": ["agent"], "tlds": ["ai"], "max_check": 5}, "domains_suggest",
     (["agent"],), {"tlds": ["ai"], "max_check": 5},
     {"keywords": ["agent"], "available": ["agent.ai"]}, json.dumps({"keywords": ["agent"], "available": ["agent.ai"]})),
]


@pytest.mark.parametrize("fn,call_kwargs,method,args,kwargs,result,expected", CASES)
def test_spec_function_calls_sdk_and_formats(fn, call_kwargs, method, args, kwargs, result, expected):
    client = MagicMock(spec=ClawFetch)
    getattr(client, method).return_value = result
    spec = ClawFetchToolSpec(client=client)
    assert getattr(spec, fn)(**call_kwargs) == expected
    getattr(client, method).assert_called_once_with(*args, **kwargs)


@pytest.mark.parametrize("fn,call_kwargs,method,args,kwargs,result,expected", CASES)
def test_function_tool_call_through_llama_index(fn, call_kwargs, method, args, kwargs, result, expected):
    client = MagicMock(spec=ClawFetch)
    getattr(client, method).return_value = result
    tools = {t.metadata.name: t for t in ClawFetchToolSpec(client=client).to_tool_list()}
    out = tools[fn].call(**call_kwargs)
    assert out.content == expected
    getattr(client, method).assert_called_once_with(*args, **kwargs)


def test_tool_list_metadata():
    tools = ClawFetchToolSpec(client=MagicMock(spec=ClawFetch)).to_tool_list()
    assert issubclass(ClawFetchToolSpec, BaseToolSpec)
    assert [t.metadata.name for t in tools] == [
        "fetch", "render", "extract", "research", "parse", "company", "domains_check", "domains_suggest",
    ]
    for t in tools:
        assert isinstance(t, FunctionTool)
        assert "$0." in t.metadata.description and "USDC" in t.metadata.description
    schema = tools[7].metadata.get_parameters_dict()
    assert schema["required"] == ["keywords"]
    assert schema["properties"]["keywords"]["type"] == "array"


def test_output_truncated_to_max_chars():
    client = MagicMock(spec=ClawFetch)
    client.parse.return_value = {"markdown": "x" * 50}
    assert ClawFetchToolSpec(client=client, max_chars=10).parse("https://a.b/x.pdf") == "x" * 10 + "\n...[truncated 40 chars]"


def test_from_private_key_and_env(monkeypatch):
    assert isinstance(ClawFetchToolSpec(private_key=DUMMY_KEY).client, ClawFetch)
    monkeypatch.setenv("CLAWFETCH_PRIVATE_KEY", DUMMY_KEY)
    assert isinstance(ClawFetchToolSpec().client, ClawFetch)


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("CLAWFETCH_PRIVATE_KEY", raising=False)
    with pytest.raises(ValueError, match="CLAWFETCH_PRIVATE_KEY"):
        ClawFetchToolSpec()
