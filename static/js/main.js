/**
 * FinLab - Enterprise PFM & Open Banking Prototype
 * Main Dashboard Interactivity, Charts & API Handlers
 */

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    initTransactionFilters();
    initOpenBankingModal();
    initMobileExperience();
    initSidebarNav();
    initBudgetRatioModal();
    initSavingsGoals();
    initRoundUpSavings();
    initCategoryBudgets();
    initConsentManager();
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

// Global modal overlay click to close
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
    }
});

// ==========================================================================
// 1. Chart.js Initialization
// ==========================================================================
function initCharts() {
    const rawDataElement = document.getElementById('dashboard-data');
    if (!rawDataElement) return;

    let dashData;
    try {
        dashData = JSON.parse(rawDataElement.textContent);
    } catch (e) {
        console.error('Failed to parse dashboard data:', e);
        return;
    }

    const { needs, wants, savings, category_breakdown, target_ratio } = dashData;

    // --- Chart 1: Budget Ratio Doughnut Chart ---
    const ctxRule = document.getElementById('ruleChart');
    if (ctxRule) {
        new Chart(ctxRule, {
            type: 'doughnut',
            data: {
                labels: [
                    `Thiết yếu (${needs.percentage}%)`,
                    `Mong muốn (${wants.percentage}%)`,
                    `Tiết kiệm (${savings.percentage}%)`
                ],
                datasets: [{
                    data: [needs.amount, wants.amount, savings.amount],
                    backgroundColor: ['#3b82f6', '#f59e0b', '#10b981'],
                    borderWidth: 2,
                    borderColor: '#ffffff',
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            font: { size: 12, weight: '600' },
                            padding: 16
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const val = context.raw || 0;
                                return ' ' + context.label + ': ' + val.toLocaleString('vi-VN') + ' VNĐ';
                            }
                        }
                    }
                },
                cutout: '68%'
            }
        });
    }

    // --- Chart 2: Category Breakdown Horizontal Bar Chart ---
    const ctxCategory = document.getElementById('categoryChart');
    if (ctxCategory && category_breakdown) {
        const sortedCats = Object.entries(category_breakdown)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 6);

        const labels = sortedCats.map(item => item[0]);
        const dataValues = sortedCats.map(item => item[1]);

        new Chart(ctxCategory, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Số tiền đã chi (VNĐ)',
                    data: dataValues,
                    backgroundColor: '#6366f1',
                    borderRadius: 6,
                    maxBarThickness: 22
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return ' ' + (context.raw || 0).toLocaleString('vi-VN') + ' VNĐ';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: '#f1f5f9' },
                        ticks: {
                            callback: function (val) {
                                return (val / 1000000).toFixed(1) + 'Tr';
                            },
                            font: { size: 11 }
                        }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { size: 11, weight: '500' } }
                    }
                }
            }
        });
    }
}

