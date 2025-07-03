// 全局变量
let currentContactId = null;
let appData = null;
let backend = null;  // 后端对象


// 动态加载 qwebchannel.js
function loadQWebChannelScript(callback) {
    const script = document.createElement('script');
    script.src = 'qwebchannel.js'; // 确保 qwebchannel.js 路径正确
    script.onload = callback;
    script.onerror = () => {
        console.error('加载 qwebchannel.js 失败');
    };
    document.head.appendChild(script);
}
function refreshCurrentContactMessages() {
    if (!currentContactId) return;

    fetch('data.json')
        .then(response => {
            if (!response.ok) throw new Error('加载 data.json 失败');
            return response.json();
        })
        .then(json => {
            appData.messages = json.messages;

            // 重新更新联系人预览和时间
            appData.contacts.forEach(contact => {
                const cid = String(contact.id);
                const msgDays = appData.messages[cid];
                if (!msgDays || msgDays.length === 0) {
                    contact.preview = '';
                    contact.time = '';
                    return;
                }

                const lastDay = msgDays[msgDays.length - 1];
                const lastMsgs = lastDay.messages;
                if (!lastMsgs || lastMsgs.length === 0) {
                    contact.preview = '';
                    contact.time = '';
                    return;
                }

                const lastMsg = lastMsgs[lastMsgs.length - 1];
                contact.preview = lastMsg.content;
                contact.time = lastMsg.time;
            });

            // 联系人排序（最新消息日期+时间排前面）
            appData.contacts.sort((a, b) => {
                const aMsg = appData.messages[a.id];
                const bMsg = appData.messages[b.id];
                let aLast = '';
                if (aMsg && aMsg.length > 0) {
                    const lastDay = aMsg[aMsg.length - 1];
                    if (lastDay.messages && lastDay.messages.length > 0) {
                        const lastMsg = lastDay.messages[lastDay.messages.length - 1];
                        aLast = `${lastDay.date} ${lastMsg.time}`;
                    }
                }
                let bLast = '';
                if (bMsg && bMsg.length > 0) {
                    const lastDay = bMsg[bMsg.length - 1];
                    if (lastDay.messages && lastDay.messages.length > 0) {
                        const lastMsg = lastDay.messages[lastDay.messages.length - 1];
                        bLast = `${lastDay.date} ${lastMsg.time}`;
                    }
                }
                return bLast.localeCompare(aLast);
            });

            renderContacts(appData.contacts);
            loadMessages(currentContactId);
        })
        .catch(err => {
            console.warn('刷新消息失败:', err);
        });
}


function getCurrentTimeWithSeconds() {
    const now = new Date();
    const hh = now.getHours().toString().padStart(2, '0');
    const mm = now.getMinutes().toString().padStart(2, '0');
    const ss = now.getSeconds().toString().padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
}

// 预处理联系人：离线用户不显示 IP
function preprocessContacts(contacts) {
    contacts.forEach(contact => {
        delete contact.preview;
        delete contact.time;
        if (contact.status === 'offline') {
            delete contact.address;
        }
    });
}


// 初始化 QWebChannel 和绑定 backend 对象
function initWebChannel() {
    if (typeof QWebChannel === 'undefined') {
        console.error('QWebChannel 未定义');
        return;
    }
    new QWebChannel(qt.webChannelTransport, function(channel) {
        backend = channel.objects.backend;
        console.log('QWebChannel 初始化完成，backend 可用');
    });
}

// DOM 加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    loadQWebChannelScript(() => {
        initWebChannel();
    });
    loadData();
    bindEvents();
});

