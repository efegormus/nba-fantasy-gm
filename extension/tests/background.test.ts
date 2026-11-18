import { beforeEach, expect, it, vi } from 'vitest';
const saved: Record<string, unknown> = {};
let listener: (...args: any[]) => unknown;
const storage = { get: vi.fn(async () => saved), set: vi.fn(async (v) => Object.assign(saved, v)), setAccessLevel: vi.fn(async () => {}) };
vi.stubGlobal('chrome', { runtime: { id: 'extension-id', onMessage: { addListener: (fn: typeof listener) => { listener = fn; } } }, storage: { local: storage } });
const sender = { id: 'extension-id', tab: { id: 1 }, url: 'https://basketball.fantasysports.yahoo.com/nba/210163' };
beforeEach(async () => {
  vi.resetModules();
  for (const key of Object.keys(saved)) delete saved[key];
  vi.stubGlobal('fetch', vi.fn());
  await import('../src/background');
});
function request(): Promise<any> { return new Promise(resolve => listener({ type: 'GM_STATUS' }, sender, resolve)); }
it('rejects foreign senders and unsupported messages', () => {
  const reply = vi.fn();
  expect(listener({ type: 'GM_STATUS' }, { ...sender, id: 'other' }, reply)).toBe(false);
  expect(listener({ type: 'GM_STATUS' }, { ...sender, url: 'https://evil.test' }, reply)).toBe(false);
  expect(listener({ type: 'TRANSACTION' }, sender, reply)).toBe(false);
  expect(reply).not.toHaveBeenCalled();
});
it('handles unpaired/offline state without inventing data', async () => {
  const result = await request();
  expect(result.connection).toBe('Offline');
  expect(result.refreshed).toBe(null);
  expect(fetch).not.toHaveBeenCalled();
});
it('reads real mode and syncs changed configured league', async () => {
  saved.token = 'x'.repeat(40);
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ mode: 'real', setup: { league_url: 'https://basketball.fantasysports.yahoo.com/nba/42' }, connection: 'manual_import', freshness: 'STALE', last_successful_refresh: '2026-01-01T00:00:00Z' })));
  const result = await request();
  expect(result.leagueUrl).toContain('/42');
  expect(result.freshness).toBe('STALE');
  expect(result.refreshed).toBe('2026-01-01T00:00:00Z');
  expect(result.token).toBeUndefined();
  expect(vi.mocked(fetch).mock.calls[0][0]).toContain('mode=real');
});
it('rejects demo data returned for a real sidebar', async () => {
  saved.token = 'x'.repeat(40);
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ mode: 'demo', setup: { league_url: sender.url } })));
  expect((await request()).connection).toBe('Offline');
});
it('handles connection rejection', async () => {
  saved.token = 'x'.repeat(40);
  vi.mocked(fetch).mockResolvedValue(new Response('', { status: 401 }));
  expect((await request()).message).toContain('pairing token');
});
