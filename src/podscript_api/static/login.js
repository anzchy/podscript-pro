/**
 * Login/Register page logic
 */

// DOM Elements
const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');

// Tab switching
tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const targetTab = btn.dataset.tab;

        // Update active tab button
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Update visible tab content
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === targetTab + 'Tab') {
                content.classList.add('active');
            }
        });

        // Clear messages
        hideMessages();
    });
});

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
    successMessage.classList.remove('show');
}

// Show success message
function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.classList.add('show');
    errorMessage.classList.remove('show');
}

// Hide all messages
function hideMessages() {
    errorMessage.classList.remove('show');
    successMessage.classList.remove('show');
}

// Get redirect URL from sessionStorage or default to homepage
function getRedirectUrl() {
    const redirectUrl = sessionStorage.getItem('redirectAfterLogin');
    sessionStorage.removeItem('redirectAfterLogin');
    return redirectUrl || '/';
}

// Set button loading state
function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.textContent = '处理中...';
    } else {
        button.disabled = false;
        button.textContent = button.dataset.originalText || button.textContent;
    }
}

// Login form submission
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();

    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const loginBtn = document.getElementById('loginBtn');

    if (!email || !password) {
        showError('请填写邮箱和密码');
        return;
    }

    setButtonLoading(loginBtn, true);

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '登录失败');
        }

        // Login successful - redirect
        showSuccess('登录成功，正在跳转...');

        // Store user info in localStorage for the main app
        localStorage.setItem('user', JSON.stringify({
            user_id: data.user_id,
            email: data.email,
            credit_balance: data.credit_balance,
        }));

        // Redirect after short delay
        setTimeout(() => {
            window.location.href = getRedirectUrl();
        }, 500);

    } catch (error) {
        showError(error.message);
    } finally {
        setButtonLoading(loginBtn, false);
    }
});

// Register form submission
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();

    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const registerBtn = document.getElementById('registerBtn');

    if (!email || !password || !confirmPassword) {
        showError('请填写所有字段');
        return;
    }

    if (password !== confirmPassword) {
        showError('两次输入的密码不一致');
        return;
    }

    if (password.length < 6) {
        showError('密码至少需要 6 位字符');
        return;
    }

    setButtonLoading(registerBtn, true);

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || '注册失败');
        }

        // Registration successful - redirect
        showSuccess('注册成功！您已获得 10 积分，正在跳转...');

        // Store user info in localStorage for the main app
        localStorage.setItem('user', JSON.stringify({
            user_id: data.user_id,
            email: data.email,
            credit_balance: data.credit_balance,
        }));

        // Redirect after short delay
        setTimeout(() => {
            window.location.href = getRedirectUrl();
        }, 1000);

    } catch (error) {
        showError(error.message);
    } finally {
        setButtonLoading(registerBtn, false);
    }
});

// Check if user is already logged in
async function checkAuth() {
    try {
        const response = await fetch('/api/auth/me');
        if (response.ok) {
            // User is already logged in, redirect to homepage
            window.location.href = getRedirectUrl();
        }
    } catch (error) {
        // Not logged in, stay on login page
    }
}

// Check auth on page load
checkAuth();
