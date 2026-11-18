import React from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { matchesLeague, type SidebarStatus } from './league';
let host: HTMLDivElement | null = null;
let root: Root | null = null;
let dismissed = false;
function unmount() { root?.unmount(); root = null; host?.remove(); host = null; }
function Sidebar({ status }: { status: SidebarStatus }) {
  return <aside aria-label="Fantasy NBA GM" style={{ font: '14px/1.6 system-ui', color: '#eef3fa', background: '#122039', padding: 22, width: 280, borderRadius: 16, boxShadow: '0 8px 40px #0005' }}>
    <button aria-label="Close Fantasy GM" style={{ float: 'right' }} onClick={() => { dismissed = true; unmount(); }}>×</button>
    <strong style={{ fontSize: 20 }}>Fantasy NBA GM</strong>
    <p>REAL LEAGUE · Manual data</p>
    <p>Connection: {status.connection}<br/>Freshness: {status.freshness}</p>
    <p>Last successful refresh: {status.refreshed ? new Date(status.refreshed).toLocaleString() : 'Never'}</p>
    <p>{status.message}</p>
    <a href="http://127.0.0.1:8501" target="_blank" rel="noreferrer" style={{ color: '#7dd3fc' }}>Open League Setup ↗</a>
    <p style={{ fontSize: 12 }}>Read-only companion. Perform any roster moves yourself in Yahoo.</p>
  </aside>;
}
async function refresh() {
  if (dismissed) return;
  try {
    const status = await chrome.runtime.sendMessage({ type: 'GM_STATUS' }) as SidebarStatus | null;
    if (!status || !matchesLeague(location.href, status.leagueUrl)) { unmount(); return; }
    if (!host) {
      host = document.createElement('div');
      host.style.cssText = 'position:fixed;right:16px;top:80px;z-index:2147483647;max-height:85vh;overflow:auto';
      const shadow = host.attachShadow({ mode: 'closed' });
      const mount = document.createElement('div'); shadow.append(mount); document.body.append(host);
      root = createRoot(mount);
    }
    root?.render(<Sidebar status={status}/>);
  } catch { unmount(); }
}
void refresh();
const timer = setInterval(() => void refresh(), 15000);
window.addEventListener('pagehide', () => { clearInterval(timer); unmount(); }, { once: true });
