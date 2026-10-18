# ClawFetch integrations

Agent-framework integrations for [ClawFetch](https://api.clawfetch.ai), a pay-per-call web intelligence API for AI agents. Calls are paid with x402 micropayments in USDC on Base. There is no API key: you need a Base wallet private key holding USDC, and payments are gasless EIP-3009 transfers signed locally.

## Python

| Package | Import | Framework | Path |
|---|---|---|---|
| `langchain-clawfetch` | `langchain_clawfetch` | LangChain (`langchain-core>=0.3,<2`) | [python/langchain-clawfetch](python/langchain-clawfetch) |
| `llama-index-tools-clawfetch` | `llama_index.tools.clawfetch` | LlamaIndex (`llama-index-core>=0.12,<0.15`) | [python/llama-index-tools-clawfetch](python/llama-index-tools-clawfetch) |
| `crewai-clawfetch` | `crewai_clawfetch` | CrewAI (`crewai>=1.0,<2`) | [python/crewai-clawfetch](python/crewai-clawfetch) |

All Python packages depend on the [`clawfetch`](https://pypi.org/project/clawfetch/) SDK (`>=0.2.2,<0.3`).

## TypeScript

| Package | Framework | Path |
|---|---|---|
| `@clawfetch/langchain` | LangChain.js | [typescript/langchain](typescript/langchain) |
| `@clawfetch/ai-sdk` | Vercel AI SDK | [typescript/ai-sdk](typescript/ai-sdk) |

## Endpoints and prices

| Endpoint | Price per call | What it does |
|---|---|---|
| fetch | $0.001 | URL to readable text (no JavaScript) |
| render | $0.005 | JavaScript-rendered page to text |
| extract | $0.008 | Typed JSON from 17 supported sites |
| research | $0.02 | Web search plus source texts for citations |
| parse | $0.005 | Office document or PDF to Markdown (no OCR) |
| domains check | $0.003 | Domain availability |
| domains suggest | $0.003 | Generate and check domain names from keywords |

## License

MIT