// 载入 data.json，初始化联系人列表
function loadData() {
    fetch('data.json')
    .then(response => {
        if (!response.ok) throw new Error('网络响应失败');
        return response.json();
    })
    .then(json => {
        appData = json;

        // 预处理联系人（去除 preview、time、离线不显示 address）
        preprocessContacts(appData.contacts);

        // 动态生成 preview 和 time 字段
        appData.contacts.forEach(contact => {
            const cid = String(contact.id);
            const msgDays = appData.messages[cid];
            if (!msgDays || msgDays.length === 0) {
                contact.preview = '';
                contact.time = '';
                return;
            }

            // 找到最后一天的消息
            const lastDay = msgDays[msgDays.length - 1];
            const lastMsgs = lastDay.messages;
            if (!lastMsgs || lastMsgs.length === 0) {
                contact.preview = '';
                contact.time = '';
                return;
            }

            const lastMsg = lastMsgs[lastMsgs.length - 1];
            contact.preview = lastMsg.content;
            contact.time = lastMsg.time;
        });

        // 按时间字符串排序，字符串格式是 HH:MM:SS，自然顺序正确
        appData.contacts.sort((a, b) => {
            const aMsg = appData.messages[a.id];
            const bMsg = appData.messages[b.id];
            let aLast = '';
            if (aMsg && aMsg.length > 0) {
                const lastDay = aMsg[aMsg.length - 1];
                if (lastDay.messages && lastDay.messages.length > 0) {
                    const lastMsg = lastDay.messages[lastDay.messages.length - 1];
                    aLast = `${lastDay.date} ${lastMsg.time}`;
                }
            }
            let bLast = '';
            if (bMsg && bMsg.length > 0) {
                const lastDay = bMsg[bMsg.length - 1];
                if (lastDay.messages && lastDay.messages.length > 0) {
                    const lastMsg = lastDay.messages[lastDay.messages.length - 1];
                    bLast = `${lastDay.date} ${lastMsg.time}`;
                }
            }
            return bLast.localeCompare(aLast);
        });


        renderContacts(appData.contacts);

        if (appData.contacts.length > 0) {
            selectContact(appData.contacts[0].id);
        }
    })
    .catch(err => {
        alert('加载数据失败，请检查 data.json 文件是否存在或格式是否正确');
        console.error(err);
    });
}


// 绑定各种事件
function bindEvents() {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-btn');
    const searchInput = document.getElementById('search-contacts');
    const themeToggle = document.getElementById('theme-toggle');

    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
        sendButton.disabled = !this.value.trim();
    });

    sendButton.addEventListener('click', sendMessage);

    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('light');
    });

    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        document.querySelectorAll('.contact-item').forEach(contact => {
            const name = contact.querySelector('.contact-name').textContent.toLowerCase();
            contact.style.display = name.includes(searchTerm) ? 'flex' : 'none';
        });
    });

    setupWindowControls();
}

// 渲染联系人列表
function renderContacts(contacts) {
    const contactList = document.getElementById('contact-list');
    contactList.innerHTML = '';

    const recentHeader = document.createElement('div');
    recentHeader.className = 'contact-header';
    recentHeader.textContent = '最近聊天';
    contactList.appendChild(recentHeader);

    contacts.forEach(contact => {
        const contactItem = document.createElement('div');
        contactItem.className = 'contact-item';
        contactItem.dataset.id = contact.id;

    contactItem.innerHTML = `
        <div class="contact-avatar">
            <span>${contact.name ? contact.name.charAt(0) : '?'}</span>
            <div class="contact-status ${contact.status === 'offline' ? 'status-offline' : ''}"></div>
        </div>
        <div class="contact-details">
            <div class="contact-name">${contact.name}</div>
            <div class="contact-preview">${contact.preview}</div>
        </div>
        <div class="contact-time">${contact.time || ''}</div>
`;


        contactItem.addEventListener('click', () => {
            selectContact(contact.id);
        });

        contactList.appendChild(contactItem);
    });
}

// 选中联系人
function selectContact(contactId) {
    currentContactId = contactId;

    document.querySelectorAll('.contact-item').forEach(item => {
        item.classList.toggle('active', item.dataset.id == contactId);
    });

    const contact = getContactById(contactId);
    if (contact) {
        document.getElementById('current-contact-avatar').textContent = contact.name[0];

        document.getElementById('current-contact-name').textContent = contact.name;

        const statusText = contact.status === 'online' ? '在线' : '离线';
        document.getElementById('current-contact-status').textContent = statusText;

        // ✅ 设置 IP 文本（如果没有就显示"未知"）
        document.getElementById('current-contact-address').textContent = ` ${contact.address || ''}`;
    }


    loadMessages(contactId);
}

function getContactById(contactId) {
    return appData.contacts.find(contact => contact.id == contactId);
}

// 载入消息
function loadMessages(contactId) {
    const messages = appData.messages[contactId] || [];
    renderMessages(messages);
}