// ==========================================================================
// 2. Feature 1: Custom Budget Ratio Logic
// ==========================================================================
function initBudgetRatioModal() {
    const btnNav = document.getElementById('btn-open-budget-ratio');
    const btnCard = document.getElementById('btn-card-edit-ratio');
    const saveBtn = document.getElementById('btn-save-budget-ratio');

    const sNeeds = document.getElementById('slider-needs');
    const sWants = document.getElementById('slider-wants');
    const sSavings = document.getElementById('slider-savings');

    const vNeeds = document.getElementById('val-needs');
    const vWants = document.getElementById('val-wants');
    const vSavings = document.getElementById('val-savings');

    const totalSumEl = document.getElementById('ratio-total-sum');
    const sumMsgEl = document.getElementById('ratio-sum-msg');

    if (btnNav) btnNav.addEventListener('click', () => openModal('modal-budget-ratio'));
    if (btnCard) btnCard.addEventListener('click', () => openModal('modal-budget-ratio'));

    function updateRatioSum() {
        if (!sNeeds || !sWants || !sSavings) return;
        const n = parseInt(sNeeds.value) || 0;
        const w = parseInt(sWants.value) || 0;
        const s = parseInt(sSavings.value) || 0;
        const sum = n + w + s;

        vNeeds.textContent = n + '%';
        vWants.textContent = w + '%';
        vSavings.textContent = s + '%';
        totalSumEl.textContent = sum + '%';

        if (sum === 100) {
            totalSumEl.style.color = '#10b981';
            sumMsgEl.innerHTML = '<i class="fa-solid fa-check-circle" style="color:#10b981;"></i> Hợp lệ (Đủ 100%)';
            if (saveBtn) saveBtn.disabled = false;
        } else {
            totalSumEl.style.color = '#ef4444';
            sumMsgEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color:#ef4444;"></i> Lệch (${sum > 100 ? '+' : ''}${sum - 100}%)`;
            if (saveBtn) saveBtn.disabled = true;
        }
    }

    if (sNeeds) sNeeds.addEventListener('input', updateRatioSum);
    if (sWants) sWants.addEventListener('input', updateRatioSum);
    if (sSavings) sSavings.addEventListener('input', updateRatioSum);

    window.setRatioPreset = function(n, w, s) {
        if (sNeeds) sNeeds.value = n;
        if (sWants) sWants.value = w;
        if (sSavings) sSavings.value = s;
        updateRatioSum();
    };

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const n = parseInt(sNeeds.value);
            const w = parseInt(sWants.value);
            const s = parseInt(sSavings.value);

            if (n + w + s !== 100) {
                alert('Tổng tỷ lệ phải đúng bằng 100%!');
                return;
            }

            saveBtn.disabled = true;
            saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';

            try {
                const res = await fetch('/api/user/budget-ratio', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ needs: n, wants: w, savings: s })
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Thành công', result.message);
                    closeModal('modal-budget-ratio');
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    alert(result.message || 'Lỗi lưu tỷ lệ!');
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu thiết lập';
                }
            } catch (err) {
                console.error(err);
                alert('Lỗi kết nối máy chủ!');
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu thiết lập';
            }
        });
    }
}

