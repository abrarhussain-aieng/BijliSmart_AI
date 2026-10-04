(function () {
  const drop = document.getElementById('drop'), input = document.getElementById('file'), status = document.getElementById('status');
  const FIELDS = [
    ['Billing month', (b) => monthLabel(b.billing_month)], ['Billing date', (b) => b.billing_date && fmtDate(b.billing_date)],
    ['Due date', (b) => b.due_date && fmtDate(b.due_date)], ['Consumer ID', (b) => b.consumer_id], ['Reference no.', (b) => b.reference_number],
    ['Meter no.', (b) => b.meter_number], ['Previous reading', (b) => b.previous_reading != null && fmtNum(b.previous_reading)],
    ['Current reading', (b) => b.current_reading != null && fmtNum(b.current_reading)], ['Units', (b) => b.units != null && fmtNum(b.units, 1)],
    ['Electricity charges', (b) => b.electricity_charges != null && fmtRs(b.electricity_charges)], ['Taxes', (b) => b.taxes != null && fmtRs(b.taxes)],
    ['FPA', (b) => b.fpa != null && fmtRs(b.fpa)], ['GST', (b) => b.gst != null && fmtRs(b.gst)],
    ['Other charges', (b) => b.other_charges != null && fmtRs(b.other_charges)], ['Tariff', (b) => b.tariff],
    ['Total amount', (b) => b.amount != null && fmtRs(b.amount)],
    ['Average cost per unit', (b) => b.amount && b.units && 'Rs. ' + (b.amount / b.units).toFixed(2)]
  ];

  drop.onclick = () => input.click();
  drop.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } };
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add('over'); };
  drop.ondragleave = () => drop.classList.remove('over');
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove('over'); if (e.dataTransfer.files[0]) handle(e.dataTransfer.files[0]); };
  input.onchange = () => { if (input.files[0]) handle(input.files[0]); input.value = ''; };

  async function handle(file) {
    status.innerHTML = '<div class="notice ok"><span class="spin" style="border-color:#166534;border-top-color:transparent"></span> Reading your bill and analysing it…</div>';
    try {
      const fd = new FormData();
      fd.append('file', file);
      const up = await api('/api/bills/upload', { method: 'POST', body: fd });
      await api(`/api/bills/${up.bill.id}/analyze`, { method: 'POST' });
      status.innerHTML = '<div class="notice ok">Bill saved and analysed.</div>' +
        up.warnings.map((w) => `<div class="notice warn">${esc(w)}</div>`).join('');
      await loadList();
      await showDetail(up.bill.id);
    } catch (e) {
      status.innerHTML = `<div class="notice err">${esc(e.message)}</div>`;
    }
  }

  async function loadList() {
    const el = document.getElementById('bill-list');
    try {
      const bills = await api('/api/bills');
      el.innerHTML = bills.length
        ? `<table><thead><tr><th>Month</th><th class="num">Units</th><th class="num">Amount</th></tr></thead><tbody>${bills.map((b) =>
            `<tr class="clickable" data-id="${b.id}"><td>${monthLabel(b.billing_month)}</td><td class="num">${fmtNum(b.units)}</td><td class="num">${fmtRs(b.amount)}</td></tr>`).join('')}</tbody></table>`
        : '<div class="empty"><b>No bills yet</b>Upload your first bill above.</div>';
      el.querySelectorAll('tr.clickable').forEach((tr) => { tr.onclick = () => showDetail(tr.dataset.id); });
      return bills;
    } catch (e) { el.innerHTML = `<div class="notice err">${esc(e.message)}</div>`; return []; }
  }

  async function showDetail(id) {
    const el = document.getElementById('bill-detail');
    try {
      const b = await api(`/api/bills/${id}`);
      const a = b.analysis || {};
      const rows = FIELDS.map(([k, f]) => [k, f(b)]).filter(([, v]) => v);
      el.innerHTML = `<div class="kv" style="grid-template-columns:1fr">${rows.map(([k, v]) => `<div><span>${k}</span><b>${esc(v)}</b></div>`).join('')}</div>
        ${(a.insights || []).map((i) => `<div class="insight" style="margin-top:12px"><div><b>${esc(i.title)}</b><span>${esc(i.text)}</span></div></div>`).join('')}
        ${b.recommendations.length ? `<h2 style="margin-top:16px;font-size:15px">Recommendations <small>(estimates)</small></h2><ul class="checks">${b.recommendations.map((r) => `<li>${icon('check')}<span><b>${esc(r.title)}</b><br><span class="sub">${esc(r.detail)}</span></span></li>`).join('')}</ul>` : ''}
        ${(a.warnings || []).map((w) => `<div class="notice warn">${esc(w)}</div>`).join('')}`;
    } catch (e) { el.innerHTML = `<div class="notice err">${esc(e.message)}</div>`; }
  }

  loadList().then((bills) => { if (bills.length) showDetail(bills[0].id); });
})();
