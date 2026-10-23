/**
 * FinLab — OTP Input Handler
 */
document.addEventListener('DOMContentLoaded', () => {
  const boxes = document.querySelectorAll('.otp-box');
  const hidden = document.getElementById('otp-hidden');
  const verifyBtn = document.getElementById('verify-btn');
  const countdownEl = document.getElementById('countdown');
  const resendBtn = document.getElementById('resend-btn');

  // Auto-focus first box
  if (boxes.length > 0) boxes[0].focus();

  function syncHidden() {
    let val = '';
    boxes.forEach(b => val += b.value);
    hidden.value = val;
    // Enable button when all 6 filled
    const allFilled = val.length === 6;
    verifyBtn.disabled = !allFilled;
    boxes.forEach((b, i) => {
      b.classList.toggle('filled', b.value !== '');
    });
  }

  boxes.forEach((box, idx) => {
    box.addEventListener('input', e => {
      // Allow only digits
      box.value = box.value.replace(/\D/g, '').slice(-1);
      syncHidden();
      // Move to next
      if (box.value && idx < boxes.length - 1) {
        boxes[idx + 1].focus();
      }
    });

    box.addEventListener('keydown', e => {
      if (e.key === 'Backspace' && !box.value && idx > 0) {
        boxes[idx - 1].focus();
        boxes[idx - 1].value = '';
        syncHidden();
      }
      if (e.key === 'ArrowLeft' && idx > 0) boxes[idx - 1].focus();
      if (e.key === 'ArrowRight' && idx < boxes.length - 1) boxes[idx + 1].focus();
    });

    box.addEventListener('paste', e => {
      e.preventDefault();
      const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/\D/g, '');
      pasted.split('').slice(0, 6).forEach((ch, i) => {
        if (boxes[i]) boxes[i].value = ch;
      });
      syncHidden();
      const lastFilled = Math.min(pasted.length, boxes.length - 1);
      boxes[lastFilled].focus();
    });
  });

  // Countdown timer
  let seconds = 60;
  const timer = setInterval(() => {
    seconds--;
    if (countdownEl) countdownEl.textContent = seconds;
    if (seconds <= 0) {
      clearInterval(timer);
      resendBtn.classList.remove('disabled');
      resendBtn.innerHTML = 'Yêu cầu gửi lại mã OTP';
      resendBtn.style.cursor = 'pointer';
    }
  }, 1000);

  if (resendBtn) {
    resendBtn.addEventListener('click', () => {
      if (resendBtn.classList.contains('disabled')) return;
      // Reset
      seconds = 60;
      resendBtn.classList.add('disabled');
      resendBtn.innerHTML = 'Yêu cầu gửi lại mã OTP (<span id="countdown">60</span>s)';
      // Restart timer
      const newCountdown = document.getElementById('countdown');
      let s2 = 60;
      const t2 = setInterval(() => {
        s2--;
        if (newCountdown) newCountdown.textContent = s2;
        if (s2 <= 0) {
          clearInterval(t2);
          resendBtn.classList.remove('disabled');
          resendBtn.innerHTML = 'Yêu cầu gửi lại mã OTP';
        }
      }, 1000);
      if (typeof showToast === 'function') showToast('Mã OTP mới đã được gửi! (Demo: nhập bất kỳ 6 số)', 'success');
    });
  }
});