// 渲染消息
function renderMessages(messageData) {
    const messageHistory = document.getElementById('message-history');
    const newMessages = document.getElementById('new-messages');

    messageHistory.innerHTML = '';
    newMessages.innerHTML = '';

    if (!messageData || messageData.length === 0) {
        const noMessages = document.createElement('div');
        noMessages.className = 'message-day';
        noMessages.textContent = '无历史消息';
        messageHistory.appendChild(noMessages);
        return;
    }

    messageData.forEach(day => {
        const dayElement = document.createElement('div');
        dayElement.className = 'message-day';
        dayElement.textContent = day.date;
        messageHistory.appendChild(dayElement);

        day.messages.forEach(msg => {
            const messageElement = document.createElement('div');
            messageElement.className = `message-bubble message-${msg.sender === 'user' ? 'sent' : 'receive'}`;
            let contentHtml = '';
            if (typeof msg.content === 'string' && msg.content.startsWith('图片: ')) {
                // 提取图片文件名
                const imgName = msg.content.replace('图片: ', '').trim();
                const imgSrc = `./image/${imgName}`;
                contentHtml = `<img src="${imgSrc}" alt="图片" style="max-width: 100%; max-height: 300px;">`;
            } else {
                contentHtml = msg.content;
            }
            messageElement.innerHTML = `
                ${contentHtml}
                <div class="message-time">${msg.time}</div>
            `;
            messageHistory.appendChild(messageElement);
        });
    });

    scrollToBottom();
}

document.addEventListener('DOMContentLoaded', function() {
    // 获取 chat-action 和其内部的下拉菜单及按钮
    const chatActions = document.querySelectorAll('.chat-action');
    const dropdownMenu = chatActions[2].querySelector('.dropdown-menu');  // 获取第三个 chat-action 中的 dropdown-menu
    const addFriendBtn = dropdownMenu.querySelector('.add-friend');
    const removeFriendBtn = dropdownMenu.querySelector('.remove-friend');

    // 确保下拉菜单默认是隐藏的
    dropdownMenu.style.display = 'none';

    // 鼠标移到 chat-action 显示下拉菜单
    chatActions[2].addEventListener('mouseenter', function() {
        dropdownMenu.style.display = 'block';
    });

    // 鼠标移出 chat-action 隐藏下拉菜单
    chatActions[2].addEventListener('mouseleave', function() {
        dropdownMenu.style.display = 'none';
    });

    // 阻止点击下拉菜单内元素时，隐藏菜单
    dropdownMenu.addEventListener('mouseenter', function(e) {
        e.stopPropagation();  // 防止事件冒泡
        dropdownMenu.style.display = 'block';  // 保持显示
    });

    // 鼠标移出下拉菜单时隐藏菜单
    dropdownMenu.addEventListener('mouseleave', function() {
        dropdownMenu.style.display = 'none';
    });

    // 点击 "添加好友" 按钮
    addFriendBtn.addEventListener('click', function() {
        alert('添加好友功能待实现');
        dropdownMenu.style.display = 'none'; // 隐藏菜单
    });

    // 点击 "删除好友" 按钮
    removeFriendBtn.addEventListener('click', function() {
        alert('删除好友功能待实现');
        dropdownMenu.style.display = 'none'; // 隐藏菜单
    });
});


document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input'); // 获取文件输入框
    const paperclipIcon = document.querySelector('.input-action i'); // 获取纸夹图标

    // 点击纸夹图标触发文件选择框
    paperclipIcon.addEventListener('click', function() {
        fileInput.click(); // 点击文件选择框
    });

    // 监听文件选择框的变化（文件被选择时触发）
    fileInput.addEventListener('change', function(event) {
        const file = event.target.files[0]; // 获取选中的文件

        if (file) {
            // 如果选中了文件，则先显示图片
            displayImage(file);
        }
    });
});

// 显示图片的函数
function displayImage(file) {
    const reader = new FileReader();

    reader.onload = function(event) {
        // 读取文件完成后的事件，event.target.result 为图片的 Data URL
        const imgDataUrl = event.target.result;

        // 生成聊天消息并显示
        const messageElement = document.createElement('div');
        messageElement.className = 'message-bubble message-sent';

        messageElement.innerHTML = `
            <img src="${imgDataUrl}" alt="Uploaded Image" style="max-width: 100%; max-height: 300px;">
            <div class="message-time">${getCurrentTimeWithSeconds()}</div>
        `;

        document.getElementById('new-messages').appendChild(messageElement);

        scrollToBottom();

        // 调用后端保存图片消息
        if (backend && backend.saveImageMessage) {
            backend.saveImageMessage(
                currentContactId,
                'user',
                imgDataUrl,
                getCurrentTimeWithSeconds(),
                new Date().toLocaleDateString()
            );
            setTimeout(refreshCurrentContactMessages, 500); // 延迟刷新，确保后端写入
        }
    };

    // 将图片转换为 Data URL
    reader.readAsDataURL(file);
}

