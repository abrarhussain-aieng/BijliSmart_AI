(function () {
  const list = document.getElementById('messages'), input = document.getElementById('q'), sendBtn = document.getElementById('send');
  const SUGGESTIONS = [
  'Why is my bill high this month?',
  'How can I reduce my electricity bill?',
  'What tariff applies to my current consumption?',
  'How much can I save by reducing AC usage?',
  'Which appliance is consuming the most electricity?',
  'How many units did I use this month?',
  'Compare my current bill with my previous bill.',
  'What can I do to reduce my monthly units?',
  'What will happen if I reduce my daily usage by 2 hours?',
  'Give me a personalized plan to lower my electricity bill.'
];
  function add(role, html) {
    const el = document.createElement('div');
    el.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
    el.innerHTML = html;
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
    return el;
  }

  async function send(text) {
    const q = (text ?? input.value).trim();
    if (!q) return;
    input.value = '';
    sendBtn.disabled = true;
    add('user', esc(q));
    const pending = add('bot', 'Thinking…');
    try {
      const res = await askAssistant(q);
      pending.innerHTML = renderText(res.answer) + answerFooter(res);
    } catch (e) {
      pending.innerHTML = `<span style="color:#9f1239">${esc(e.message)}</span>`;
    }
    sendBtn.disabled = false;
    list.scrollTop = list.scrollHeight;
    input.focus();
  }

  const hello = add('bot', 'Hi! I am BijliSmart AI. I answer using your uploaded bills, your appliance estimates and the tariff knowledge base. Try one of these:<br>' + 
    SUGGESTIONS.map((s) => `<span class="chip" tabindex="0">${esc(s)}</span>`).join(''));
  hello.querySelectorAll('.chip').forEach((c) => {
    c.onclick = () => send(c.textContent);
    c.onkeydown = (e) => { if (e.key === 'Enter') send(c.textContent); };
  });
  sendBtn.onclick = () => send();
  input.onkeydown = (e) => { if (e.key === 'Enter') send(); };
})();
