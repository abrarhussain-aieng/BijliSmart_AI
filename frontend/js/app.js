/* Shared helpers: API client, formatting, charts and the page shell. */
const ICONS = {
  bolt: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>',
  chart: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  plug: '<path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8z"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  send: '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
  up: '<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>',
  down: '<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>',
  bulb: '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2z"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
  leaf: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>'
};
const NAV = [
  ['index.html', 'Dashboard', 'home'], ['bills.html', 'Bills', 'file'], ['history.html', 'History', 'chart'],
  ['appliances.html', 'Appliances', 'plug'], ['assistant.html', 'AI Assistant', 'chat']
];
const PALETTE = ['#2563eb', '#16a34a', '#f97316', '#eab308', '#8b5cf6', '#94a3b8', '#06b6d4', '#ec4899'];

const icon = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[n]}</svg>`;
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtRs = (n) => (n == null ? '—' : 'Rs. ' + Number(n).toLocaleString('en-PK', { maximumFractionDigits: 0 }));
const fmtNum = (n, d = 0) => (n == null ? '—' : Number(n).toLocaleString('en-PK', { maximumFractionDigits: d }));
const fmtSigned = (n, d = 0) => (n == null ? '—' : (n > 0 ? '+' : '') + fmtNum(n, d));
const fmtDate = (s) => (s ? new Date(s + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—');
function monthLabel(m) {
  const [y, mo] = (m || '').split('-');
  return y && mo ? new Date(+y, +mo - 1, 1).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' }) : '—';
}
function badge(pct) {
  if (pct == null) return '';
  const cls = pct > 0.05 ? 'up' : pct < -0.05 ? 'down' : 'flat';
  const ic = cls === 'up' ? icon('up') : cls === 'down' ? icon('down') : '';
  return `<span class="badge ${cls}">${ic}${Math.abs(pct).toFixed(pct % 1 ? 1 : 0)}%</span>`;
}
function renderText(text) {
  return esc(text)
    .replace(/^\[([^\]]+)\]\s*$/gm, '<b>$1</b>')   // [Heading] alone on a line → bold
    .replace(/\[([^\]]+)\]/g, '$1')                  // remaining [text] inline → plain, no brackets
    .replace(/^###\s+(.+)$/gm, '<b>$1</b>')          // ### Heading → bold
    .replace(/^##\s+(.+)$/gm, '<b>$1</b>')           // ## Heading → bold
    .replace(/^#\s+(.+)$/gm, '<b>$1</b>')            // # Heading → bold
    .replace(/^---+$/gm, '')                          // --- divider → remove
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');         // **bold** → <b>
}
function toast(message, isError = false) {
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' err' : '');
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    let msg = data && data.detail;
    if (Array.isArray(msg)) msg = msg.map((d) => d.msg).join('; ');
    throw new Error(msg || `Request failed (${res.status})`);
  }
  return data;
}
const postJSON = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

/* ---------- charts (Chart.js) ---------- */
const charts = {};
function mountChart(id, config) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), config);
}
function trendChart(id, history) {
  mountChart(id, {
    type: 'line',
    data: {
      labels: history.map((h) => h.label),
      datasets: [
        { label: 'Units Consumed', data: history.map((h) => h.units), borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,.10)', fill: true, tension: .35, yAxisID: 'y', pointRadius: 4 },
        { label: 'Bill Amount (Rs.)', data: history.map((h) => h.amount), borderColor: '#16a34a', tension: .35, yAxisID: 'y1', pointRadius: 4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      scales: {
        y: { beginAtZero: true, title: { display: true, text: 'Units' } },
        y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Bill Amount (Rs.)' } }
      },
      plugins: { legend: { position: 'top', align: 'end' } }
    }
  });
}
function barChart(id, labels, data, label, color) {
  mountChart(id, {
    type: 'bar',
    data: { labels, datasets: [{ label, data, backgroundColor: color, borderRadius: 6 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } }
  });
}
function donutChart(id, labels, data) {
  mountChart(id, {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: PALETTE, borderWidth: 2, borderColor: '#fff' }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { display: false } } }
  });
}
function donutLegend(items) {
  return items.map((a, i) => `<div><i style="background:${PALETTE[i % PALETTE.length]}"></i>${esc(a.name)}<span>${fmtNum(a.monthly_kwh, 0)} kWh</span><b>${a.percentage.toFixed(0)}%</b></div>`).join('');
}

/* ---------- assistant helper shared by the dashboard card and chat page ---------- */
const TOOL_LABELS = {
  analyze_bill: 'current bill', analyze_history: 'bill history', analyze_consumption: 'consumption analysis',
  retrieve_tariff: 'tariff knowledge', analyze_appliances: 'appliance estimates', generate_recommendations: 'recommendations'
};
const askAssistant = (message) => postJSON('/api/assistant/chat', { message });
function answerFooter(res) {
  const parts = [];
  if (res.tools_used && res.tools_used.length) parts.push('Used: ' + res.tools_used.map((t) => TOOL_LABELS[t] || t).join(', '));
  if (res.sources && res.sources.length) parts.push('Sources: ' + res.sources.map((s) => esc(s.source)).join(', '));
  return parts.length ? `<small>${parts.join(' · ')}</small>` : '';
}

/* ---------- page shell ---------- */
function buildShell() {
  const page = document.body.dataset.page;
  const hour = new Date().getHours();
  const greet = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  const title = page === 'index.html' ? `${greet}! 👋` : document.body.dataset.title;
  document.getElementById('sidebar').innerHTML = `
    <div class="brand">${icon('bolt')}<div><b>BijliSmart <span>AI</span></b><small>Smarter Energy. Brighter Future.</small></div></div>
    <nav class="nav">${NAV.map(([href, label, ic]) => `<a href="${href}" class="${href === page ? 'active' : ''}">${icon(ic)}${label}</a>`).join('')}</nav>
    <div class="side-note"><b>Save Energy, Save Pakistan</b>Small changes in your usage can make a big difference.</div>`;
  document.getElementById('topbar').innerHTML = `<h1>${title}</h1><p>${esc(document.body.dataset.sub || '')}</p>`;
}
buildShell();
