# @clawfetch/ai-sdk

[Vercel AI SDK](https://ai-sdk.dev) tools for [ClawFetch](https://api.clawfetch.ai): pay-per-call web fetching, rendering, extraction, research, document parsing and domain checks for AI agents.

## Install

```bash
npm install @clawfetch/ai-sdk ai zod
```

Requires `ai` v7 and `zod` 3.25.76+ or 4.

## Quickstart

```ts
import { generateText, stepCountIs } from 'ai';
import { openai } from '@ai-sdk/openai';
import { clawfetchTools } from '@clawfetch/ai-sdk';

const { text } = await generateText({
  model: openai('gpt-5'),
  tools: clawfetchTools(), // reads CLAWFETCH_PRIVATE_KEY
  stopWhen: stepCountIs(5),
  prompt: 'What changed in the latest release of vercel/ai on GitHub?',
});
```

Pick only the tools you want:

```ts
const { fetchUrl, researchTopic } = clawfetchTools({ privateKey: '0x…' });
await generateText({ model, tools: { fetchUrl, researchTopic }, prompt });
```

### Options

| Option | Type | Description |
|---|---|---|
| `privateKey` | `` `0x${string}` `` | Wallet key that pays for calls. Defaults to `process.env.CLAWFETCH_PRIVATE_KEY`. |
| `client` | `ClawFetch` | A pre-configured [`@clawfetch/sdk`](https://www.npmjs.com/package/@clawfetch/sdk) client (custom base URL, timeouts, retries). Takes precedence over `privateKey`. |
| `maxChars` | `number` | Default text limit for `fetchUrl` and `renderPage`. |

## Tools and prices

| Tool | Endpoint | Price per call | What it does |
|---|---|---|---|
| `fetchUrl` | `POST /fetch` | $0.001 | Fetch a page as readable text |
| `renderPage` | `POST /render` | $0.005 | Render a JS-heavy page in a browser |
| `extractData` | `POST /extract` | $0.008 | Structured JSON from 17 site extractors |
| `researchTopic` | `POST /research` | $0.02 | Web search plus top result pages |
| `parseDocument` | `POST /parse` | $0.005 | Document (pdf, docx, xlsx, …) to Markdown |
| `enrichCompany` | `POST /company` | $0.02 | Company profile from a domain: socials, emails, tech stack, key pages |
| `checkDomains` | `POST /domains/check` | $0.003 | Domain availability (WHOIS) |
| `suggestDomains` | `POST /domains/suggest` | $0.003 | Domain ideas from keywords, checked |

Prices are in USDC and charged only when a tool runs. The model sees each price in the tool description.

## Wallet

ClawFetch has no API keys and no accounts. Each call is paid with an [x402](https://x402.org) micropayment in **USDC on Base**, signed by your wallet. You need:

- a Base wallet private key (`0x…`), passed as `privateKey` or set as `CLAWFETCH_PRIVATE_KEY`
- some USDC on Base in that wallet

Payments are gasless signed authorizations, so the wallet needs no ETH. Use a dedicated wallet holding only the USDC you are willing to spend, and keep the key out of source control.

## License

MIT