// ==========================================================================
// 3. Feature 2: Savings Goals (Hũ Tích Lũy Số)
// ==========================================================================
function initSavingsGoals() {
    const btnTrigger = document.getElementById('btn-trigger-add-goal');
    const submitAddBtn = document.getElementById('btn-submit-add-goal');
    const submitDepositBtn = document.getElementById('btn-submit-deposit');

    if (btnTrigger) {
        btnTrigger.addEventListener('click', () => openModal('modal-add-goal'));
    }

    if (submitAddBtn) {
        submitAddBtn.addEventListener('click', async () => {
            const name = document.getElementById('goal-name-input').value.trim();
            const target_amount = parseInt(document.getElementById('goal-target-input').value) || 0;
            const current_amount = parseInt(document.getElementById('goal-current-input').value) || 0;
            const deadline = document.getElementById('goal-deadline-input').value;
            const icon = document.getElementById('goal-icon-select').value;
            const color = document.getElementById('goal-color-select').value;

            if (!name || target_amount <= 0) {
                alert('Vui lòng nhập tên mục tiêu và số tiền lớn hơn 0!');
                return;
            }

            submitAddBtn.disabled = true;
            submitAddBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tạo...';

            try {
                const res = await fetch('/api/goals', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name,
                        target_amount,
                        current_amount,
                        deadline,
                        icon,
                        color
                    })
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Mục tiêu mới', result.message);
                    closeModal('modal-add-goal');
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    alert(result.message || 'Lỗi tạo mục tiêu!');
                    submitAddBtn.disabled = false;
                    submitAddBtn.innerHTML = '<i class="fa-solid fa-check"></i> Tạo mục tiêu';
                }
            } catch (e) {
                console.error(e);
                alert('Lỗi kết nối máy chủ!');
                submitAddBtn.disabled = false;
                submitAddBtn.innerHTML = '<i class="fa-solid fa-check"></i> Tạo mục tiêu';
            }
        });
    }

    window.openDepositModal = function(goalId, goalName) {
        const depositGoalId = document.getElementById('deposit-goal-id');
        const subtitle = document.getElementById('deposit-modal-subtitle');
        if (depositGoalId) depositGoalId.value = goalId;
        if (subtitle) subtitle.innerHTML = `Nạp thêm tiền tích lũy vào mục tiêu: <strong>${goalName}</strong>`;
        openModal('modal-deposit-goal');
    };

    if (submitDepositBtn) {
        submitDepositBtn.addEventListener('click', async () => {
            const goalId = document.getElementById('deposit-goal-id').value;
            const amount = parseInt(document.getElementById('deposit-amount-input').value) || 0;

            if (!goalId || amount <= 0) {
                alert('Vui lòng nhập số tiền nạp lớn hơn 0!');
                return;
            }

            submitDepositBtn.disabled = true;
            submitDepositBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang nạp...';

            try {
                const res = await fetch(`/api/goals/${goalId}/deposit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ amount })
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Tích lũy thành công', result.message);
                    closeModal('modal-deposit-goal');
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    alert(result.message || 'Lỗi nạp tiền!');
                    submitDepositBtn.disabled = false;
                    submitDepositBtn.innerHTML = '<i class="fa-solid fa-arrow-down-to-bracket"></i> Xác nhận nạp';
                }
            } catch (e) {
                console.error(e);
                alert('Lỗi kết nối máy chủ!');
                submitDepositBtn.disabled = false;
                submitDepositBtn.innerHTML = '<i class="fa-solid fa-arrow-down-to-bracket"></i> Xác nhận nạp';
            }
        });
    }

    window.deleteGoal = async function(goalId) {
        if (!confirm('Bạn có chắc chắn muốn xóa mục tiêu tích lũy này?')) return;
        try {
            const res = await fetch(`/api/goals/${goalId}`, { method: 'DELETE' });
            const result = await res.json();
            if (result.success) {
                showNotification('Đã xóa', result.message);
                setTimeout(() => window.location.reload(), 600);
            } else {
                alert(result.message || 'Lỗi xóa mục tiêu!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối máy chủ!');
        }
    };
}

// ==========================================================================
// 4. Feature 3: Round-Up Savings (Micro-investing)
// ==========================================================================
function initRoundUpSavings() {
    const toggleEnabled = document.getElementById('toggle-roundup-enabled');
    const selectStep = document.getElementById('select-roundup-step');
    const btnTransfer = document.getElementById('btn-transfer-roundup');

    if (toggleEnabled) {
        toggleEnabled.addEventListener('change', async () => {
            const enabled = toggleEnabled.checked;
            try {
                const res = await fetch('/api/user/round-up/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Heo Đất FinLab', enabled ? 'Đã kích hoạt tự động làm tròn chi tiêu!' : 'Đã tạm dừng tích lũy tiền lẻ.');
                }
            } catch (e) {
                console.error(e);
            }
        });
    }

    if (selectStep) {
        selectStep.addEventListener('change', async () => {
            const step = parseInt(selectStep.value);
            try {
                const res = await fetch('/api/user/round-up/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ step })
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Mức làm tròn', `Đã cập nhật mức làm tròn lên ${step.toLocaleString('vi-VN')} VNĐ!`);
                    setTimeout(() => window.location.reload(), 700);
                }
            } catch (e) {
                console.error(e);
            }
        });
    }

    if (btnTransfer) {
        btnTransfer.addEventListener('click', async () => {
            btnTransfer.disabled = true;
            btnTransfer.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang chuyển...';

            try {
                const res = await fetch('/api/user/round-up/transfer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Chuyển tiền lẻ thành công', result.message);
                    setTimeout(() => window.location.reload(), 900);
                } else {
                    alert(result.message || 'Lỗi chuyển tiền lẻ!');
                    btnTransfer.disabled = false;
                    btnTransfer.innerHTML = '<i class="fa-solid fa-arrow-right-arrow-left"></i> Chuyển vào Mục tiêu';
                }
            } catch (e) {
                console.error(e);
                alert('Lỗi kết nối máy chủ!');
                btnTransfer.disabled = false;
                btnTransfer.innerHTML = '<i class="fa-solid fa-arrow-right-arrow-left"></i> Chuyển vào Mục tiêu';
            }
        });
    }
}

// ==========================================================================
// 5. Feature 5: Category Budgets Editing
// ==========================================================================
function initCategoryBudgets() {
    const btnTrigger = document.getElementById('btn-trigger-edit-limits');
    const saveBtn = document.getElementById('btn-save-category-limits');

    if (btnTrigger) {
        btnTrigger.addEventListener('click', () => openModal('modal-category-budgets'));
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            const inputs = document.querySelectorAll('.cat-budget-input');
            const data = {};
            inputs.forEach(inp => {
                const cat = inp.getAttribute('data-category');
                const val = parseInt(inp.value) || 0;
                if (cat) data[cat] = val;
            });

            saveBtn.disabled = true;
            saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lưu...';

            try {
                const res = await fetch('/api/user/category-budgets', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Hạn mức danh mục', result.message);
                    closeModal('modal-category-budgets');
                    setTimeout(() => window.location.reload(), 800);
                } else {
                    alert(result.message || 'Lỗi lưu hạn mức!');
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu hạn mức';
                }
            } catch (e) {
                console.error(e);
                alert('Lỗi kết nối máy chủ!');
                saveBtn.disabled = false;
                saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Lưu hạn mức';
            }
        });
    }
}

// ==========================================================================
// 6. Feature 6: Open Banking Consent Management (Nghị định 13)
// ==========================================================================
function initConsentManager() {
    const btnNav = document.getElementById('btn-open-consent-mgr');
    if (btnNav) btnNav.addEventListener('click', () => openModal('modal-consent-mgr'));

    // Scope check toggles
    const scopeChecks = document.querySelectorAll('.scope-check');
    scopeChecks.forEach(check => {
        check.addEventListener('change', async () => {
            const bank_id = check.getAttribute('data-bank-id');
            const scope = check.getAttribute('data-scope');
            const enabled = check.checked;

            try {
                const res = await fetch('/api/consent/toggle-scope', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bank_id, scope, enabled })
                });
                const result = await res.json();
                if (result.success) {
                    showNotification('Quyền riêng tư', result.message);
                }
            } catch (e) {
                console.error(e);
            }
        });
    });

    window.revokeConsent = async function(bankId) {
        if (!confirm('Bạn có chắc chắn muốn THU HỒI QUYỀN TRUY CẬP (Revoke Consent) đối với ngân hàng này? Quá trình đồng bộ dữ liệu sẽ tạm dừng theo Nghị định 13.')) return;

        try {
            const res = await fetch('/api/consent/revoke', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bank_id: bankId })
            });
            const result = await res.json();
            if (result.success) {
                showNotification('Đã thu hồi quyền', result.message);
                setTimeout(() => window.location.reload(), 900);
            } else {
                alert(result.message || 'Lỗi thu hồi quyền!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối máy chủ!');
        }
    };

    window.reauthorizeConsent = async function(bankId) {
        try {
            const res = await fetch('/api/consent/reauthorize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bank_id: bankId })
            });
            const result = await res.json();
            if (result.success) {
                showNotification('Đã cấp lại quyền', result.message);
                setTimeout(() => window.location.reload(), 900);
            } else {
                alert(result.message || 'Lỗi cấp lại quyền!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối máy chủ!');
        }
    };
}

// ==========================================================================
// 7. Transaction Filter & Search
// ==========================================================================
function initTransactionFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const searchInput = document.getElementById('search-input');
    const tableRows = document.querySelectorAll('.fin-table tbody tr');

    let currentBank = 'ALL';
    let currentSearch = '';

    function filterTable() {
        tableRows.forEach(row => {
            const rowBank = row.getAttribute('data-bank') || '';
            const rowText = row.textContent.toLowerCase();

            const matchBank = (currentBank === 'ALL' || rowBank.toLowerCase() === currentBank.toLowerCase());
            const matchSearch = (!currentSearch || rowText.includes(currentSearch));

            if (matchBank && matchSearch) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentBank = btn.getAttribute('data-bank');
            filterTable();
        });
    });

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.trim().toLowerCase();
            filterTable();
        });
    }
}

// ==========================================================================
// 8. Open Banking Modal & API Sync Simulation
// ==========================================================================
function initOpenBankingModal() {
    const openBtn = document.getElementById('btn-open-banking');
    const modalOverlay = document.getElementById('modal-bank-sync');
    const closeBtn = document.getElementById('btn-modal-close');
    const cancelBtn = document.getElementById('btn-modal-cancel');
    const confirmSyncBtn = document.getElementById('btn-confirm-sync');
    const bankCards = document.querySelectorAll('.bank-choice-card');

    let selectedBankId = 'VCB';

    if (!modalOverlay) return;

    if (openBtn) openBtn.addEventListener('click', () => openModal('modal-bank-sync'));
    if (closeBtn) closeBtn.addEventListener('click', () => closeModal('modal-bank-sync'));
    if (cancelBtn) cancelBtn.addEventListener('click', () => closeModal('modal-bank-sync'));

    bankCards.forEach(card => {
        card.addEventListener('click', () => {
            bankCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedBankId = card.getAttribute('data-bank-id');
        });
    });

    if (confirmSyncBtn) {
        confirmSyncBtn.addEventListener('click', async () => {
            confirmSyncBtn.disabled = true;
            confirmSyncBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang xác thực OAuth 2.0...';

            try {
                const response = await fetch('/api/sync-bank', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bank_id: selectedBankId })
                });

                const result = await response.json();
                if (result.success) {
                    confirmSyncBtn.innerHTML = '<i class="fa-solid fa-check"></i> Đã đồng bộ!';
                    setTimeout(() => {
                        closeModal('modal-bank-sync');
                        showNotification('Thành công', result.message || 'Đồng bộ Open Banking API thành công!');
                        setTimeout(() => window.location.reload(), 900);
                    }, 800);
                } else {
                    alert(result.message || 'Lỗi đồng bộ!');
                    confirmSyncBtn.disabled = false;
                    confirmSyncBtn.innerHTML = 'Kết nối & Đồng bộ ngay';
                }
            } catch (err) {
                console.error(err);
                alert('Có lỗi kết nối đến máy chủ!');
                confirmSyncBtn.disabled = false;
                confirmSyncBtn.innerHTML = 'Kết nối & Đồng bộ ngay';
            }
        });
    }
}

// Toast notification
function showNotification(title, message) {
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.top = '1.5rem';
    toast.style.right = '1.5rem';
    toast.style.background = '#0f172a';
    toast.style.color = '#ffffff';
    toast.style.padding = '0.9rem 1.4rem';
    toast.style.borderRadius = '12px';
    toast.style.boxShadow = '0 10px 25px rgba(0,0,0,0.25)';
    toast.style.zIndex = '9999';
    toast.style.fontSize = '0.88rem';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '0.65rem';
    toast.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #10b981; font-size: 1.15rem;"></i> <div><strong>${title}</strong><div style="font-size: 0.78rem; opacity: 0.85;">${message}</div></div>`;

    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.4s ease';
        setTimeout(() => toast.remove(), 400);
    }, 3200);
}

// ==========================================================================
// 9. Mobile App Responsive Experience & Simulator Toggle
// ==========================================================================
function initMobileExperience() {
    const toggleBtn = document.getElementById('btn-toggle-device');
    const toggleText = document.getElementById('toggle-device-text');
    const mobileNavItems = document.querySelectorAll('.mobile-bottom-nav .mobile-nav-item');
    const mobileAiBtn = document.getElementById('mobile-nav-ai-btn');
    const chatbotTrigger = document.getElementById('chatbot-trigger');

    // 1. Mobile Simulator Toggle
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const isSimulator = document.body.classList.toggle('mobile-simulator-active');
            toggleBtn.classList.toggle('active', isSimulator);

            if (isSimulator) {
                toggleText.textContent = 'Chế độ Web';
                toggleBtn.querySelector('i').className = 'fa-solid fa-desktop';
                showNotification('Chế độ Mobile App', 'Đang giả lập màn hình ứng dụng di động cho buổi thuyết trình.');
            } else {
                toggleText.textContent = 'Chế độ App';
                toggleBtn.querySelector('i').className = 'fa-solid fa-mobile-screen';
                showNotification('Chế độ Web Desktop', 'Đã quay trở lại chế độ xem bảng điều khiển toàn màn hình.');
            }
        });
    }

    // 2. Mobile Bottom Nav Tab Navigation
    mobileNavItems.forEach(item => {
        item.addEventListener('click', (e) => {
            if (item.id === 'mobile-nav-ai-btn') return;

            mobileNavItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            const targetId = item.getAttribute('href');
            if (targetId && targetId.startsWith('#')) {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }
        });
    });

    // 3. Connect mobile nav AI button to Chatbot toggle
    if (mobileAiBtn && chatbotTrigger) {
        mobileAiBtn.addEventListener('click', (e) => {
            e.preventDefault();
            chatbotTrigger.click();
        });
    }
}