// 获取当前时间（以秒为单位）
function getCurrentTimeWithSeconds() {
    const now = new Date();
    const hh = now.getHours().toString().padStart(2, '0');
    const mm = now.getMinutes().toString().padStart(2, '0');
    const ss = now.getSeconds().toString().padStart(2, '0');
    return `${hh}:${mm}:${ss}`;
}

// 滚动到聊天窗口底部
function scrollToBottom() {
    const messageArea = document.querySelector('.messages-container');
    messageArea.scrollTop = messageArea.scrollHeight;
}




// 发送消息，保存到后端
function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const messageText = messageInput.value.trim();

    if (!messageText || !currentContactId) return;

    const now = new Date();
    const timeString = getCurrentTimeWithSeconds();

    const todayDate = now.toLocaleDateString();

    // 1. 本地保存
    if (!appData.messages[currentContactId]) {
        appData.messages[currentContactId] = [];
    }

    let dayEntry = appData.messages[currentContactId].find(day => day.date === todayDate);
    if (!dayEntry) {
        dayEntry = { date: todayDate, messages: [] };
        appData.messages[currentContactId].push(dayEntry);
    }

    dayEntry.messages.push({
        sender: 'user',
        content: messageText,
        time: timeString
    });

    // 2. 界面更新
    const messageElement = document.createElement('div');
    messageElement.className = 'message-bubble message-sent';
    messageElement.innerHTML = `
        ${messageText}
        <div class="message-time">${timeString}</div>
    `;
    document.getElementById('new-messages').appendChild(messageElement);

    messageInput.value = '';
    messageInput.style.height = 'auto';
    document.getElementById('send-btn').disabled = true;
    scrollToBottom();

    // 3. 调用后端保存
    if (backend && backend.saveMessage) {
        backend.saveMessage(currentContactId, 'user', messageText, timeString, todayDate);
        console.log('调用后端保存消息');
    } else {
        console.warn('后端未连接，消息未保存');
    }

    // 发送完后刷新聊天消息
    setTimeout(refreshCurrentContactMessages, 500); // 延迟保证后端写完
}

function setupWindowControls() {
    const minimizeBtn = document.querySelector('.minimize');
    const maximizeBtn = document.querySelector('.maximize');
    const closeBtn = document.querySelector('.close');

    minimizeBtn.addEventListener('click', function() {
        this.style.opacity = '0.7';
        setTimeout(() => this.style.opacity = '1', 300);
    });

    maximizeBtn.addEventListener('click', function() {
        document.querySelector('.desktop-app').classList.toggle('fullscreen');
        const icon = this.querySelector('i');
        if (icon.classList.contains('fa-square')) {
            icon.classList.replace('fa-square', 'fa-clone');
            icon.classList.add('fas');
            icon.style.transform = 'rotate(180deg)';
        } else {
            icon.classList.replace('fa-clone', 'fa-square');
            icon.classList.remove('fas');
            icon.classList.add('far');
            icon.style.transform = '';
        }
    });

    closeBtn.addEventListener('click', function() {
        this.style.opacity = '0.7';
        setTimeout(() => {
            const app = document.querySelector('.desktop-app');
            app.style.transform = 'scale(0.9)';
            app.style.opacity = '0';
            setTimeout(() => alert('应用程序已关闭 - 此提示仅用于演示'), 300);
        }, 300);
    });
}

// ===================== 好友管理相关接口 =====================

/**
 * 添加好友接口（向服务器请求，暂未启用）
 * @param {string} friendName - 新好友昵称
 * @param {string} friendId - 新好友ID
 */
// function addFriend(friendName, friendId) {
//     // 示例：向服务器发送添加好友请求
//     fetch('/api/add_friend', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ name: friendName, id: friendId })
//     })
//     .then(response => response.json())
//     .then(data => {
//         if (data.success) {
//             // 成功后可刷新联系人列表
//             // refreshContacts();
//         } else {
//             alert('添加好友失败: ' + data.message);
//         }
//     })
//     .catch(err => {
//         alert('网络错误，添加好友失败');
//     });
// }

/**
 * 删除好友接口（向服务器请求，暂未启用）
 * @param {string} friendId - 要删除的好友ID
 */
// function deleteFriend(friendId) {
//     // 示例：向服务器发送删除好友请求
//     fetch('/api/delete_friend', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ id: friendId })
//     })
//     .then(response => response.json())
//     .then(data => {
//         if (data.success) {
//             // 成功后可刷新联系人列表
//             // refreshContacts();
//         } else {
//             alert('删除好友失败: ' + data.message);
//         }
//     })
//     .catch(err => {
//         alert('网络错误，删除好友失败');
//     });
// }
