import { afterEach, describe, expect, it, vi } from 'vitest';
import { generateText } from 'ai';
import { MockLanguageModelV4 } from 'ai/test';
import type { z } from 'zod';
import type { ClawFetch } from '@clawfetch/sdk';
import { clawfetchTools, createClawFetchClient } from '../src/index';

const DUMMY_KEY = '0x0000000000000000000000000000000000000000000000000000000000000001' as const;

function mockClient() {
  return {
    fetch: vi.fn(async (url: string) => ({ url, title: 'Example', content: 'hello' })),
    render: vi.fn(async (url: string) => ({ url, content: 'rendered' })),
    extract: vi.fn(async (url: string) => ({ url, extractor: 'github', data: { stars: 1 } })),
    research: vi.fn(async (topic: string) => ({ topic, summary: '', sources: [] })),
    parse: vi.fn(async () => ({ markdown: '# Doc', format: 'pdf', chars: 5 })),
    domainsCheck: vi.fn(async (domains: string[]) => ({ domains: domains.map(domain => ({ domain, available: true })) })),
    domainsSuggest: vi.fn(async () => ({ query: 'agent grid', generated: 1, checked: 1, suggestions: [] })),
  };
}

const opts = { toolCallId: 't1', messages: [], context: {} };

function setup(extra: { maxChars?: number } = {}) {
  const client = mockClient();
  const tools = clawfetchTools({ client: client as unknown as ClawFetch, ...extra });
  return { client, tools };
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('clawfetchTools', () => {
  it('exposes one tool per paid endpoint, each stating its price', () => {
    const { tools } = setup();
    expect(Object.keys(tools).sort()).toEqual(
      ['checkDomains', 'extractData', 'fetchUrl', 'parseDocument', 'renderPage', 'researchTopic', 'suggestDomains'],
    );
    const prices: Record<string, string> = {
      fetchUrl: '$0.001', renderPage: '$0.005', extractData: '$0.008', researchTopic: '$0.02',
      parseDocument: '$0.005', checkDomains: '$0.003', suggestDomains: '$0.003',
    };
    for (const [name, t] of Object.entries(tools)) {
      expect(t.description).toContain(`Costs ${prices[name]} per call`);
    }
  });

  it('fetchUrl → client.fetch, falling back to the maxChars option', async () => {
    const { client, tools } = setup({ maxChars: 500 });
    const out = await tools.fetchUrl.execute({ url: 'https://example.com' }, opts);
    expect(client.fetch).toHaveBeenCalledWith('https://example.com', { maxChars: 500 });
    expect(out).toMatchObject({ content: 'hello' });

    await tools.fetchUrl.execute({ url: 'https://example.com', maxChars: 50 }, opts);
    expect(client.fetch).toHaveBeenLastCalledWith('https://example.com', { maxChars: 50 });
  });

  it('renderPage → client.render', async () => {
    const { client, tools } = setup({ maxChars: 500 });
    await tools.renderPage.execute({ url: 'https://example.com', waitFor: '#app' }, opts);
    expect(client.render).toHaveBeenCalledWith('https://example.com', { waitFor: '#app', maxChars: 500 });
  });

  it('extractData → client.extract with type', async () => {
    const { client, tools } = setup();
    const out = await tools.extractData.execute({ url: 'https://github.com/a/b', type: 'github' }, opts);
    expect(client.extract).toHaveBeenCalledWith('https://github.com/a/b', { type: 'github' });
    expect(out).toMatchObject({ data: { stars: 1 } });
  });

  it('researchTopic → client.research(query)', async () => {
    const { client, tools } = setup();
    await tools.researchTopic.execute({ query: 'x402 payments', maxResults: 3 }, opts);
    expect(client.research).toHaveBeenCalledWith('x402 payments', { maxResults: 3 });
  });

  it('parseDocument → client.parse(url)', async () => {
    const { client, tools } = setup();
    const out = await tools.parseDocument.execute({ url: 'https://example.com/a.pdf' }, opts);
    expect(client.parse).toHaveBeenCalledWith('https://example.com/a.pdf', { format: undefined });
    expect(out).toMatchObject({ markdown: '# Doc' });
  });

  it('checkDomains → client.domainsCheck', async () => {
    const { client, tools } = setup();
    const out = await tools.checkDomains.execute({ domains: ['example.com'] }, opts);
    expect(client.domainsCheck).toHaveBeenCalledWith(['example.com']);
    expect(out).toEqual({ domains: [{ domain: 'example.com', available: true }] });
  });

  it('suggestDomains → client.domainsSuggest', async () => {
    const { client, tools } = setup();
    await tools.suggestDomains.execute({ keywords: ['agent', 'grid'], tlds: ['ai'], maxCheck: 10 }, opts);
    expect(client.domainsSuggest).toHaveBeenCalledWith(['agent', 'grid'], { tlds: ['ai'], maxCheck: 10 });
  });

  it('input schemas reject invalid input before the API (and a payment) is reached', () => {
    const { tools } = setup();
    const parse = (t: { inputSchema: unknown }, v: unknown) => (t.inputSchema as z.ZodType).safeParse(v).success;
    expect(parse(tools.extractData, { url: 'https://sec.gov', type: 'sec-edgar' })).toBe(false);
    expect(parse(tools.extractData, { url: 'https://sec.gov', type: 'edgar' })).toBe(true);
    expect(parse(tools.researchTopic, { query: 'x', maxResults: 11 })).toBe(false);
    expect(parse(tools.fetchUrl, { url: 'not a url' })).toBe(false);
    expect(parse(tools.checkDomains, { domains: [] })).toBe(false);
  });

  it('runs through generateText: model tool call is validated and dispatched to the SDK', async () => {
    const { client, tools } = setup();
    const model = new MockLanguageModelV4({
      doGenerate: {
        content: [{ type: 'tool-call', toolCallId: 'c1', toolName: 'researchTopic', input: JSON.stringify({ query: 'base usdc' }) }],
        finishReason: { unified: 'tool-calls', raw: undefined },
        usage: {
          inputTokens: { total: 1, noCache: 1, cacheRead: 0, cacheWrite: 0 },
          outputTokens: { total: 1, text: 1, reasoning: 0 },
        },
        warnings: [],
      },
    });
    const result = await generateText({ model, tools, prompt: 'research base usdc' });
    expect(client.research).toHaveBeenCalledWith('base usdc', { maxResults: undefined });
    expect(result.toolResults[0]).toMatchObject({ toolName: 'researchTopic', output: { topic: 'base usdc' } });

    // The model was offered JSON-schema tool definitions for every endpoint.
    const offered = model.doGenerateCalls[0].tools?.map(t => t.name).sort();
    expect(offered).toHaveLength(7);
  });
});

describe('createClawFetchClient', () => {
  it('returns the provided client unchanged', () => {
    const client = mockClient() as unknown as ClawFetch;
    expect(createClawFetchClient({ client })).toBe(client);
  });

  it('builds a client from privateKey', () => {
    expect(createClawFetchClient({ privateKey: DUMMY_KEY }).walletAddress).toMatch(/^0x[0-9a-fA-F]{40}$/);
  });

  it('falls back to CLAWFETCH_PRIVATE_KEY', () => {
    vi.stubEnv('CLAWFETCH_PRIVATE_KEY', DUMMY_KEY);
    expect(createClawFetchClient().walletAddress).toBe(createClawFetchClient({ privateKey: DUMMY_KEY }).walletAddress);
  });

  it('throws a clear error when no key or client is given', () => {
    vi.stubEnv('CLAWFETCH_PRIVATE_KEY', '');
    expect(() => clawfetchTools()).toThrow(/CLAWFETCH_PRIVATE_KEY/);
  });
});
