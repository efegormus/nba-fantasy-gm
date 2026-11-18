export const DEFAULT_LEAGUE_URL = 'https://basketball.fantasysports.yahoo.com/nba/210163';
export function leagueId(url: string): string | null {
  try {
    const value = new URL(url);
    if (value.origin !== 'https://basketball.fantasysports.yahoo.com' || value.username || value.password) return null;
    return /^\/nba\/([1-9][0-9]*)(?:\/|$)/.exec(value.pathname)?.[1] ?? null;
  } catch { return null; }
}
export function matchesLeague(page: string, configured: string): boolean {
  const id = leagueId(configured);
  return id !== null && leagueId(page) === id;
}
export interface SidebarStatus {
  leagueUrl: string;
  connection: string;
  freshness: string;
  refreshed: string | null;
  message: string;
}
