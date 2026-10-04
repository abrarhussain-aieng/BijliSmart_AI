(function () {
  const $ = (id) => document.getElementById(id);
  const msg = $('form-msg');

  async function load() {
    try {
      const d = await api('/api/appliances');
      $('appliance-table').innerHTML = d.items.length
        ? `<table><thead><tr><th>Appliance</th><th class="num">Hours/day</th><th class="num">Est. kWh</th><th class="num">Est. cost</th><th class="num">Share</th><th></th></tr></thead><tbody>
          ${d.items.map((a) => `<tr><td>${esc(a.name)}<br><span class="sub">${fmtNum(a.power_watts)} W × ${a.quantity} · ${a.days_per_month} days</span></td><td class="num">${fmtNum(a.hours_per_day, 1)}</td><td class="num">${fmtNum(a.monthly_kwh, 1)}</td><td class="num">${fmtRs(a.estimated_cost)}</td><td class="num">${a.percentage.toFixed(0)}%</td>
          <td class="num"><button class="btn icon" data-id="${a.id}" aria-label="Remove ${esc(a.name)}">${icon('trash')}</button></td></tr>`).join('')}
          </tbody><tfoot><tr><td><b>Total</b></td><td></td><td class="num"><b>${fmtNum(d.total_kwh, 1)}</b></td><td class="num"><b>${fmtRs(d.total_cost)}</b></td><td></td><td></td></tr></tfoot></table>
          <p class="sub" style="margin-top:12px">${esc(d.note)}${d.effective_rate ? ` Rate used: Rs. ${d.effective_rate.toFixed(2)}/unit.` : ' Upload a bill to enable cost estimates.'}</p>`
        : '<div class="empty"><b>No appliances yet</b>Add an appliance above to estimate its usage.</div>';
      $('appliance-table').querySelectorAll('button[data-id]').forEach((b) => { b.onclick = () => remove(b.dataset.id); });
      $('appliance-donut').innerHTML = d.items.length
        ? `<div class="donut-wrap"><div class="donut"><canvas id="donut"></canvas><div class="center">Total<b>${fmtNum(d.total_kwh, 0)} kWh</b></div></div><div class="legend">${donutLegend(d.items.slice(0, 8))}</div></div>`
        : '<div class="empty">Nothing to show yet.</div>';
      if (d.items.length) donutChart('donut', d.items.slice(0, 8).map((a) => a.name), d.items.slice(0, 8).map((a) => a.monthly_kwh));
    } catch (e) { $('appliance-table').innerHTML = `<div class="notice err">${esc(e.message)}</div>`; }
  }

  function refreshAnalysis() { // keep stored recommendations in sync; runs in the background
    api('/api/bills').then((b) => { if (b.length) api(`/api/bills/${b[0].id}/analyze`, { method: 'POST' }).catch(() => {}); }).catch(() => {});
  }

  async function add() {
    const body = {
      name: $('a-name').value.trim(), power_watts: parseFloat($('a-watts').value), quantity: parseInt($('a-qty').value, 10),
      hours_per_day: parseFloat($('a-hours').value), days_per_month: parseInt($('a-days').value, 10)
    };
    if (!body.name || [body.power_watts, body.quantity, body.hours_per_day, body.days_per_month].some(Number.isNaN)) {
      msg.innerHTML = '<div class="notice err">Fill in every field with valid numbers.</div>';
      return;
    }
    try {
      await postJSON('/api/appliances', body);
      msg.innerHTML = '';
      ['a-name', 'a-watts', 'a-hours'].forEach((id) => { $(id).value = ''; });
      await load();
      refreshAnalysis();
    } catch (e) { msg.innerHTML = `<div class="notice err">${esc(e.message)}</div>`; }
  }

  async function remove(id) {
    try { await api(`/api/appliances/${id}`, { method: 'DELETE' }); await load(); refreshAnalysis(); }
    catch (e) { toast(e.message, true); }
  }

  $('a-add').onclick = add;
  document.querySelectorAll('#appliance-form input').forEach((i) => { i.onkeydown = (e) => { if (e.key === 'Enter') add(); }; });
  load();
})();
