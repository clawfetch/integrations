import { afterEach, describe, expect, it, vi } from 'vitest';
import { ToolMessage } from '@langchain/core/messages';
import type { ClawFetch } from '@clawfetch/sdk';
import { clawfetchTools, createClawFetchClient, fetchUrlTool } from '../src/index';

const DUMMY_KEY = '0x0000000000000000000000000000000000000000000000000000000000000001' as const;

function mockClient() {
  return {
    fetch: vi.fn(async (url: string) => ({ url, title: 'Example', content: 'hello' })),
    render: vi.fn(async (url: string) => ({ url, content: 'rendered' })),
    extract: vi.fn(async (url: string) => ({ url, extractor: 'github', data: { stars: 1 } })),
    research: vi.fn(async (topic: string) => ({ topic, summary: '', sources: [] })),
    parse: vi.fn(async () => ({ markdown: '# Doc', format: 'pdf', chars: 5 })),
    company: vi.fn(async (domain: string) => ({ domain, name: 'Vercel', socials: {}, techStack: [] })),
    domainsCheck: vi.fn(async (domains: string[]) => ({ domains: domains.map(domain => ({ domain, available: true })) })),
    domainsSuggest: vi.fn(async () => ({ query: 'agent grid', generated: 1, checked: 1, suggestions: [] })),
  };
}

function setup(extra: { maxChars?: number } = {}) {
  const client = mockClient();
  const tools = clawfetchTools({ client: client as unknown as ClawFetch, ...extra });
  const byName = Object.fromEntries(tools.map(t => [t.name, t]));
  return { client, tools, byName };
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('clawfetchTools', () => {
  it('returns one tool per paid endpoint, each stating its price', () => {
    const { tools } = setup();
    const prices: Record<string, string> = {
      fetch_url: '$0.001', render_page: '$0.005', extract_data: '$0.008', research_topic: '$0.02',
      parse_document: '$0.005', enrich_company: '$0.02', check_domains: '$0.003', suggest_domains: '$0.003',
    };
    expect(tools.map(t => t.name).sort()).toEqual(Object.keys(prices).sort());
    for (const t of tools) expect(t.description).toContain(`Costs ${prices[t.name]} per call`);
  });

  it('fetch_url → client.fetch, falling back to the maxChars option; returns JSON text', async () => {
    const { client, byName } = setup({ maxChars: 500 });
    const out = await byName.fetch_url.invoke({ url: 'https://example.com' });
    expect(client.fetch).toHaveBeenCalledWith('https://example.com', { maxChars: 500 });
    expect(JSON.parse(out)).toMatchObject({ content: 'hello' });

    await byName.fetch_url.invoke({ url: 'https://example.com', maxChars: 50 });
    expect(client.fetch).toHaveBeenLastCalledWith('https://example.com', { maxChars: 50 });
  });

  it('render_page → client.render', async () => {
    const { client, byName } = setup({ maxChars: 500 });
    await byName.render_page.invoke({ url: 'https://example.com', waitFor: '#app' });
    expect(client.render).toHaveBeenCalledWith('https://example.com', { waitFor: '#app', maxChars: 500 });
  });

  it('extract_data → client.extract with type', async () => {
    const { client, byName } = setup();
    const out = await byName.extract_data.invoke({ url: 'https://github.com/a/b', type: 'github' });
    expect(client.extract).toHaveBeenCalledWith('https://github.com/a/b', { type: 'github' });
    expect(JSON.parse(out)).toMatchObject({ data: { stars: 1 } });
  });

  it('research_topic → client.research(query)', async () => {
    const { client, byName } = setup();
    await byName.research_topic.invoke({ query: 'x402 payments', maxResults: 3 });
    expect(client.research).toHaveBeenCalledWith('x402 payments', { maxResults: 3 });
  });

  it('parse_document → client.parse(url)', async () => {
    const { client, byName } = setup();
    const out = await byName.parse_document.invoke({ url: 'https://example.com/a.pdf' });
    expect(client.parse).toHaveBeenCalledWith('https://example.com/a.pdf', { format: undefined });
    expect(JSON.parse(out)).toMatchObject({ markdown: '# Doc' });
  });

  it('enrich_company → client.company(domain)', async () => {
    const { client, byName } = setup();
    const out = await byName.enrich_company.invoke({ domain: 'vercel.com' });
    expect(client.company).toHaveBeenCalledWith('vercel.com');
    expect(JSON.parse(out)).toMatchObject({ name: 'Vercel' });
  });

  it('check_domains → client.domainsCheck', async () => {
    const { client, byName } = setup();
    const out = await byName.check_domains.invoke({ domains: ['example.com'] });
    expect(client.domainsCheck).toHaveBeenCalledWith(['example.com']);
    expect(JSON.parse(out)).toEqual({ domains: [{ domain: 'example.com', available: true }] });
  });

  it('suggest_domains → client.domainsSuggest', async () => {
    const { client, byName } = setup();
    await byName.suggest_domains.invoke({ keywords: ['agent', 'grid'], tlds: ['ai'], maxCheck: 10 });
    expect(client.domainsSuggest).toHaveBeenCalledWith(['agent', 'grid'], { tlds: ['ai'], maxCheck: 10 });
  });

  it('rejects invalid input before calling (and paying for) the API', async () => {
    const { client, byName } = setup();
    await expect(byName.extract_data.invoke({ url: 'https://sec.gov', type: 'sec-edgar' })).rejects.toThrow();
    await expect(byName.research_topic.invoke({ query: 'x', maxResults: 11 })).rejects.toThrow();
    await expect(byName.fetch_url.invoke({ url: 'not a url' })).rejects.toThrow();
    expect(client.extract).not.toHaveBeenCalled();
    expect(client.research).not.toHaveBeenCalled();
    expect(client.fetch).not.toHaveBeenCalled();
  });

  it('handles a model ToolCall (agent path) and returns a ToolMessage', async () => {
    const { client, byName } = setup();
    const msg = await byName.research_topic.invoke({
      type: 'tool_call', id: 'call_1', name: 'research_topic', args: { query: 'base usdc' },
    });
    expect(client.research).toHaveBeenCalledWith('base usdc', { maxResults: undefined });
    expect(msg).toBeInstanceOf(ToolMessage);
    expect(msg.tool_call_id).toBe('call_1');
    expect(JSON.parse(msg.content as string)).toMatchObject({ topic: 'base usdc' });
  });

  it('shares one client across all tools', () => {
    vi.stubEnv('CLAWFETCH_PRIVATE_KEY', DUMMY_KEY);
    expect(clawfetchTools()).toHaveLength(8);
  });

  it('individual tool factories work standalone', async () => {
    const client = mockClient();
    const t = fetchUrlTool({ client: client as unknown as ClawFetch });
    await t.invoke({ url: 'https://example.com' });
    expect(client.fetch).toHaveBeenCalledOnce();
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
