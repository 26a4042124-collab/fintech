/**
 * FinLab - Main Dashboard Interactivity & Charts
 */

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    initTransactionFilters();
    initOpenBankingModal();
    initMobileExperience();
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

    const { needs, wants, savings, category_breakdown } = dashData;

    // --- Chart 1: 50/30/20 Rule Doughnut Chart ---
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
                    maxBarThickness: 24
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
// 2. Transaction Filter & Search
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
// 3. Open Banking Modal & API Sync Simulation
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

    function openModal() {
        modalOverlay.classList.add('open');
    }

    function closeModal() {
        modalOverlay.classList.remove('open');
    }

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });

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
                        closeModal();
                        showNotification('Thành công', result.message || 'Đồng bộ Open Banking API thành công!');
                        setTimeout(() => window.location.reload(), 1000);
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

// Simple toast notification
function showNotification(title, message) {
    const toast = document.createElement('div');
    toast.style.position = 'fixed';
    toast.style.top = '1.5rem';
    toast.style.right = '1.5rem';
    toast.style.background = '#0f172a';
    toast.style.color = '#ffffff';
    toast.style.padding = '0.9rem 1.4rem';
    toast.style.borderRadius = '12px';
    toast.style.boxShadow = '0 10px 25px rgba(0,0,0,0.2)';
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
    }, 3000);
}

// ==========================================================================
// 4. Mobile App Responsive Experience & Simulator Toggle
// ==========================================================================
function initMobileExperience() {
    const toggleBtn = document.getElementById('btn-toggle-device');
    const toggleText = document.getElementById('toggle-device-text');
    const mobileNavItems = document.querySelectorAll('.mobile-bottom-nav .mobile-nav-item');
    const mobileAiBtn = document.getElementById('mobile-nav-ai-btn');
    const chatbotTrigger = document.getElementById('chatbot-trigger');

    // 1. Mobile Simulator Toggle (For PC / Laptop Presentation)
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

