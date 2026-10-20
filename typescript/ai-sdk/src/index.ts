import { tool, type Tool } from 'ai';
import { z } from 'zod';
import {
  ClawFetch,
  type DomainCheckResult,
  type DomainSuggestResult,
  type ExtractResult,
  type FetchResult,
  type ParseResult,
  type RenderResult,
  type ResearchResult,
} from '@clawfetch/sdk';

export interface ClawFetchToolsOptions {
  /** Base wallet private key that pays for calls in USDC. Falls back to env CLAWFETCH_PRIVATE_KEY. */
  privateKey?: `0x${string}`;
  /** Pre-configured client. Takes precedence over `privateKey`. */
  client?: ClawFetch;
  /** Default max characters returned by fetchUrl and renderPage. */
  maxChars?: number;
}

/** Extractor names accepted by POST /extract `type` (keys of the server's extractor registry). */
export const EXTRACTORS = [
  'twitter', 'coingecko', 'github', 'news', 'npm', 'pypi', 'crates', 'hackernews', 'youtube',
  'wikipedia', 'producthunt', 'edgar', 'imdb', 'amazon', 'crunchbase', 'zillow', 'redfin',
] as const;

const fetchUrlInput = z.object({
  url: z.string().url().describe('Absolute http(s) URL to fetch'),
  maxChars: z.number().int().positive().optional().describe('Max characters of text to return'),
});

const renderPageInput = z.object({
  url: z.string().url().describe('Absolute http(s) URL to render'),
  waitFor: z.string().optional().describe('CSS selector to wait for before reading the page'),
});

const extractDataInput = z.object({
  url: z.string().url().describe('URL on a supported site'),
  type: z.enum(EXTRACTORS).optional().describe('Force a specific extractor'),
});

const researchTopicInput = z.object({
  query: z.string().min(1).describe('Search query'),
  maxResults: z.number().int().min(1).max(10).optional().describe('Number of result pages, 1-10 (default 5)'),
});

const parseDocumentInput = z.object({
  url: z.string().url().describe('Absolute http(s) URL of the document'),
  format: z.string().optional().describe('Format hint such as "csv" when it cannot be detected'),
});

const checkDomainsInput = z.object({
  domains: z.array(z.string()).min(1).max(20).describe('Fully qualified domains, e.g. ["example.com"]'),
});

const suggestDomainsInput = z.object({
  keywords: z.array(z.string()).min(1).describe('Keywords to combine, e.g. ["agent", "grid"]'),
  tlds: z.array(z.string()).optional().describe('TLDs to try (default com, ai, io)'),
  maxCheck: z.number().int().min(1).max(50).optional().describe('Max candidates to check (default 30)'),
});

/** A tool whose `execute` is always defined. */
type ClawFetchTool<INPUT, OUTPUT> = Tool<INPUT, OUTPUT> & { execute: NonNullable<Tool<INPUT, OUTPUT>['execute']> };

// A type alias (not an interface) so it stays assignable to the AI SDK's `ToolSet`.
export type ClawFetchTools = {
  fetchUrl: ClawFetchTool<z.infer<typeof fetchUrlInput>, FetchResult>;
  renderPage: ClawFetchTool<z.infer<typeof renderPageInput>, RenderResult>;
  extractData: ClawFetchTool<z.infer<typeof extractDataInput>, ExtractResult>;
  researchTopic: ClawFetchTool<z.infer<typeof researchTopicInput>, ResearchResult>;
  parseDocument: ClawFetchTool<z.infer<typeof parseDocumentInput>, ParseResult>;
  checkDomains: ClawFetchTool<z.infer<typeof checkDomainsInput>, DomainCheckResult>;
  suggestDomains: ClawFetchTool<z.infer<typeof suggestDomainsInput>, DomainSuggestResult>;
};

const PAYMENT_NOTE = 'paid automatically in USDC on Base via x402';

/** Returns the given client, or builds one from `privateKey` / CLAWFETCH_PRIVATE_KEY. */
export function createClawFetchClient(options: ClawFetchToolsOptions = {}): ClawFetch {
  if (options.client) return options.client;
  const privateKey = options.privateKey ?? (process.env.CLAWFETCH_PRIVATE_KEY as `0x${string}` | undefined);
  if (!privateKey) {
    throw new Error('ClawFetch: pass `privateKey` or `client`, or set CLAWFETCH_PRIVATE_KEY');
  }
  return new ClawFetch({ privateKey });
}

/** Vercel AI SDK tools for every paid ClawFetch endpoint. Pass the result as `tools`. */
export function clawfetchTools(options: ClawFetchToolsOptions = {}): ClawFetchTools {
  const client = createClawFetchClient(options);
  const { maxChars } = options;

  return {
    fetchUrl: tool({
      description:
        `Fetch a web page and return its readable text. Fast; does not run JavaScript. Use renderPage for JS-heavy sites. Costs $0.001 per call (${PAYMENT_NOTE}).`,
      inputSchema: fetchUrlInput,
      execute: ({ url, maxChars: max }) => client.fetch(url, { maxChars: max ?? maxChars }),
    }),

    renderPage: tool({
      description:
        `Render a JavaScript-heavy page in a real browser and return its visible text. Use when fetchUrl returns empty or incomplete content. Costs $0.005 per call (${PAYMENT_NOTE}).`,
      inputSchema: renderPageInput,
      execute: ({ url, waitFor }) => client.render(url, { waitFor, maxChars }),
    }),

    extractData: tool({
      description:
        `Extract structured JSON from a supported site: ${EXTRACTORS.join(', ')}. The extractor is auto-detected from the URL when type is omitted. Costs $0.008 per call (${PAYMENT_NOTE}).`,
      inputSchema: extractDataInput,
      execute: ({ url, type }) => client.extract(url, { type }),
    }),

    researchTopic: tool({
      description:
        `Search the web for a query and return the text of the top result pages. Costs $0.02 per call (${PAYMENT_NOTE}).`,
      inputSchema: researchTopicInput,
      execute: ({ query, maxResults }) => client.research(query, { maxResults }),
    }),

    parseDocument: tool({
      description:
        `Convert a document at a URL (pdf, docx, pptx, xlsx, odt, ods, odp, rtf, epub, csv, doc, ppt) to Markdown. No OCR: scanned PDFs fail. Costs $0.005 per call (${PAYMENT_NOTE}).`,
      inputSchema: parseDocumentInput,
      execute: ({ url, format }) => client.parse(url, { format }),
    }),

    checkDomains: tool({
      description:
        `Check whether domain names are available to register (live WHOIS). Costs $0.003 per call (${PAYMENT_NOTE}).`,
      inputSchema: checkDomainsInput,
      execute: ({ domains }) => client.domainsCheck(domains),
    }),

    suggestDomains: tool({
      description:
        `Generate domain name ideas from keywords and check which are available. Costs $0.003 per call (${PAYMENT_NOTE}).`,
      inputSchema: suggestDomainsInput,
      execute: ({ keywords, tlds, maxCheck }) => client.domainsSuggest(keywords, { tlds, maxCheck }),
    }),
  };
}
