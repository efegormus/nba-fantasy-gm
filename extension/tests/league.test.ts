import { describe, expect, it } from 'vitest';
import { DEFAULT_LEAGUE_URL, leagueId, matchesLeague } from '../src/league';
describe('Yahoo league matching', () => {
  it('matches the configured root and nested pages', () => {
    expect(matchesLeague(`${DEFAULT_LEAGUE_URL}/2?week=5`, DEFAULT_LEAGUE_URL)).toBe(true);
    expect(matchesLeague(DEFAULT_LEAGUE_URL, DEFAULT_LEAGUE_URL)).toBe(true);
    expect(matchesLeague('https://basketball.fantasysports.yahoo.com/nba/42/players', 'https://basketball.fantasysports.yahoo.com/nba/42')).toBe(true);
  });
  it('rejects other leagues and lookalike URLs', () => {
    for (const url of ['https://basketball.fantasysports.yahoo.com/nba/2101630', 'https://evil.test/nba/210163', 'https://basketball.fantasysports.yahoo.com.evil.test/nba/210163', 'https://x:y@basketball.fantasysports.yahoo.com/nba/210163', 'http://basketball.fantasysports.yahoo.com/nba/210163', 'garbage']) {
      expect(matchesLeague(url, DEFAULT_LEAGUE_URL)).toBe(false);
    }
    expect(leagueId('https://basketball.fantasysports.yahoo.com/nba/210163evil')).toBe(null);
  });
});
