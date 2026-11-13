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
  const aiBucket = opts.aiBucket || 'Nhu cầu linh hoạt (Wants)';

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
        if (bB) bB.textContent = (ai.bucket_label || 'Nhu cầu linh hoạt (Wants)');
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
        aiBucket: (data.ai_analysis && data.ai_analysis.bucket_label) || 'Nhu cầu linh hoạt (Wants)'
      };

      if (typeof window.triggerBankPushNotification === 'function') {
        window.triggerBankPushNotification(lastSimPushData);
      } else if (window.showToast) {
        window.showToast(`🔔 ${bank}: Biến động ${type==='INFLOW'?'+':'-'}${amount.toLocaleString('vi-VN')}đ!`, 'success');
      }

      const statusEl = document.getElementById('ddp-last-event');
      if (statusEl) {
        const ai = data.ai_analysis || {};
        statusEl.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#10B981;"></i> Đã bắn Webhook: <strong>${escapeHtmlMain(desc)}</strong> (${type === 'INFLOW' ? '+' : '-'}${amount.toLocaleString('vi-VN')}đ)<br><span style="color:#CBD5E1;font-size:9.5px;">AI: ${escapeHtmlMain(ai.category || 'Mới')} &bull; ${escapeHtmlMain(ai.bucket_label || 'Phân loại tự động')}</span>`;
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
      aiBucket: 'Nhu cầu linh hoạt (Wants)'
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
      aiBucket: type === 'INFLOW' ? 'Dòng thu nhập (Inflow)' : (desc.includes('Shopee') ? 'Nhu cầu linh hoạt (Wants)' : 'Nhu cầu thiết yếu (Needs)')
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
        statusEl.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#10B981;"></i> Đã bắn Webhook: <strong>${escapeHtmlMain(desc)}</strong> (${type === 'INFLOW' ? '+' : '-'}${amount.toLocaleString('vi-VN')}đ)<br><span style="color:#CBD5E1;font-size:9.5px;">AI: ${escapeHtmlMain(ai.category || 'Mới')} &bull; ${escapeHtmlMain(ai.bucket_label || 'Phân loại tự động')}</span>`;
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

// ==========================================================================
// Income-Based Custom Budget Allocation Modal Controller (Global)
// ==========================================================================
function _getLocalSuggestionByIncome(income) {
  const inc = Number(income) || 0;
  if (inc < 12000000) {
    return {
      needs: 65,
      wants: 20,
      savings: 15,
      bracket: '< 12 triệu',
      reason: 'Thu nhập dưới 12 triệu nên ưu tiên 65% chi tiêu thiết yếu, 20% mong muốn và duy trì 15% tiết kiệm.'
    };
  }
  if (inc < 25000000) {
    return {
      needs: 55,
      wants: 25,
      savings: 20,
      bracket: '12 – 25 triệu',
      reason: 'Thu nhập 12–25 triệu phù hợp 55% thiết yếu, 25% mong muốn và 20% tích lũy.'
    };
  }
  return {
    needs: 40,
    wants: 25,
    savings: 35,
    bracket: 'Từ 25 triệu trở lên',
    reason: 'Thu nhập từ 25 triệu trở lên tối ưu đẩy mạnh tỷ trọng tích sản & đầu tư lên 35%.'
  };
}

function _applyRatioValues(needs, wants, savings, incomeOverride) {
  const incEl = document.getElementById('ratio-income-input');
  if (incomeOverride !== undefined && incomeOverride !== null && incEl) {
    incEl.value = Math.round(Number(incomeOverride) || 0);
  }
  const income = Math.max(0, Number(incEl ? incEl.value : 0));
  const map = { needs: needs, wants: wants, savings: savings };
  ['needs', 'wants', 'savings'].forEach((k) => {
    const pct = Math.max(0, Math.min(100, Math.round(Number(map[k]) || 0)));
    const rng = document.getElementById(`ratio-range-${k}`);
    const pctEl = document.getElementById(`ratio-pct-${k}`);
    const vndEl = document.getElementById(`ratio-vnd-${k}`);
    const fmtEl = document.getElementById(`ratio-vnd-fmt-${k}`);
    if (rng) rng.value = pct;
    if (pctEl) pctEl.value = pct;
    const vnd = Math.round((income * pct) / 100);
    if (vndEl) vndEl.value = vnd;
    if (fmtEl) fmtEl.textContent = vnd.toLocaleString('vi-VN') + 'đ';
  });
  _updateRatioSuggestionHint(income);
  refreshRatioSummary();
}

function _updateRatioSuggestionHint(income) {
  const noteEl = document.getElementById('ratio-suggestion-note');
  if (!noteEl) return;
  const sug = _getLocalSuggestionByIncome(income);
  noteEl.innerHTML = `<i class="fa-solid fa-lightbulb" style="color:#2563EB;"></i> <strong>Gợi ý (${sug.bracket}):</strong> ${sug.needs}% / ${sug.wants}% / ${sug.savings}% — ${sug.reason}`;
}

function refreshRatioSummary() {
  const income = Math.max(0, Number(document.getElementById('ratio-income-input')?.value || 0));
  const needs = Number(document.getElementById('ratio-pct-needs')?.value || 0);
  const wants = Number(document.getElementById('ratio-pct-wants')?.value || 0);
  const savings = Number(document.getElementById('ratio-pct-savings')?.value || 0);
  const totalPct = needs + wants + savings;
  const totalVnd = Math.round((income * totalPct) / 100);

  const pctBadge = document.getElementById('ratio-total-pct');
  const vndBadge = document.getElementById('ratio-total-vnd');
  const msgEl = document.getElementById('ratio-total-msg');
  const autoBtn = document.getElementById('btn-autobalance-ratio');
  const saveBtn = document.getElementById('btn-save-budget-ratio');
  const box = document.getElementById('ratio-summary-box');

  if (pctBadge) pctBadge.textContent = `${totalPct}%`;
  if (vndBadge) vndBadge.textContent = `${totalVnd.toLocaleString('vi-VN')}đ / ${Math.round(income).toLocaleString('vi-VN')}đ`;

  const valid = totalPct === 100 && income > 0;
  if (box) {
    box.style.background = valid ? '#ECFDF5' : '#FEF2F2';
    box.style.borderColor = valid ? '#A7F3D0' : '#FECACA';
  }
  if (pctBadge) pctBadge.style.color = valid ? '#059669' : '#DC2626';
  if (msgEl) {
    if (income <= 0) {
      msgEl.textContent = 'Vui lòng nhập thu nhập hàng tháng lớn hơn 0đ.';
      msgEl.style.color = '#DC2626';
    } else if (totalPct === 100) {
      msgEl.textContent = 'Tổng phân bổ hợp lệ (100% thu nhập).';
      msgEl.style.color = '#059669';
    } else {
      const diff = 100 - totalPct;
      msgEl.textContent = diff > 0 ? `Còn thiếu ${diff}% chưa phân bổ.` : `Đang vượt quá ${Math.abs(diff)}% thu nhập.`;
      msgEl.style.color = '#DC2626';
    }
  }
  if (autoBtn) autoBtn.style.display = totalPct === 100 ? 'none' : 'inline-flex';
  if (saveBtn) {
    saveBtn.disabled = !valid;
    saveBtn.style.opacity = valid ? '1' : '0.55';
  }
}

function openBudgetRatioModal() {
  const modal = document.getElementById('modal-budget-ratio');
  if (!modal) {
    if (window.showToast) window.showToast('Vui lòng đăng nhập để tự chia ngân sách!', 'info');
    return;
  }
  const inc = Number(modal.dataset.income || 18000000);
  const needs = Number(modal.dataset.needs || 50);
  const wants = Number(modal.dataset.wants || 30);
  const savings = Number(modal.dataset.savings || 20);
  _applyRatioValues(needs, wants, savings, inc);
  openModal('modal-budget-ratio');
}

function closeBudgetRatioModal() {
  closeModal('modal-budget-ratio');
}

function syncRatioFromPct(bucket, rawVal) {
  const pct = Math.max(0, Math.min(100, Math.round(Number(rawVal) || 0)));
  const rng = document.getElementById(`ratio-range-${bucket}`);
  const pctEl = document.getElementById(`ratio-pct-${bucket}`);
  const vndEl = document.getElementById(`ratio-vnd-${bucket}`);
  const fmtEl = document.getElementById(`ratio-vnd-fmt-${bucket}`);
  const income = Math.max(0, Number(document.getElementById('ratio-income-input')?.value || 0));
  if (rng) rng.value = pct;
  if (pctEl) pctEl.value = pct;
  const vnd = Math.round((income * pct) / 100);
  if (vndEl) vndEl.value = vnd;
  if (fmtEl) fmtEl.textContent = vnd.toLocaleString('vi-VN') + 'đ';
  refreshRatioSummary();
}

function syncRatioFromVnd(bucket, rawVal) {
  const vnd = Math.max(0, Number(rawVal) || 0);
  const income = Math.max(0, Number(document.getElementById('ratio-income-input')?.value || 0));
  const pct = income > 0 ? Math.max(0, Math.min(100, Math.round((vnd / income) * 100))) : 0;
  const rng = document.getElementById(`ratio-range-${bucket}`);
  const pctEl = document.getElementById(`ratio-pct-${bucket}`);
  const fmtEl = document.getElementById(`ratio-vnd-fmt-${bucket}`);
  if (rng) rng.value = pct;
  if (pctEl) pctEl.value = pct;
  if (fmtEl) fmtEl.textContent = Math.round(vnd).toLocaleString('vi-VN') + 'đ';
  refreshRatioSummary();
}

function onRatioIncomeInput() {
  const income = Math.max(0, Number(document.getElementById('ratio-income-input')?.value || 0));
  ['needs', 'wants', 'savings'].forEach((k) => {
    const pct = Math.max(0, Math.min(100, Math.round(Number(document.getElementById(`ratio-pct-${k}`)?.value || 0))));
    const vnd = Math.round((income * pct) / 100);
    const vndEl = document.getElementById(`ratio-vnd-${k}`);
    const fmtEl = document.getElementById(`ratio-vnd-fmt-${k}`);
    if (vndEl) vndEl.value = vnd;
    if (fmtEl) fmtEl.textContent = vnd.toLocaleString('vi-VN') + 'đ';
  });
  _updateRatioSuggestionHint(income);
  refreshRatioSummary();
}

function applyRatioPreset(needs, wants, savings, label) {
  _applyRatioValues(needs, wants, savings);
  if (label && window.showToast) {
    window.showToast(`Đã áp dụng tỷ lệ ${needs}/${wants}/${savings} (${label})`, 'info');
  }
}

async function suggestRatioForIncomeInput() {
  const income = Math.max(0, Number(document.getElementById('ratio-income-input')?.value || 0));
  if (income <= 0) {
    if (window.showToast) window.showToast('Vui lòng nhập thu nhập lớn hơn 0đ!', 'error');
    return;
  }
  let sug = _getLocalSuggestionByIncome(income);
  try {
    const res = await fetch(`/api/user/budget-suggestion?income=${encodeURIComponent(income)}`);
    if (res.ok) {
      const data = await res.json();
      if (data.success && data.suggestion) sug = data.suggestion;
    }
  } catch (e) {
    // Fallback sang gợi ý cục bộ
  }
  _applyRatioValues(sug.needs, sug.wants, sug.savings);
  const noteEl = document.getElementById('ratio-suggestion-note');
  if (noteEl) {
    noteEl.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles" style="color:#2563EB;"></i> <strong>Gợi ý (${sug.bracket}):</strong> ${sug.needs}% / ${sug.wants}% / ${sug.savings}% — ${sug.reason}`;
  }
  if (window.showToast) {
    window.showToast(`Đã áp dụng gợi ý ${sug.needs}/${sug.wants}/${sug.savings} cho thu nhập ${income.toLocaleString('vi-VN')}đ`, 'success');
  }
}

function autoBalanceRatio() {
  let needs = Math.max(0, Math.min(100, Math.round(Number(document.getElementById('ratio-pct-needs')?.value || 0))));
  let wants = Math.max(0, Math.min(100, Math.round(Number(document.getElementById('ratio-pct-wants')?.value || 0))));
  let savings = 0;
  if (needs + wants <= 100) {
    savings = 100 - needs - wants;
  } else {
    const sumNW = needs + wants;
    needs = Math.round((needs / sumNW) * 100);
    wants = 100 - needs;
    savings = 0;
  }
  _applyRatioValues(needs, wants, savings);
}

async function submitBudgetRatio() {
  const income = Math.max(0, Math.round(Number(document.getElementById('ratio-income-input')?.value || 0)));
  const needs = Math.round(Number(document.getElementById('ratio-pct-needs')?.value || 0));
  const wants = Math.round(Number(document.getElementById('ratio-pct-wants')?.value || 0));
  const savings = Math.round(Number(document.getElementById('ratio-pct-savings')?.value || 0));

  if (income <= 0) {
    if (window.showToast) window.showToast('Thu nhập hàng tháng phải lớn hơn 0đ!', 'error');
    return;
  }
  if (needs + wants + savings !== 100) {
    if (window.showToast) window.showToast(`Tổng tỷ lệ phải bằng 100% (hiện tại ${needs + wants + savings}%)!`, 'error');
    return;
  }

  const btn = document.getElementById('btn-save-budget-ratio');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';
  }
  try {
    const res = await fetch('/api/user/budget-ratio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        monthly_income: income,
        needs: needs,
        wants: wants,
        savings: savings
      })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      const modal = document.getElementById('modal-budget-ratio');
      if (modal) {
        modal.dataset.income = income;
        modal.dataset.needs = needs;
        modal.dataset.wants = wants;
        modal.dataset.savings = savings;
      }
      closeBudgetRatioModal();
      if (window.showToast) {
        window.showToast(`✅ Đã lưu thu nhập ${income.toLocaleString('vi-VN')}đ (${needs}/${wants}/${savings})!`, 'success');
      }
      setTimeout(() => window.location.reload(), 650);
    } else {
      if (window.showToast) window.showToast(data.message || 'Không thể lưu cấu hình ngân sách!', 'error');
    }
  } catch (err) {
    console.error(err);
    if (window.showToast) window.showToast('Lỗi kết nối khi lưu tỷ lệ ngân sách!', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu ngân sách';
    }
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
window.openBudgetRatioModal = openBudgetRatioModal;
window.closeBudgetRatioModal = closeBudgetRatioModal;
window.syncRatioFromPct = syncRatioFromPct;
window.syncRatioFromVnd = syncRatioFromVnd;
window.onRatioIncomeInput = onRatioIncomeInput;
window.applyRatioPreset = applyRatioPreset;
window.suggestRatioForIncomeInput = suggestRatioForIncomeInput;
window.autoBalanceRatio = autoBalanceRatio;
window.submitBudgetRatio = submitBudgetRatio;
window.refreshRatioSummary = refreshRatioSummary;

