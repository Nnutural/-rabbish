document.addEventListener('DOMContentLoaded', function () {
    // ✅ 初始化 QWebChannel
    if (typeof QWebChannel === 'undefined') {
        console.error("❌ qwebchannel.js 未加载");
        return;
    }

    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.backend = channel.objects.backend;
        console.log("✅ WebChannel 已连接");
    });

    // 标签切换
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function () {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));

            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.getElementById(`${tabId}-form`).classList.add('active');
        });
    });

    // 表单切换（登录 <=> 注册）
    document.querySelectorAll('.switch-form a').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const formId = this.getAttribute('data-switch');

            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.form').forEach(f => f.classList.remove('active'));

            document.querySelector(`.tab[data-tab="${formId}"]`).classList.add('active');
            document.getElementById(`${formId}-form`).classList.add('active');
        });
    });

    // 密码显示/隐藏功能
    setupPasswordToggle('login-password', 'login-password-toggle');
    setupPasswordToggle('register-password', 'register-password-toggle');

    // 登录验证
    document.getElementById('login-btn').addEventListener('click', function () {
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        let isValid = true;

        document.getElementById('login-username-error').style.display = 'none';
        document.getElementById('login-password-error').style.display = 'none';

        if (!username) {
            showError('login-username-error', '请输入用户名');
            isValid = false;
        }

        if (!password) {
            showError('login-password-error', '请输入密码');
            isValid = false;
        }

        if (isValid) {
            console.log("正在尝试调用 backend.loginSuccess()");
            if (window.backend && typeof window.backend.loginSuccess === 'function') {
                window.backend.loginSuccess(); // ✅ 通知 PyQt 登录成功
            } else {
                alert("❌ WebChannel 未连接，无法跳转！");
            }
        }
    });

    // 注册验证
    document.getElementById('register-btn').addEventListener('click', function () {
        const username = document.getElementById('register-username').value.trim();
        const password = document.getElementById('register-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        let isValid = true;

        document.querySelectorAll('#register-form .error').forEach(el => el.style.display = 'none');

        if (!username) {
            showError('register-username-error', '请输入用户名');
            isValid = false;
        } else if (!validateUsername(username)) {
            showError('register-username-error', '用户名需为6-20位字母数字组合');
            isValid = false;
        }

        if (!password) {
            showError('register-password-error', '请输入密码');
            isValid = false;
        } else if (!validatePassword(password)) {
            showError('register-password-error', '密码需8-20位，包含大小写字母和数字');
            isValid = false;
        }

        if (!confirmPassword) {
            showError('confirm-password-error', '请确认密码');
            isValid = false;
        } else if (password !== confirmPassword) {
            showError('confirm-password-error', '两次输入的密码不一致');
            isValid = false;
        }

        if (isValid) {
            alert('注册成功！实际应用中将创建账户');
        }
    });

    // 实时输入验证
    document.getElementById('register-username').addEventListener('input', function () {
        const username = this.value.trim();
        if (username && !validateUsername(username)) {
            showError('register-username-error', '用户名需为6-20位字母数字组合');
        } else {
            document.getElementById('register-username-error').style.display = 'none';
        }
    });

    document.getElementById('register-password').addEventListener('input', function () {
        const password = this.value;
        if (password && !validatePassword(password)) {
            showError('register-password-error', '密码需8-20位，包含大小写字母和数字');
        } else {
            document.getElementById('register-password-error').style.display = 'none';
        }
    });

    // =================== 工具函数 ====================
    function setupPasswordToggle(inputId, toggleId) {
        const passwordInput = document.getElementById(inputId);
        const toggleButton = document.getElementById(toggleId);

        toggleButton.addEventListener('click', function () {
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                this.textContent = '🔒';
            } else {
                passwordInput.type = 'password';
                this.textContent = '👁️';
            }
        });
    }

    function showError(elementId, message) {
        const errorElement = document.getElementById(elementId);
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }

    function validateUsername(username) {
        return /^[a-zA-Z0-9]{6,20}$/.test(username);
    }

    function validatePassword(password) {
        return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,20}$/.test(password);
    }
});
