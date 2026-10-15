/**
 * FinLab — Main JS (Dark Theme / Canva Redesign)
 */

document.addEventListener('DOMContentLoaded', () => {
  initChatbot();
  initBankModal();
  initToastQueue();
});

// ==========================================================================
// Toast Notification
// ==========================================================================
function showToast(message, type = 'info') {
  // Remove existing
  const old = document.getElementById('finlab-toast');
  if (old) old.remove();

  const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', info: 'fa-circle-info' };
  const toast = document.createElement('div');
  toast.id = 'finlab-toast';
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
  document.body.appendChild(toast);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('show'));
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, 3200);
}

function initToastQueue() {
  // Make globally accessible
  window.showToast = showToast;
}

// ==========================================================================
// Chatbot
// ==========================================================================
function initChatbot() {
  const trigger    = document.getElementById('chatbot-trigger');
  const triggerTop = document.getElementById('chatbot-fab-top');
  const win        = document.getElementById('chat-window');
  const closeBtn   = document.getElementById('chat-close');
  const input      = document.getElementById('chat-input');
  const sendBtn    = document.getElementById('chat-send');
  const msgs       = document.getElementById('chat-messages');
  const chips      = document.querySelectorAll('.chip');

  if (!win) return;

  function toggleChat() {
    win.classList.toggle('open');
    if (win.classList.contains('open') && input) input.focus();
  }

  if (trigger)    trigger.addEventListener('click', toggleChat);
  if (triggerTop) triggerTop.addEventListener('click', toggleChat);
  if (closeBtn)   closeBtn.addEventListener('click', () => win.classList.remove('open'));

  chips.forEach(chip => {
    chip.addEventListener('click', () => sendMessage(chip.dataset.q || chip.textContent.trim()));
  });

  if (sendBtn) sendBtn.addEventListener('click', send);
  if (input) input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

  function send() {
    const text = input.value.trim();
    if (!text) return;
    sendMessage(text);
    input.value = '';
  }

  async function sendMessage(text) {
    appendMsg('user', text);
    scrollBottom();
    const typId = appendTyping();
    scrollBottom();

    try {
      const res  = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      removeTyping(typId);
      appendMsg('bot', data.reply || 'Xin lỗi, tôi chưa hiểu câu hỏi này!');
    } catch {
      removeTyping(typId);
      appendMsg('bot', 'Lỗi kết nối đến máy chủ AI. Vui lòng thử lại!');
    }
    scrollBottom();
  }

  function appendMsg(role, text) {
    const div = document.createElement('div');
    div.className = `msg msg-${role}`;
    div.innerHTML = formatText(text);
    msgs.appendChild(div);
  }

  function appendTyping() {
    const id = 'typ-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'msg msg-bot';
    div.style.cssText = 'display:flex;gap:5px;align-items:center;padding:10px 14px;';
    div.innerHTML = `
      <span style="width:7px;height:7px;background:rgba(255,255,255,0.3);border-radius:50%;animation:bounce 1.2s infinite 0.0s;"></span>
      <span style="width:7px;height:7px;background:rgba(255,255,255,0.3);border-radius:50%;animation:bounce 1.2s infinite 0.15s;"></span>
      <span style="width:7px;height:7px;background:rgba(255,255,255,0.3);border-radius:50%;animation:bounce 1.2s infinite 0.3s;"></span>`;
    msgs.appendChild(div);
    return id;
  }

  function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function scrollBottom() {
    setTimeout(() => { msgs.scrollTop = msgs.scrollHeight; }, 50);
  }

  function formatText(t) {
    if (!t) return '';
    return t
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')
      .replace(/\*(.*?)\*/g,'<em>$1</em>')
      .replace(/\n/g,'<br>');
  }
}

// ==========================================================================
// Open Banking Modal (Dashboard)
// ==========================================================================
function initBankModal() {
  const overlay   = document.getElementById('modal-bank');
  const syncBtn   = document.getElementById('btn-sync');
  const bankCards = document.querySelectorAll('.bank-choice');
  if (!overlay) return;

  let selectedBank = 'VCB';

  bankCards.forEach(card => {
    card.addEventListener('click', () => {
      bankCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedBank = card.dataset.bank;
    });
  });

  // Close on backdrop click
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });

  if (syncBtn) {
    syncBtn.addEventListener('click', async () => {
      syncBtn.disabled = true;
      syncBtn.innerHTML = '<span class="spinner"></span> Đang xác thực...';
      try {
        const res    = await fetch('/api/sync-bank', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bank_id: selectedBank })
        });
        const result = await res.json();
        overlay.classList.remove('open');
        if (result.success) {
          showToast(result.message || 'Đồng bộ thành công!', 'success');
          setTimeout(() => location.reload(), 1200);
        } else {
          showToast(result.message || 'Lỗi kết nối!', 'error');
        }
      } catch {
        showToast('Lỗi kết nối đến máy chủ!', 'error');
      } finally {
        syncBtn.disabled = false;
        syncBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Đồng bộ ngay';
      }
    });
  }
}
