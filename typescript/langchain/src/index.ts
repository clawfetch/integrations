import { tool, type StructuredToolInterface } from '@langchain/core/tools';
import { z } from 'zod';
import { ClawFetch } from '@clawfetch/sdk';

export interface ClawFetchToolsOptions {
  /** Base wallet private key that pays for calls in USDC. Falls back to env CLAWFETCH_PRIVATE_KEY. */
  privateKey?: `0x${string}`;
  /** Pre-configured client. Takes precedence over `privateKey`. */
  client?: ClawFetch;
  /** Default max characters returned by fetch_url and render_page. */
  maxChars?: number;
}

/** Extractor names accepted by POST /extract `type` (keys of the server's extractor registry). */
export const EXTRACTORS = [
  'twitter', 'coingecko', 'github', 'news', 'npm', 'pypi', 'crates', 'hackernews', 'youtube',
  'wikipedia', 'producthunt', 'edgar', 'imdb', 'amazon', 'crunchbase', 'zillow', 'redfin',
] as const;

const PAYMENT_NOTE = 'paid automatically in USDC on Base via x402';

const json = (value: unknown) => JSON.stringify(value);

/** Returns the given client, or builds one from `privateKey` / CLAWFETCH_PRIVATE_KEY. */
export function createClawFetchClient(options: ClawFetchToolsOptions = {}): ClawFetch {
  if (options.client) return options.client;
  const privateKey = options.privateKey ?? (process.env.CLAWFETCH_PRIVATE_KEY as `0x${string}` | undefined);
  if (!privateKey) {
    throw new Error('ClawFetch: pass `privateKey` or `client`, or set CLAWFETCH_PRIVATE_KEY');
  }
  return new ClawFetch({ privateKey });
}

export function fetchUrlTool(options: ClawFetchToolsOptions = {}) {
  const client = createClawFetchClient(options);
  return tool(
    async ({ url, maxChars }) => json(await client.fetch(url, { maxChars: maxChars ?? options.maxChars })),
    {
      name: 'fetch_url',
      description:
        `Fetch a web page and return its readable text. Fast; does not run JavaScript. Use render_page for JS-heavy sites. Costs $0.001 per call (${PAYMENT_NOTE}).`,
      schema: z.object({
        url: z.string().url().describe('Absolute http(s) URL to fetch'),
        maxChars: z.number().int().positive().optional().describe('Max characters of text to return'),
      }),
    },
  );
}

export function renderPageTool(options: ClawFetchToolsOptions = {}) {
  const client = createClawFetchClient(options);
  return tool(
    async ({ url, waitFor }) => json(await client.render(url, { waitFor, maxChars: options.maxChars })),
    {
      name: 'render_page',
      description:
        `Render a JavaScript-heavy page in a real browser and return its visible text. Use when fetch_url returns empty or incomplete content. Costs $0.005 per call (${PAYMENT_NOTE}).`,
      schema: z.object({
        url: z.string().url().describe('Absolute http(s) URL to render'),
        waitFor: z.string().optional().describe('CSS selector to wait for before reading the page'),
      }),
    },
  );
}

export function extractDataTool(options: ClawFetchToolsOptions = {}) {
  const client = createClawFetchClient(options);
  return tool(
    async ({ url, type }) => json(await client.extract(url, { type })),
    {
      name: 'extract_data',
      description:
        `Extract structured JSON from a supported site: ${EXTRACTORS.join(', ')}. The extractor is auto-detected from the URL when type is omitted. Costs $0.008 per call (${PAYMENT_NOTE}).`,
      schema: z.object({
        url: z.string().url().describe('URL on a supported site'),
        type: z.enum(EXTRACTORS).optional().describe('Force a specific extractor'),
      }),
    },
  );
}

export function researchTopicTool(options: ClawFetchToolsOptions = {}) {
  const client = createClawFetchClient(options);
  return tool(
    async ({ query, maxResults }) => json(await client.research(query, { maxResults })),
    {
      name: 'research_topic',
      description:
        `Search the web for a query and return the text of the top result pages. Costs $0.02 per call (${PAYMENT_NOTE}).`,
      schema: z.object({
        query: z.string().min(1).describe('Search query'),
        maxResults: z.number().int().min(1).max(10).optional().describe('Number of result pages, 1-10 (default 5)'),
      }),
    },
  );
}

export function parseDocumentTool(options: ClawFetchToolsOptions = {}) {
  const client = createClawFetchClient(options);
  return tool(
    async ({ url, format }) => json(await client.parse(url, { format })),
    {
      name: 'parse_document',
      description:
        `Convert a document at a URL (pdf, docx, pptx, xlsx, odt, ods, odp, rtf, epub, csv, doc, ppt) to Markdown. No OCR: scanned PDFs fail. Costs $0.005 per call (${PAYMENT_NOTE}).`,
      schema: z.object({
        url: z.string().url().describe('Absolute http(s) URL of the document'),
        format: z.string().optional().describe('Format hint such as "csv" when it cannot be detected'),
      }),
    },
  );
}

export function checkDomainsTool(options: ClawFetchToolsOptions = {}) {
  const client = createClawFetchClient(options);
  return tool(
    async ({ domains }) => json(await client.domainsCheck(domains)),
    {
      name: 'check_domains',
      description:
        `Check whether domain names are available to register (live WHOIS). Costs $0.003 per call (${PAYMENT_NOTE}).`,
      schema: z.object({
        domains: z.array(z.string()).min(1).max(20).describe('Fully qualified domains, e.g. ["example.com"]'),
      }),
    },
  );
}

export function suggestDomainsTool(options: ClawFetchToolsOptions = {}) {
  const client = createClawFetchClient(options);
  return tool(
    async ({ keywords, tlds, maxCheck }) => json(await client.domainsSuggest(keywords, { tlds, maxCheck })),
    {
      name: 'suggest_domains',
      description:
        `Generate domain name ideas from keywords and check which are available. Costs $0.003 per call (${PAYMENT_NOTE}).`,
      schema: z.object({
        keywords: z.array(z.string()).min(1).describe('Keywords to combine, e.g. ["agent", "grid"]'),
        tlds: z.array(z.string()).optional().describe('TLDs to try (default com, ai, io)'),
        maxCheck: z.number().int().min(1).max(50).optional().describe('Max candidates to check (default 30)'),
      }),
    },
  );
}

/** All ClawFetch tools sharing one client. Pass to `model.bindTools()` or an agent. */
export function clawfetchTools(options: ClawFetchToolsOptions = {}): StructuredToolInterface[] {
  const shared = { ...options, client: createClawFetchClient(options) };
  return [
    fetchUrlTool(shared),
    renderPageTool(shared),
    extractDataTool(shared),
    researchTopicTool(shared),
    parseDocumentTool(shared),
    checkDomainsTool(shared),
    suggestDomainsTool(shared),
  ];
}
