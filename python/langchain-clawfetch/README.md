# langchain-clawfetch

LangChain tools for [ClawFetch](https://api.clawfetch.ai), a pay-per-call web intelligence API for AI agents. Each call is paid with an x402 micropayment in USDC on Base.

## Install

```bash
pip install langchain-clawfetch
```

## Wallet

You need a Base wallet private key that holds USDC. There is no API key and no signup. Payments are gasless EIP-3009 transfers signed locally by the [`clawfetch`](https://pypi.org/project/clawfetch/) SDK, so the wallet does not need ETH. Use a dedicated wallet with a small balance.

```bash
export CLAWFETCH_PRIVATE_KEY=0x...
```

## Quickstart

```python
from langchain_clawfetch import ClawFetchToolkit

tools = ClawFetchToolkit().get_tools()  # reads CLAWFETCH_PRIVATE_KEY
# or: ClawFetchToolkit(private_key="0x...", max_chars=8000)

fetch = tools[0]
print(fetch.invoke({"url": "https://example.com"}))
```

To use the tools with an agent:

```python
from langchain.agents import create_agent

agent = create_agent(llm, tools=tools)  # llm: any LangChain chat model
agent.invoke({"messages": [{"role": "user", "content": "What's new on news.ycombinator.com?"}]})
```

You can also create a single tool, or pass an existing client:

```python
from clawfetch import ClawFetch, AsyncClawFetch
from langchain_clawfetch import ClawFetchResearch

research = ClawFetchResearch(client=ClawFetch(private_key="0x..."), async_client=AsyncClawFetch(private_key="0x..."))
```

Every tool supports `invoke` and `ainvoke`. Async calls use `AsyncClawFetch`.

## Tools

| Tool | Name | Price per call | What it does |
|---|---|---|---|
| `ClawFetchFetch` | `clawfetch_fetch` | $0.001 | URL to readable text (no JavaScript) |
| `ClawFetchRender` | `clawfetch_render` | $0.005 | JavaScript-rendered page to text |
| `ClawFetchExtract` | `clawfetch_extract` | $0.008 | Typed JSON from 17 supported sites |
| `ClawFetchResearch` | `clawfetch_research` | $0.02 | Web search plus source texts for citations |
| `ClawFetchParse` | `clawfetch_parse` | $0.005 | Office document or PDF at a URL to Markdown (no OCR) |
| `ClawFetchCompany` | `clawfetch_company` | $0.02 | Company profile from a domain: socials, emails, phones, tech stack, key pages |
| `ClawFetchDomainsCheck` | `clawfetch_domains_check` | $0.003 | Domain availability |
| `ClawFetchDomainsSuggest` | `clawfetch_domains_suggest` | $0.003 | Generate and check domain names from keywords |

Supported `clawfetch_extract` sites: twitter, coingecko, github, news, npm, pypi, crates, hackernews, youtube, wikipedia, producthunt, imdb, amazon, crunchbase, sec-edgar, zillow, redfin.

## Output and errors

Tools return a string. Fetch and render return the page title, URL and text. Parse returns Markdown. The other tools return the API response as JSON. Output is cut at `max_chars` (default 10,000).

SDK errors (`PaymentError`, `RateLimitError`, `ApiError`, `NetworkError`) are raised as `ToolException`. To hand the message to the model instead of raising, pass `handle_tool_error=True` when you create a tool.

## License

MIT