// ==========================================================================
// 10. Vertical Sidebar Navigation, Smooth Scroll, Scrollspy & Mobile Drawer
// ==========================================================================
function initSidebarNav() {
    const navLinks = document.querySelectorAll('.sidebar-nav .nav-link[data-section]');
    const sections = Array.from(navLinks).map(link => {
        const secId = link.getAttribute('data-section');
        return document.getElementById(secId);
    }).filter(Boolean);

    // 1. Live Date display
    const dateEl = document.getElementById('current-live-date');
    if (dateEl) {
        try {
            const now = new Date();
            const daysOfWeek = ['Chủ Nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
            const dayName = daysOfWeek[now.getDay()];
            const day = String(now.getDate()).padStart(2, '0');
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const year = now.getFullYear();
            dateEl.innerHTML = `<i class="fa-regular fa-calendar"></i> ${dayName}, ${day}/${month}/${year}`;
        } catch (e) {
            console.error('Error formatting live date:', e);
        }
    }

    // 2. Smooth Scrolling on Navigation Click
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const secId = link.getAttribute('data-section');
            const target = document.getElementById(secId);
            if (target) {
                e.preventDefault();
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');

                // Smooth scroll with sticky top bar offset
                const headerOffset = 82;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });

                closeMobileSidebar();
            }
        });
    });

    // 3. Scrollspy - Highlight active sidebar link as user scrolls
    let isScrollTicking = false;
    window.addEventListener('scroll', () => {
        if (!isScrollTicking) {
            window.requestAnimationFrame(() => {
                const scrollPos = window.pageYOffset + 130;
                let activeId = '';

                sections.forEach(sec => {
                    if (sec) {
                        const top = sec.offsetTop;
                        const height = sec.offsetHeight;
                        if (scrollPos >= top && scrollPos < top + height) {
                            activeId = sec.getAttribute('id');
                        }
                    }
                });

                // Default to first section if at top
                if (!activeId && window.pageYOffset < 200 && sections.length > 0) {
                    activeId = sections[0].getAttribute('id');
                }

                if (activeId) {
                    navLinks.forEach(link => {
                        if (link.getAttribute('data-section') === activeId) {
                            link.classList.add('active');
                        } else {
                            link.classList.remove('active');
                        }
                    });
                }
                isScrollTicking = false;
            });
            isScrollTicking = true;
        }
    }, { passive: true });

    // 4. Sidebar Quick Action Triggers
    const btnSidebarConsent = document.getElementById('sidebar-btn-consent');
    if (btnSidebarConsent) {
        btnSidebarConsent.addEventListener('click', () => {
            openModal('modal-consent-mgr');
            closeMobileSidebar();
        });
    }

    const btnSidebarBank = document.getElementById('sidebar-btn-open-banking');
    if (btnSidebarBank) {
        btnSidebarBank.addEventListener('click', () => {
            openModal('modal-bank-sync');
            closeMobileSidebar();
        });
    }

    const btnSidebarAi = document.getElementById('sidebar-btn-ai-chat');
    const chatbotTrigger = document.getElementById('chatbot-trigger');
    if (btnSidebarAi && chatbotTrigger) {
        btnSidebarAi.addEventListener('click', () => {
            chatbotTrigger.click();
            closeMobileSidebar();
        });
    }

    // 5. Mobile Drawer Toggle & Backdrop
    const btnToggle = document.getElementById('btn-sidebar-toggle');
    const btnClose = document.getElementById('btn-sidebar-close');
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');

    function openMobileSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (backdrop) backdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeMobileSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (btnToggle) btnToggle.addEventListener('click', openMobileSidebar);
    if (btnClose) btnClose.addEventListener('click', closeMobileSidebar);
    if (backdrop) backdrop.addEventListener('click', closeMobileSidebar);
}
