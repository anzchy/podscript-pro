/**
 * Credits page JavaScript
 * Handles balance display, payment flow, and transaction history
 */

// State
let currentBalance = 0;
let selectedAmount = 50;
let selectedMethod = 'alipay';
let currentUser = null;

// DOM Elements
const balanceEl = document.getElementById('currentBalance');
const errorMessageEl = document.getElementById('errorMessage');
const payBtn = document.getElementById('payBtn');
const customAmountInput = document.getElementById('customAmount');
const customCreditsEl = document.getElementById('customCredits');
const historyLoadingEl = document.getElementById('historyLoading');
const historyEmptyEl = document.getElementById('historyEmpty');
const historyTableEl = document.getElementById('historyTable');
const historyBodyEl = document.getElementById('historyBody');
const userMenuEl = document.getElementById('userMenu');
const loginLinkEl = document.getElementById('loginLink');
const userCreditsEl = document.getElementById('userCredits');
const logoutBtnEl = document.getElementById('logoutBtn');

// Initialize
document.addEventListener('DOMContentLoaded', init);

async function init() {
    await checkAuth();

    if (!currentUser) {
        // Redirect to login if not authenticated
        sessionStorage.setItem('redirectAfterLogin', '/static/credits.html');
        window.location.href = '/login';
        return;
    }

    setupPresetButtons();
    setupCustomAmount();
    setupPaymentMethods();
    setupPayButton();
    setupLogout();

    await Promise.all([
        loadBalance(),
        loadTransactions()
    ]);
}

// Auth check
async function checkAuth() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            const data = await response.json();
            currentUser = data;
            currentBalance = data.credits;
            updateAuthUI(true);
        } else {
            updateAuthUI(false);
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        updateAuthUI(false);
    }
}

function updateAuthUI(isLoggedIn) {
    if (isLoggedIn && currentUser) {
        userMenuEl.hidden = false;
        loginLinkEl.style.display = 'none';
        userCreditsEl.textContent = currentUser.credits;
    } else {
        userMenuEl.hidden = true;
        loginLinkEl.style.display = '';
    }
}

// Setup logout
function setupLogout() {
    logoutBtnEl.addEventListener('click', async () => {
        try {
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/';
        } catch (error) {
            console.error('Logout failed:', error);
        }
    });
}

// Load balance
async function loadBalance() {
    try {
        const response = await fetch('/api/credits/balance');
        if (response.ok) {
            const data = await response.json();
            currentBalance = data.balance;
            balanceEl.textContent = currentBalance;
            userCreditsEl.textContent = currentBalance;
        } else if (response.status === 401) {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Failed to load balance:', error);
        balanceEl.textContent = '--';
    }
}

// Load transactions
async function loadTransactions() {
    try {
        const response = await fetch('/api/credits/transactions?limit=20');
        historyLoadingEl.style.display = 'none';

        if (response.ok) {
            const data = await response.json();

            if (data.transactions.length === 0) {
                historyEmptyEl.style.display = 'block';
                historyTableEl.style.display = 'none';
            } else {
                historyEmptyEl.style.display = 'none';
                historyTableEl.style.display = 'table';
                renderTransactions(data.transactions);
            }
        } else if (response.status === 401) {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Failed to load transactions:', error);
        historyLoadingEl.textContent = '加载失败';
    }
}

function renderTransactions(transactions) {
    historyBodyEl.innerHTML = transactions.map(tx => {
        const date = new Date(tx.created_at);
        const dateStr = date.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });

        const typeLabels = {
            'bonus': '赠送',
            'recharge': '充值',
            'consumption': '消费',
            'refund': '退款'
        };

        const typeClasses = {
            'bonus': 'type-bonus',
            'recharge': 'type-recharge',
            'consumption': 'type-consumption',
            'refund': 'type-recharge'
        };

        const amountClass = tx.amount >= 0 ? 'amount-positive' : 'amount-negative';
        const amountStr = tx.amount >= 0 ? `+${tx.amount}` : tx.amount;

        return `
            <tr>
                <td>${dateStr}</td>
                <td><span class="type-badge ${typeClasses[tx.type] || ''}">${typeLabels[tx.type] || tx.type}</span></td>
                <td class="${amountClass}">${amountStr}</td>
                <td>${tx.description || '-'}</td>
            </tr>
        `;
    }).join('');
}

// Setup preset buttons
function setupPresetButtons() {
    const presetBtns = document.querySelectorAll('.preset-btn');

    presetBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Clear custom input
            customAmountInput.value = '';
            customCreditsEl.textContent = '0';

            // Update selection
            presetBtns.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');

            selectedAmount = parseInt(btn.dataset.amount);
            updatePayButton();
        });
    });
}

// Setup custom amount
function setupCustomAmount() {
    customAmountInput.addEventListener('input', () => {
        const value = parseInt(customAmountInput.value) || 0;

        // Clear preset selection
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('selected'));

        if (value >= 1 && value <= 500) {
            selectedAmount = value;
            customCreditsEl.textContent = value;
            hideError();
        } else if (value > 500) {
            selectedAmount = 0;
            customCreditsEl.textContent = '0';
            showError('金额不能超过 500 元');
        } else {
            selectedAmount = 0;
            customCreditsEl.textContent = '0';
        }

        updatePayButton();
    });
}

// Setup payment methods
function setupPaymentMethods() {
    const methodBtns = document.querySelectorAll('.method-btn');

    methodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            methodBtns.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedMethod = btn.dataset.method;
        });
    });
}

// Setup pay button
function setupPayButton() {
    payBtn.addEventListener('click', createPayment);
}

function updatePayButton() {
    if (selectedAmount >= 1 && selectedAmount <= 500) {
        payBtn.textContent = `立即支付 ${selectedAmount} 元`;
        payBtn.disabled = false;
    } else {
        payBtn.textContent = '请选择金额';
        payBtn.disabled = true;
    }
}

// Create payment
async function createPayment() {
    if (selectedAmount < 1 || selectedAmount > 500) {
        showError('请选择有效的充值金额');
        return;
    }

    payBtn.disabled = true;
    payBtn.textContent = '正在创建订单...';

    try {
        const response = await fetch('/api/payment/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                amount: selectedAmount,
                pay_type: selectedMethod,
            }),
        });

        if (response.ok) {
            const data = await response.json();
            // Redirect to payment page
            window.location.href = data.payment_url;
        } else if (response.status === 401) {
            window.location.href = '/login';
        } else if (response.status === 503) {
            showError('支付服务暂不可用，请稍后再试');
        } else {
            const error = await response.json();
            showError(error.detail || '创建订单失败');
        }
    } catch (error) {
        console.error('Payment creation failed:', error);
        showError('网络错误，请稍后再试');
    } finally {
        updatePayButton();
    }
}

// Error handling
function showError(message) {
    errorMessageEl.textContent = message;
    errorMessageEl.classList.add('show');
}

function hideError() {
    errorMessageEl.classList.remove('show');
}
