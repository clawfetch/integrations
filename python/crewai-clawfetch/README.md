# crewai-clawfetch

CrewAI tools for [ClawFetch](https://api.clawfetch.ai), a pay-per-call web intelligence API for AI agents. Each call is paid with an x402 micropayment in USDC on Base.

## Install

```bash
pip install crewai-clawfetch
```

## Wallet

You need a Base wallet private key that holds USDC. There is no API key and no signup. Payments are gasless EIP-3009 transfers signed locally by the [`clawfetch`](https://pypi.org/project/clawfetch/) SDK, so the wallet does not need ETH. Use a dedicated wallet with a small balance.

```bash
export CLAWFETCH_PRIVATE_KEY=0x...
```

## Quickstart

```python
from crewai import Agent
from crewai_clawfetch import clawfetch_tools

tools = clawfetch_tools()  # reads CLAWFETCH_PRIVATE_KEY
# or: clawfetch_tools(private_key="0x...", max_chars=8000)

researcher = Agent(
    role="Researcher",
    goal="Answer questions with cited web sources",
    backstory="You read primary sources before answering.",
    tools=tools,
)
```

You can also create a single tool, or pass an existing client:

```python
from clawfetch import ClawFetch
from crewai_clawfetch import ClawFetchFetchTool

fetch = ClawFetchFetchTool(client=ClawFetch(private_key="0x..."))
print(fetch.run(url="https://example.com"))
```

## Tools

| Tool | Name | Price per call | What it does |
|---|---|---|---|
| `ClawFetchFetchTool` | `clawfetch_fetch` | $0.001 | URL to readable text (no JavaScript) |
| `ClawFetchRenderTool` | `clawfetch_render` | $0.005 | JavaScript-rendered page to text |
| `ClawFetchExtractTool` | `clawfetch_extract` | $0.008 | Typed JSON from 17 supported sites |
| `ClawFetchResearchTool` | `clawfetch_research` | $0.02 | Web search plus source texts for citations |
| `ClawFetchParseTool` | `clawfetch_parse` | $0.005 | Office document or PDF at a URL to Markdown (no OCR) |
| `ClawFetchDomainsCheckTool` | `clawfetch_domains_check` | $0.003 | Domain availability |
| `ClawFetchDomainsSuggestTool` | `clawfetch_domains_suggest` | $0.003 | Generate and check domain names from keywords |

Supported `clawfetch_extract` sites: twitter, coingecko, github, news, npm, pypi, crates, hackernews, youtube, wikipedia, producthunt, imdb, amazon, crunchbase, sec-edgar, zillow, redfin.

## Output and errors

Tools return a string. Fetch and render return the page title, URL and text. Parse returns Markdown. The other tools return the API response as JSON. Output is cut at `max_chars` (default 10,000).

SDK errors (`PaymentError`, `RateLimitError`, `ApiError`, `NetworkError`, all subclasses of `clawfetch.ClawFetchError`) are raised unchanged.

## License

MIT
