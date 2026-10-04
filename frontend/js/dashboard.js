(async function () {
  const content = document.getElementById('content');
  content.innerHTML = '<div class="card empty">Loading your data…</div>';
  try {
    const bills = await api('/api/bills');
    if (!bills.length) {
      content.innerHTML = `<div class="card empty"><b>No bills yet</b>Upload your first electricity bill to see your usage, trends and savings.<br><br><a class="btn" href="bills.html">Upload a bill</a></div>`;
      return;
    }
    const latestId = bills[0].id;
    let detail = await api(`/api/bills/${latestId}`);
    if (!detail.analysis) {
      await api(`/api/bills/${latestId}/analyze`, { method: 'POST' });
      detail = await api(`/api/bills/${latestId}`);
    }
    const [summary, appliances] = await Promise.all([api('/api/history/summary'), api('/api/appliances')]);
    render(bills, detail, summary, appliances);
  } catch (e) {
    content.innerHTML = `<div class="card notice err">${esc(e.message)}</div>`;
  }

  function render(bills, detail, summary, appl) {
    const comp = summary.comparison, prev = summary.previous, cur = summary.current;
    const analysis = detail.analysis || {};
    const recs = detail.recommendations || [];
    const saveKwh = analysis.estimated_monthly_savings_kwh, saveCost = analysis.estimated_monthly_savings_cost;
    const toneIcon = { bad: ['red', 'up'], good: ['green', 'down'], info: ['blue', 'info'] };

    const insights = (analysis.insights || []).map((i) => {
      const [c, ic] = toneIcon[i.tone] || toneIcon.info;
      return `<div class="insight"><div class="ico ${c}">${icon(ic)}</div><div><b>${esc(i.title)}</b><span>${esc(i.text)}</span></div></div>`;
    }).join('') || '<div class="sub">No insights yet.</div>';

    const applianceCard = appl.items.length ? `
      <div class="donut-wrap">
        <div class="donut"><canvas id="donut"></canvas><div class="center">Total<b>${fmtNum(appl.total_kwh, 0)} kWh</b></div></div>
        <div class="legend">${donutLegend(appl.items.slice(0, 6))}</div>
      </div>` : `<div class="empty">Add your appliances to see an estimate.<br><br><a class="btn ghost" href="appliances.html">Add appliances</a></div>`;

    const compareCard = prev ? `
      <div class="cmp">
        <div><small>Previous Bill · ${esc(prev.label)}</small><strong>${fmtNum(prev.units)} units</strong><strong>${fmtRs(prev.amount)}</strong></div>
        <div><small>Current Bill · ${esc(cur.label)}</small><strong>${fmtNum(cur.units)} units</strong><strong>${fmtRs(cur.amount)}</strong></div>
      </div>
      ${comp ? `<div class="alert ${comp.unit_change > 0 ? 'up' : comp.unit_change < 0 ? 'down' : 'flat'}">${comp.unit_change > 0 ? 'Increase' : comp.unit_change < 0 ? 'Decrease' : 'No change'}:
        ${fmtSigned(comp.unit_change)} units${comp.bill_change != null ? ` · ${comp.bill_change >= 0 ? '+' : '−'}${fmtRs(Math.abs(comp.bill_change))}` : ''}</div>` : ''}`
      : '<div class="empty">Upload a previous month’s bill to compare.</div>';

    const planCard = `
      <div class="saving"><small class="sub">Estimated savings</small>
        <b>${saveCost ? fmtRs(saveCost) + ' / month' : '—'}</b>
        <span class="sub">${saveKwh ? `≈ ${fmtNum(saveKwh)} kWh/month, based on the values you entered` : 'Enter your appliances to see estimates'}</span></div>
      <ul class="checks">${recs.map((r) => `<li>${icon('check')}<span>${esc(r.title)}</span></li>`).join('')}</ul>
      ${analysis.recommendation_summary ? `<p class="sub" style="margin-top:10px">${esc(analysis.recommendation_summary)}</p>` : ''}`;

    document.getElementById('content').innerHTML = `
      <section class="grid stats">
        <div class="card stat"><div class="head"><div class="ico blue">${icon('bolt')}</div>Current Bill Amount</div>
          <div class="big">${fmtRs(detail.amount)}</div><div>${badge(comp && comp.bill_percentage_change)} <span class="sub">${comp ? 'vs last month' : 'first bill'}</span></div></div>
        <div class="card stat"><div class="head"><div class="ico green">${icon('chart')}</div>Units Consumed</div>
          <div class="big">${fmtNum(detail.units)}</div><div>${badge(comp && comp.unit_percentage_change)} <span class="sub">${prev ? 'Previous: ' + fmtNum(prev.units) + ' units' : 'vs last month'}</span></div></div>
        <div class="card stat"><div class="head"><div class="ico violet">${icon('calendar')}</div>Billing Period</div>
          <div class="big" style="font-size:26px">${monthLabel(detail.billing_month)}</div>
          <div class="sub">Due: ${fmtDate(detail.due_date)}${detail.previous_reading != null ? `<br>Reading: ${fmtNum(detail.previous_reading)} → ${fmtNum(detail.current_reading)}` : ''}</div></div>
        <div class="card stat"><div class="head"><div class="ico teal">${icon('leaf')}</div>Estimated Monthly Savings</div>
          <div class="big" style="font-size:26px">${saveCost ? fmtRs(saveCost) : '—'}</div>
          <div class="sub">${saveKwh ? '≈ ' + fmtNum(saveKwh) + ' kWh/month (estimate)' : 'Add appliances for an estimate'}</div></div>
      </section>
      <section class="grid two">
        <div class="card"><h2>Consumption Trend</h2><div class="chart-box"><canvas id="trend"></canvas></div></div>
        <div class="card"><h2>${icon('bulb')} Quick Insights</h2>${insights}</div>
      </section>
      <section class="grid three">
        <div class="card"><h2>Appliance-wise Energy Usage <small>(Estimated)</small></h2>${applianceCard}</div>
        <div class="card"><h2>Bill Comparison</h2>${compareCard}</div>
        <div class="card"><h2>${icon('leaf')} AI Saving Plan</h2>${planCard}</div>
      </section>
      <section class="grid two-b">
        <div class="card"><h2>Recent Bills</h2>
          <table><thead><tr><th>Month</th><th class="num">Units</th><th class="num">Bill Amount</th></tr></thead><tbody>
          ${bills.slice(0, 5).map((b, i) => `<tr><td>${monthLabel(b.billing_month)}${i === 0 ? ' (Current)' : ''}</td><td class="num"><b>${fmtNum(b.units)}</b></td><td class="num"><b>${fmtRs(b.amount)}</b></td></tr>`).join('')}
          </tbody></table><p style="margin-top:12px"><a href="bills.html">View all bills</a></p></div>
        <div class="card mini-chat"><h2>Ask BijliSmart AI</h2>
          <div id="mini-answer" class="sub">Ask why your bill changed or how to reduce it.</div>
          <div class="composer"><input id="mini-q" placeholder="Ask BijliSmart AI..." maxlength="1000"><button class="btn" id="mini-send" aria-label="Send">${icon('send')}</button></div>
          <p style="margin-top:10px"><a href="assistant.html">Open full assistant</a></p></div>
      </section>`;

    if (summary.history.length) trendChart('trend', summary.history);
    if (appl.items.length) donutChart('donut', appl.items.slice(0, 6).map((a) => a.name), appl.items.slice(0, 6).map((a) => a.monthly_kwh));

    const send = async () => {
      const input = document.getElementById('mini-q'), out = document.getElementById('mini-answer'), q = input.value.trim();
      if (!q) return;
      input.value = '';
      out.innerHTML = `<div class="msg user">${esc(q)}</div><div class="msg bot">Thinking…</div>`;
      try {
        const res = await askAssistant(q);
        out.innerHTML = `<div class="msg user">${esc(q)}</div><div class="msg bot">${renderText(res.answer)}${answerFooter(res)}</div>`;
      } catch (e) { out.innerHTML = `<div class="notice err">${esc(e.message)}</div>`; }
    };
    document.getElementById('mini-send').onclick = send;
    document.getElementById('mini-q').onkeydown = (e) => { if (e.key === 'Enter') send(); };
  }
})();
