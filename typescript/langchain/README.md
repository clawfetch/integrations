# @clawfetch/langchain

[LangChain.js](https://js.langchain.com) tools for [ClawFetch](https://api.clawfetch.ai): pay-per-call web fetching, rendering, extraction, research, document parsing and domain checks for AI agents.

## Install

```bash
npm install @clawfetch/langchain @langchain/core zod
```

Requires `@langchain/core` v1 and `zod` 3.25.76+ or 4.

## Quickstart

```ts
import { createAgent } from 'langchain';
import { clawfetchTools } from '@clawfetch/langchain';

const agent = createAgent({
  model: 'openai:gpt-5',
  tools: clawfetchTools(), // reads CLAWFETCH_PRIVATE_KEY
});

const result = await agent.invoke({
  messages: [{ role: 'user', content: 'Summarize the top Hacker News story right now.' }],
});
```

Or bind to any tool-calling chat model:

```ts
const model = new ChatOpenAI({ model: 'gpt-5' }).bindTools(clawfetchTools({ privateKey: '0x…' }));
```

Each tool is also exported as a factory (`fetchUrlTool`, `renderPageTool`, `extractDataTool`, `researchTopicTool`, `parseDocumentTool`, `enrichCompanyTool`, `checkDomainsTool`, `suggestDomainsTool`) taking the same options. Tools return the API response as a JSON string.

### Options

| Option | Type | Description |
|---|---|---|
| `privateKey` | `` `0x${string}` `` | Wallet key that pays for calls. Defaults to `process.env.CLAWFETCH_PRIVATE_KEY`. |
| `client` | `ClawFetch` | A pre-configured [`@clawfetch/sdk`](https://www.npmjs.com/package/@clawfetch/sdk) client (custom base URL, timeouts, retries). Takes precedence over `privateKey`. |
| `maxChars` | `number` | Default text limit for `fetch_url` and `render_page`. |

## Tools and prices

| Tool | Endpoint | Price per call | What it does |
|---|---|---|---|
| `fetch_url` | `POST /fetch` | $0.001 | Fetch a page as readable text |
| `render_page` | `POST /render` | $0.005 | Render a JS-heavy page in a browser |
| `extract_data` | `POST /extract` | $0.008 | Structured JSON from 17 site extractors |
| `research_topic` | `POST /research` | $0.02 | Web search plus top result pages |
| `parse_document` | `POST /parse` | $0.005 | Document (pdf, docx, xlsx, …) to Markdown |
| `enrich_company` | `POST /company` | $0.02 | Company profile from a domain: socials, emails, tech stack, key pages |
| `check_domains` | `POST /domains/check` | $0.003 | Domain availability (WHOIS) |
| `suggest_domains` | `POST /domains/suggest` | $0.003 | Domain ideas from keywords, checked |

Prices are in USDC and charged only when a tool runs. The model sees each price in the tool description.

## Wallet

ClawFetch has no API keys and no accounts. Each call is paid with an [x402](https://x402.org) micropayment in **USDC on Base**, signed by your wallet. You need:

- a Base wallet private key (`0x…`), passed as `privateKey` or set as `CLAWFETCH_PRIVATE_KEY`
- some USDC on Base in that wallet

Payments are gasless signed authorizations, so the wallet needs no ETH. Use a dedicated wallet holding only the USDC you are willing to spend, and keep the key out of source control.

## License

MIT
