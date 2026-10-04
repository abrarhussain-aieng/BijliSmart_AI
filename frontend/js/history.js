(async function () {
  const body = document.getElementById('history-body');
  try {
    const s = await api('/api/history/summary');
    if (!s.has_data) {
      body.innerHTML = '<div class="card empty"><b>No history yet</b>Upload bills to build your monthly history.<br><br><a class="btn" href="bills.html">Upload a bill</a></div>';
      return;
    }
    const c = s.comparison, h = s.history;
    const box = (title, units, amount, extra) => `<div class="card stat"><div class="sub">${title}</div><div class="big" style="font-size:26px">${fmtNum(units)} units</div><div><b>${fmtRs(amount)}</b> ${extra || ''}</div></div>`;
    body.innerHTML = `
      <section class="grid stats" style="grid-template-columns:repeat(3,1fr)">
        ${box('Current · ' + s.current.label, s.current.units, s.current.amount)}
        ${s.previous ? box('Previous · ' + s.previous.label, s.previous.units, s.previous.amount, c ? badge(c.unit_percentage_change) : '') : '<div class="card empty">No previous month yet</div>'}
        ${s.average_units != null ? box('Average of earlier months', s.average_units, s.average_amount, c ? badge(c.vs_average_percentage) : '') : '<div class="card empty">Average needs 2+ earlier bills</div>'}
      </section>
      ${c ? `<div class="card" style="margin-bottom:18px"><b>Change vs ${esc(c.previous_label)}:</b> ${fmtSigned(c.unit_change)} units (${c.unit_percentage_change == null ? '—' : fmtSigned(c.unit_percentage_change, 2) + '%'})${c.bill_change != null ? ` · bill ${c.bill_change >= 0 ? '+' : '−'}${fmtRs(Math.abs(c.bill_change))} (${fmtSigned(c.bill_percentage_change, 2)}%)` : ''}</div>` : ''}
      <section class="grid even">
        <div class="card"><h2>Units per month</h2><div class="chart-box sm"><canvas id="units"></canvas></div></div>
        <div class="card"><h2>Bill amount per month</h2><div class="chart-box sm"><canvas id="amount"></canvas></div></div>
      </section>
      <section class="card" style="margin-bottom:18px"><h2>Usage trend</h2><div class="chart-box"><canvas id="trend"></canvas></div></section>
      <section class="card"><h2>All months</h2><table><thead><tr><th>Month</th><th>Billing date</th><th class="num">Units</th><th class="num">Change</th><th class="num">Amount</th><th>Tariff</th></tr></thead><tbody>
        ${h.map((r, i) => `<tr><td>${r.label}</td><td>${fmtDate(r.billing_date)}</td><td class="num">${fmtNum(r.units)}</td><td class="num">${i && h[i - 1].units != null && r.units != null ? fmtSigned(r.units - h[i - 1].units) : '—'}</td><td class="num">${fmtRs(r.amount)}</td><td>${esc(r.tariff || '—')}</td></tr>`).reverse().join('')}
      </tbody></table></section>`;
    barChart('units', h.map((r) => r.label), h.map((r) => r.units), 'Units', '#2563eb');
    barChart('amount', h.map((r) => r.label), h.map((r) => r.amount), 'Amount (Rs.)', '#16a34a');
    trendChart('trend', h);
  } catch (e) {
    body.innerHTML = `<div class="card notice err">${esc(e.message)}</div>`;
  }
})();
