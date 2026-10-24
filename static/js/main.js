/**
 * FinLab — Main JS (Mobile App & Client Logic)
 */

document.addEventListener('DOMContentLoaded', () => {
  initChatbot();
  initBankModal();
  initToastQueue();
});

// ==========================================================================
// Modal Utility Functions (Global)
// ==========================================================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
}

document.addEventListener('click', (e) => {
  if (e.target.classList && e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// ==========================================================================
// Toast & Realistic Bank Push Notification
// ==========================================================================
function escapeHtmlMain(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let bankPushTimer = null;

function playBankChime() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    if (ctx.state === 'suspended') {
      ctx.resume();
    }
    const now = ctx.currentTime;
    
    // Nốt thứ nhất (G6 - 1567.98 Hz)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(1567.98, now);
    gain1.gain.setValueAtTime(0.2, now);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
    osc1.connect(gain1);
    gain1.connect(ctx.destination);
    osc1.start(now);
    osc1.stop(now + 0.35);

    // Nốt thứ hai chuông ngân cao (B6 - 1975.53 Hz)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(1975.53, now + 0.12);
    gain2.gain.setValueAtTime(0.25, now + 0.12);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.65);
    osc2.connect(gain2);
    gain2.connect(ctx.destination);
    osc2.start(now + 0.12);
    osc2.stop(now + 0.65);
  } catch(e) {
    console.warn('Audio chime unsupported or blocked:', e);
  }
}

function triggerBankPushNotification(opts) {
  opts = opts || {};
  const bank = opts.bank || 'MB Bank';
  const type = (opts.type || 'OUTFLOW').toUpperCase();
  const amount = typeof opts.amount === 'number' ? opts.amount : parseFloat(String(opts.amount || 45000).replace(/[^\d]/g, ''));
  const desc = opts.description || 'Chi tiêu qua ngân hàng';
  const balance = opts.balance;
  const account = opts.account || '•••• 4321';
  const aiCategory = opts.aiCategory || 'Ăn uống & Cà phê';
  const aiBucket = opts.aiBucket || '30% Nhu cầu linh hoạt';

  const banner = document.getElementById('bank-push-banner');
  if (!banner) return;

  // 1. Play realistic bank chime audio & vibrate
  playBankChime();
  if (navigator.vibrate) {
    try { navigator.vibrate([100, 50, 100]); } catch(e){}
  }

  // 2. Shake all visible bell icons
  document.querySelectorAll('.fa-bell').forEach(bell => {
    bell.classList.add('fa-shake');
    setTimeout(() => bell.classList.remove('fa-shake'), 2500);
  });

  // 3. Bank branding styles & icons
  const bankLower = bank.toLowerCase();
  let bankIcon = 'fa-building-columns';
  let glowColor = 'linear-gradient(90deg, #1D4ED8, #3B82F6, #60A5FA)';
  let iconBg = 'rgba(59, 130, 246, 0.35)';

  if (bankLower.includes('vietcom') || bankLower.includes('vcb')) {
    bankIcon = 'fa-building-columns';
    glowColor = 'linear-gradient(90deg, #059669, #10B981, #34D399)';
    iconBg = 'rgba(16, 185, 129, 0.35)';
  } else if (bankLower.includes('techcom') || bankLower.includes('tcb')) {
    bankIcon = 'fa-building-columns';
    glowColor = 'linear-gradient(90deg, #DC2626, #EF4444, #E8632A)';
    iconBg = 'rgba(239, 68, 68, 0.35)';
  } else if (bankLower.includes('momo')) {
    bankIcon = 'fa-mobile-screen-button';
    glowColor = 'linear-gradient(90deg, #A50064, #D81B60, #FF4081)';
    iconBg = 'rgba(216, 27, 96, 0.35)';
  }

  const glowEl = document.getElementById('bpn-accent-glow');
  if (glowEl) glowEl.style.background = glowColor;

  const iconEl = document.getElementById('bpn-bank-icon');
  if (iconEl) {
    iconEl.innerHTML = `<i class="fa-solid ${bankIcon}"></i>`;
    iconEl.style.background = iconBg;
  }

  const nameEl = document.getElementById('bpn-bank-name');
  if (nameEl) nameEl.textContent = bank.toUpperCase();

  const accEl = document.getElementById('bpn-account');
  if (accEl) accEl.textContent = `TK: ${account}`;

  const amtEl = document.getElementById('bpn-amount');
  if (amtEl) {
    amtEl.textContent = (type === 'INFLOW' ? '+' : '-') + amount.toLocaleString('vi-VN') + ' VND';
    amtEl.className = `bpn-amount ${type === 'INFLOW' ? 'inflow' : 'outflow'}`;
  }

  const nowTime = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
  const detEl = document.getElementById('bpn-details');
  if (detEl) {
    let balStr = '';
    if (balance !== undefined && balance !== null) {
      balStr = `Số dư: <strong>${Math.round(balance).toLocaleString('vi-VN')} VND</strong>. `;
    }
    detEl.innerHTML = `Lúc ${nowTime}. ${balStr}ND: ${escapeHtmlMain(desc)}`;
  }

  const aiEl = document.getElementById('bpn-ai-text');
  if (aiEl) {
    aiEl.innerHTML = `FinLab AI: <strong>${escapeHtmlMain(aiCategory)}</strong> &bull; ${escapeHtmlMain(aiBucket)}`;
  }

  // 4. Slide in animation
  if (bankPushTimer) clearTimeout(bankPushTimer);
  banner.classList.add('show');

  // Auto dismiss after 6.5s
  bankPushTimer = setTimeout(() => {
    banner.classList.remove('show');
  }, 6500);
}

function dismissBankPushBanner() {
  const banner = document.getElementById('bank-push-banner');
  if (banner) banner.classList.remove('show');
  if (bankPushTimer) clearTimeout(bankPushTimer);
}

function showToast(message, type = 'info') {
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
  window.showToast = showToast;
  window.triggerBankPushNotification = triggerBankPushNotification;
  window.dismissBankPushBanner = dismissBankPushBanner;
  window.playBankChime = playBankChime;
  window.openModal = openModal;
  window.closeModal = closeModal;
}
initToastQueue();

// ==========================================================================
// Chatbot
// ==========================================================================
function initChatbot() {
  const triggerTop = document.getElementById('chatbot-fab-top');
  const triggerGlobal = document.getElementById('chatbot-global-fab');
  
  if (triggerTop) {
    triggerTop.addEventListener('click', (e) => {
      e.preventDefault();
      if (typeof window.toggleInAppChat === 'function') {
        window.toggleInAppChat();
      }
    });
  }
  if (triggerGlobal) {
    triggerGlobal.addEventListener('click', (e) => {
      e.preventDefault();
      if (typeof window.toggleInAppChat === 'function') {
        window.toggleInAppChat();
      }
    });
  }
}

// ==========================================================================
// Open Banking Modal (Dashboard Helper)
// ==========================================================================
function initBankModal() {
  const overlay = document.getElementById('modal-bank');
  const bankCards = document.querySelectorAll('.bank-choice');
  if (!overlay) return;

  bankCards.forEach(card => {
    card.addEventListener('click', () => {
      bankCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
    });
  });

  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
}

// ==========================================================================
// Demo Webhook & AI Phân Loại Simulation Controller
// ==========================================================================
let lastSimPushData = null;

function openSimulateTxnModal(preferredBank) {
  const modal = document.getElementById('modal-simulate-txn');
  if (!modal) return;
  const bankSelect = document.getElementById('sim-bank-select');
  if (bankSelect && preferredBank) {
    const pBankLower = preferredBank.toLowerCase();
    for (let i = 0; i < bankSelect.options.length; i++) {
      if (pBankLower.includes(bankSelect.options[i].value.toLowerCase()) || 
          bankSelect.options[i].value.toLowerCase().includes(pBankLower)) {
        bankSelect.selectedIndex = i;
        break;
      }
    }
  }
  const resBox = document.getElementById('sim-result-box');
  if (resBox) resBox.style.display = 'none';
  modal.classList.add('open');
}

function closeSimulateTxnModal() {
  const modal = document.getElementById('modal-simulate-txn');
  if (modal) modal.classList.remove('open');
}

function applySimPreset(bank, desc, amount, type) {
  const bankSelect = document.getElementById('sim-bank-select');
  if (bankSelect) {
    for (let i = 0; i < bankSelect.options.length; i++) {
      if (bank.toLowerCase().includes(bankSelect.options[i].value.toLowerCase()) || 
          bankSelect.options[i].value.toLowerCase().includes(bank.toLowerCase())) {
        bankSelect.selectedIndex = i;
        break;
      }
    }
  }
  const descInput = document.getElementById('sim-desc-input');
  if (descInput) descInput.value = desc;

  const amtInput = document.getElementById('sim-amount-input');
  if (amtInput) amtInput.value = amount.toLocaleString('vi-VN');

  const typeSelect = document.getElementById('sim-type-select');
  if (typeSelect) typeSelect.value = type || 'OUTFLOW';

  const resBox = document.getElementById('sim-result-box');
  if (resBox) resBox.style.display = 'none';

  if (window.showToast) window.showToast(`Đã nạp kịch bản: ${desc} (${amount.toLocaleString('vi-VN')}đ)`, 'info');
}

async function submitSimulateTxn() {
  const bankSelect = document.getElementById('sim-bank-select');
  const typeSelect = document.getElementById('sim-type-select');
  const amtInput   = document.getElementById('sim-amount-input');
  const descInput  = document.getElementById('sim-desc-input');
  const btnTrigger = document.getElementById('btn-trigger-simulate');

  const bank = bankSelect ? bankSelect.value : 'MB Bank';
  const type = typeSelect ? typeSelect.value : 'OUTFLOW';
  const desc = descInput && descInput.value.trim() ? descInput.value.trim() : 'Chi tiêu qua ngân hàng';
  const amtRaw = amtInput ? amtInput.value.replace(/[^\d]/g, '') : '45000';
  const amount = parseInt(amtRaw, 10) || 45000;

  if (btnTrigger) {
    btnTrigger.disabled = true;
    btnTrigger.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xử lý...';
  }

  try {
    const res = await fetch('/api/open-banking/simulate-transaction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bank: bank,
        amount: amount,
        type: type,
        description: desc
      })
    });
    const data = await res.json();
    if (data.status === 'success' || data.success) {
      const resBox = document.getElementById('sim-result-box');
      if (resBox) {
        const refEl = document.getElementById('sim-res-ref');
        if (refEl) refEl.textContent = data.transaction ? data.transaction.reference_code : 'WEBHOOK_OK';
        const dEl = document.getElementById('sim-res-desc');
        if (dEl) dEl.textContent = desc;
        const mEl = document.getElementById('sim-res-meta');
        if (mEl) mEl.textContent = `${bank} • Vừa xong • Open API v2.1`;
        
        const amtEl = document.getElementById('sim-res-amount');
        if (amtEl) {
          amtEl.textContent = (type === 'INFLOW' ? '+' : '-') + amount.toLocaleString('vi-VN') + 'đ';
          amtEl.style.color = (type === 'INFLOW' ? '#10B981' : '#E8632A');
        }

        const ai = data.ai_analysis || {};
        const catB = document.getElementById('sim-res-cat-badge');
        if (catB) catB.textContent = (ai.category || 'Ăn uống & Cà phê');
        const bB = document.getElementById('sim-res-bucket-badge');
        if (bB) bB.textContent = (ai.bucket_label || '30% Nhu cầu linh hoạt');
        const cB = document.getElementById('sim-res-conf-badge');
        if (cB) cB.textContent = `🎯 Tin cậy: ${ai.confidence_pct || 98}%`;

        const alertBox = document.getElementById('sim-res-alert-box');
        if (alertBox) {
          alertBox.style.display = ai.is_night_spending ? 'block' : 'none';
        }

        resBox.style.display = 'block';
        resBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      if (typeof loadWallets === 'function') {
        try {
          const wallets = loadWallets();
          const target = wallets.find(w => {
            const prov = (w.provider || '').toLowerCase();
            const nm = (w.name || '').toLowerCase();
            const b = bank.toLowerCase();
            return prov.includes(b) || b.includes(prov) || nm.includes(b);
          });
          if (target && data.updated_wallet_balance !== null && data.updated_wallet_balance !== undefined) {
            target.currentBalance = data.updated_wallet_balance;
            target.lastSyncedAt = 'Vừa xong';
            saveWallets(wallets);
            if (typeof renderWallets === 'function') renderWallets();
          }
        } catch(e){}
      }

      lastSimPushData = {
        bank: bank,
        type: type,
        amount: amount,
        description: desc,
        balance: data.updated_wallet_balance,
        account: (data.transaction && data.transaction.account_number) ? data.transaction.account_number : '•••• ' + (data.wallet_id ? data.wallet_id.slice(-4) : '4321'),
        aiCategory: (data.ai_analysis && data.ai_analysis.category) || 'Ăn uống & Cà phê',
        aiBucket: (data.ai_analysis && data.ai_analysis.bucket_label) || '30% Nhu cầu linh hoạt'
      };

      if (typeof window.triggerBankPushNotification === 'function') {
        window.triggerBankPushNotification(lastSimPushData);
      } else if (window.showToast) {
        window.showToast(`🔔 ${bank}: Biến động ${type==='INFLOW'?'+':'-'}${amount.toLocaleString('vi-VN')}đ!`, 'success');
      }

      const statusEl = document.getElementById('ddp-last-event');
      if (statusEl) {
        const ai = data.ai_analysis || {};
        statusEl.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#10B981;"></i> Đã bắn Webhook: <strong>${escapeHtmlMain(desc)}</strong> (${type === 'INFLOW' ? '+' : '-'}${amount.toLocaleString('vi-VN')}đ)<br><span style="color:#CBD5E1;font-size:9.5px;">AI: ${escapeHtmlMain(ai.category || 'Mới')} &bull; ${escapeHtmlMain(ai.bucket_label || '50/30/20')}</span>`;
        statusEl.style.display = 'block';
      }
    } else {
      if (window.showToast) window.showToast(data.message || 'Lỗi giả lập Webhook!', 'error');
    }
  } catch (err) {
    console.error(err);
    if (window.showToast) window.showToast('Không thể kết nối API mô phỏng!', 'error');
  } finally {
    if (btnTrigger) {
      btnTrigger.disabled = false;
      btnTrigger.innerHTML = '<i class="fa-solid fa-bolt"></i> Bắn Webhook &amp; Phân Loại AI';
    }
  }
}

