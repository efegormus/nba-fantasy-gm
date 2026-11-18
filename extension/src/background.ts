import { DEFAULT_LEAGUE_URL, leagueId, type SidebarStatus } from './league';
void chrome.storage.local.setAccessLevel({ accessLevel: 'TRUSTED_CONTEXTS' });
chrome.runtime.onMessage.addListener((message: unknown, sender, sendResponse) => {
  if (sender.id !== chrome.runtime.id || !sender.tab || !sender.url || !leagueId(sender.url) ||
      !message || typeof message !== 'object' || !('type' in message) || message.type !== 'GM_STATUS') return false;
  async function status(): Promise<SidebarStatus> {
    const saved = await chrome.storage.local.get(['token', 'leagueUrl']);
    const fallback = { leagueUrl: typeof saved.leagueUrl === 'string' ? saved.leagueUrl : DEFAULT_LEAGUE_URL,
      connection: 'Offline', freshness: 'UNAVAILABLE', refreshed: null,
      message: 'Start the local backend and pair this extension in its Options page.' };
    if (typeof saved.token !== 'string' || saved.token.length < 32) return fallback;
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/league?mode=real', {
        headers: { Authorization: `Bearer ${saved.token}` }, signal: AbortSignal.timeout(5000), credentials: 'omit'
      });
      if (!response.ok) throw new Error('Local connection rejected. Check the pairing token and allowed extension origin.');
      const data = await response.json();
      if (data.mode !== 'real' || !leagueId(data.setup?.league_url)) throw new Error('Invalid backend response.');
      await chrome.storage.local.set({ leagueUrl: data.setup.league_url });
      return { leagueUrl: data.setup.league_url, connection: data.connection,
        freshness: data.freshness, refreshed: data.last_successful_refresh,
        message: 'Use League Setup to import rosters and select your team. Decision engines are not yet available.' };
    } catch (error) {
      return { ...fallback, message: error instanceof Error ? error.message : 'Backend unavailable' };
    }
  }
  void status().then(sendResponse).catch(() => sendResponse(null));
  return true;
});
