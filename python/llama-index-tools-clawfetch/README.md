# llama-index-tools-clawfetch

LlamaIndex tool spec for [ClawFetch](https://api.clawfetch.ai), a pay-per-call web intelligence API for AI agents. Each call is paid with an x402 micropayment in USDC on Base.

## Install

```bash
pip install llama-index-tools-clawfetch
```

## Wallet

You need a Base wallet private key that holds USDC. There is no API key and no signup. Payments are gasless EIP-3009 transfers signed locally by the [`clawfetch`](https://pypi.org/project/clawfetch/) SDK, so the wallet does not need ETH. Use a dedicated wallet with a small balance.

```bash
export CLAWFETCH_PRIVATE_KEY=0x...
```

## Quickstart

```python
from llama_index.tools.clawfetch import ClawFetchToolSpec

spec = ClawFetchToolSpec()  # reads CLAWFETCH_PRIVATE_KEY
# or: ClawFetchToolSpec(private_key="0x...", max_chars=8000)

print(spec.fetch("https://example.com"))

tools = spec.to_tool_list()
```

To use the tools with an agent:

```python
from llama_index.core.agent.workflow import FunctionAgent

agent = FunctionAgent(tools=tools, llm=llm)  # llm: any LlamaIndex LLM with tool calling
response = await agent.run("What's new on news.ycombinator.com?")
```

## Tools

| Function | Price per call | What it does |
|---|---|---|
| `fetch(url)` | $0.001 | URL to readable text (no JavaScript) |
| `render(url, wait_for=None)` | $0.005 | JavaScript-rendered page to text |
| `extract(url, type=None)` | $0.008 | Typed JSON from 17 supported sites |
| `research(query, max_results=None)` | $0.02 | Web search plus source texts for citations |
| `parse(url, format=None)` | $0.005 | Office document or PDF at a URL to Markdown (no OCR) |
| `company(domain)` | $0.02 | Company profile from a domain: socials, emails, phones, tech stack, key pages |
| `domains_check(domains)` | $0.003 | Domain availability |
| `domains_suggest(keywords, tlds=None, max_check=None)` | $0.003 | Generate and check domain names from keywords |

Supported `extract` sites: twitter, coingecko, github, news, npm, pypi, crates, hackernews, youtube, wikipedia, producthunt, imdb, amazon, crunchbase, sec-edgar, zillow, redfin.

## Output and errors

Functions return a string. Fetch and render return the page title, URL and text. Parse returns Markdown. The other functions return the API response as JSON. Output is cut at `max_chars` (default 10,000).

SDK errors (`PaymentError`, `RateLimitError`, `ApiError`, `NetworkError`, all subclasses of `clawfetch.ClawFetchError`) are raised unchanged.

## License

MIT