function replayPushFromSimResult() {
  if (lastSimPushData && typeof window.triggerBankPushNotification === 'function') {
    window.triggerBankPushNotification(lastSimPushData);
  } else if (typeof window.triggerBankPushNotification === 'function') {
    window.triggerBankPushNotification({
      bank: 'MB Bank',
      type: 'OUTFLOW',
      amount: 45000,
      description: 'Highlands Coffee',
      balance: 7455000,
      aiCategory: 'Cà phê & Đồ uống',
      aiBucket: '30% Nhu cầu linh hoạt'
    });
  }
}

async function quickFireWebhookPreset(bank, desc, amount, type) {
  type = type || 'OUTFLOW';
  amount = amount || 45000;
  desc = desc || 'Chi tiêu qua ngân hàng';
  bank = bank || 'MB Bank';

  // 1. Kích hoạt hiệu ứng chuông & notification tức thì
  if (typeof window.triggerBankPushNotification === 'function') {
    window.triggerBankPushNotification({
      bank: bank,
      type: type,
      amount: amount,
      description: desc,
      balance: type === 'INFLOW' ? 32455000 : 7410000,
      account: '•••• 4321',
      aiCategory: desc.includes('Highlands') ? 'Cà phê & Đồ uống' : (desc.includes('Grab') ? 'Ăn uống & Cà phê' : (desc.includes('Shopee') ? 'Mua sắm & Giải trí' : 'Thu nhập lương')),
      aiBucket: type === 'INFLOW' ? 'Thu nhập' : (desc.includes('Shopee') ? '30% Nhu cầu linh hoạt' : '50% Nhu cầu thiết yếu')
    });
  }

  // 2. Gửi request Webhook Event lên server
  try {
    const res = await fetch('/api/open-banking/simulate-transaction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        bank: bank,
        amount: amount,
        type: type,
        description: desc
      })
    });
    const data = await res.json();
    if (data.status === 'success' || data.success) {
      if (typeof loadWallets === 'function') {
        try {
          const wallets = loadWallets();
          const target = wallets.find(w => {
            const prov = (w.provider || '').toLowerCase();
            const nm = (w.name || '').toLowerCase();
            const b = bank.toLowerCase();
            return prov.includes(b) || b.includes(prov) || nm.includes(b);
          });
          if (target && data.updated_wallet_balance !== null && data.updated_wallet_balance !== undefined) {
            target.currentBalance = data.updated_wallet_balance;
            target.lastSyncedAt = 'Vừa xong';
            saveWallets(wallets);
            if (typeof renderWallets === 'function') renderWallets();
          }
        } catch(e){}
      }

      const statusEl = document.getElementById('ddp-last-event');
      if (statusEl) {
        const ai = data.ai_analysis || {};
        statusEl.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#10B981;"></i> Đã bắn Webhook: <strong>${escapeHtmlMain(desc)}</strong> (${type === 'INFLOW' ? '+' : '-'}${amount.toLocaleString('vi-VN')}đ)<br><span style="color:#CBD5E1;font-size:9.5px;">AI: ${escapeHtmlMain(ai.category || 'Mới')} &bull; ${escapeHtmlMain(ai.bucket_label || '50/30/20')}</span>`;
        statusEl.style.display = 'block';
      }
    }
  } catch(e) {
    console.error('Quick fire error:', e);
  }
}

function toggleDesktopDemoPanel() {
  const panel = document.getElementById('desktop-demo-panel');
  if (panel) {
    panel.classList.toggle('active');
  }
}

// Global exports
window.openSimulateTxnModal = openSimulateTxnModal;
window.closeSimulateTxnModal = closeSimulateTxnModal;
window.applySimPreset = applySimPreset;
window.submitSimulateTxn = submitSimulateTxn;
window.replayPushFromSimResult = replayPushFromSimResult;
window.quickFireWebhookPreset = quickFireWebhookPreset;
window.toggleDesktopDemoPanel = toggleDesktopDemoPanel;

