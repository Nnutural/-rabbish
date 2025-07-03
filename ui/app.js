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


// 初始化 QWebChannel 和绑定 backend/audioRecorder 对象
function initWebChannel() {
    if (typeof QWebChannel === 'undefined') {
        console.error('QWebChannel 未定义');
        return;
    }
    new QWebChannel(qt.webChannelTransport, function(channel) {
        backend = channel.objects.backend;
        if (channel.objects.audioRecorder) {
            window.audioRecorder = channel.objects.audioRecorder;
            // 录音完成信号：文件名+识别文本
            audioRecorder.recordingFinished.connect(function(fileName, recognizedText) {
                // 保存消息
                if (backend && backend.saveMessage) {
                    const now = new Date();
                    const timeString = getCurrentTimeWithSeconds();
                    const todayDate = now.toLocaleDateString();
                    backend.saveMessage(currentContactId, 'user', '语音: ' + fileName, timeString, todayDate);
                    // 延迟写入 recognized_text 字段
                    setTimeout(function() {
                        const msgs = appData.messages[currentContactId];
                        if (msgs && msgs.length > 0) {
                            const lastDay = msgs[msgs.length - 1];
                            if (lastDay.messages && lastDay.messages.length > 0) {
                                // 找到最后一条语音消息
                                for (let i = lastDay.messages.length - 1; i >= 0; i--) {
                                    const msg = lastDay.messages[i];
                                    if (msg.content === '语音: ' + fileName) {
                                        msg.recognized_text = recognizedText;
                                        if (backend && backend.saveAllMessages) {
                                            backend.saveAllMessages(appData.messages);
                                        }
                                        break;
                                    }
                                }
                            }
                        }
                        refreshCurrentContactMessages();
                    }, 800);
                }
            });
        }
        if (channel.objects.stego) {
            window.stego = channel.objects.stego;
            console.log('stego对象已注册', window.stego);
        }
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
    setupAudioRecording(); // 新增，绑定录音按钮

    // Emoji Picker 逻辑
    const emojiBtn = document.getElementById('emoji-btn');
    const emojiPicker = document.getElementById('emoji-picker');
    const messageInput = document.getElementById('message-input');
    // 常用emoji
    const emojis = [
        '😀','😃','😄','😁','😆','😅','😂','🤣','😊','😇','🙂','🙃','😉','😌','😍','🥰','😘','😗','😙','😚','😋','😜','😝','😛','🤑','🤗','🤭','🤫','🤔','🤐','😐','😑','😶','😏','😒','🙄','😬','🤥','😌','😔','😪','🤤','😴','😷','🤒','🤕','🤢','🤮','🥵','🥶','🥴','😵','🤯','🤠','🥳','😎','🤓','🧐','😕','😟','🙁','☹️','😮','😯','😲','😳','🥺','😦','😧','😨','😰','😥','😢','😭','😱','😖','😣','😞','😓','😩','😫','🥱','😤','😡','😠','🤬','😈','👿','💀','☠️','🤡','👹','👺','👻','👽','👾','🤖','😺','😸','😹','😻','😼','😽','🙀','😿','😾','👍','👎','👌','✌️','🤞','🤟','🤘','🤙','🖕','🖐️','✋','👏','🙏','💪','🦾','🦵','🦶','👀','👁️','👅','👄','💋','🧠','🦷','🦴','👃','👂','🦻','👶','🧒','👦','👧','🧑','👱‍♂️','👱‍♀️','👨','👩','🧓','👴','👵','🙍','🙎','🙅','🙆','💁','🙋','🧏','🙇','🤦','🤷','💆','💇','🚶','🏃','💃','🕺','🕴️','👯','🧖','🧘','🛌','🧑‍🤝‍🧑','👭','👫','👬','💏','💑','👪','🗣️','👤','👥','🫂','👣','🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐵','🙈','🙉','🙊','🐒','🐔','🐧','🐦','🐤','🐣','🐥','🦆','🦅','🦉','🦇','🐺','🐗','🐴','🦄','🐝','🪱','🐛','🦋','🐌','🐞','🐜','🪰','🪲','🪳','🦟','🦗','🕷️','🕸️','🦂','🐢','🐍','🦎','🦖','🦕','🐙','🦑','🦐','🦞','🦀','🐡','🐠','🐟','🐬','🐳','🐋','🦈','🐊','🐅','🐆','🦓','🦍','🦧','🐘','🦣','🦛','🦏','🐪','🐫','🦒','🦘','🦬','🐃','🐂','🐄','🐎','🐖','🐏','🐑','🦙','🐐','🦌','🐕','🐩','🦮','🐕‍🦺','🐈','🐓','🦃','🦤','🦚','🦜','🦢','🦩','🕊️','🐇','🦝','🦨','🦡','🦦','🦥','🐁','🐀','🐿️','🦔'
    ];
    emojiPicker.innerHTML = emojis.map(e => `<span>${e}</span>`).join('');

    emojiBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        emojiPicker.style.display = emojiPicker.style.display === 'none' ? 'flex' : 'none';
    });
    // 点击页面其他地方关闭emoji
    document.addEventListener('click', function(e) {
        if (emojiPicker.style.display !== 'none') {
            emojiPicker.style.display = 'none';
        }
    });
    emojiPicker.addEventListener('click', function(e) {
        if (e.target.tagName === 'SPAN') {
            insertAtCursor(messageInput, e.target.textContent);
            emojiPicker.style.display = 'none';
        }
    });

    // 隐写按钮逻辑
    const stegoBtn = document.getElementById('stego-btn');
    if (stegoBtn) {
        stegoBtn.addEventListener('click', function() {
            showStegoModal();
        });
    }
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

        // 统计未读消息数
        let unreadCount = 0;
        const messages = appData.messages[contact.id] || [];
        messages.forEach(day => {
            day.messages.forEach(msg => {
                if (msg.sender === 'contact' && msg.read === false) {
                    unreadCount++;
                }
            });
        });

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
            ${unreadCount > 0 ? `<span class='unread-badge'>${unreadCount > 99 ? '99+' : unreadCount}</span>` : ''}
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

    // 新增：将所有对方发来的消息设为已读
    const messages = appData.messages[contactId] || [];
    let hasUnread = false;
    messages.forEach(day => {
        day.messages.forEach(msg => {
            if (msg.sender === 'contact' && msg.read === false) {
                msg.read = true;
                hasUnread = true;
            }
        });
    });
    if (hasUnread) {
        renderContacts(appData.contacts);
        // 持久化到data.json
        if (backend && backend.saveAllMessages) {
            backend.saveAllMessages(appData.messages);
        }
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

    let needRefresh = false;

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
                const imgName = msg.content.replace('图片: ', '').trim();
                const imgSrc = `./image/${imgName}`;
                // 检查是否为隐写图片
                if (imgName.endsWith('_stego.png')) {
                    if (msg.stego) {
                        // 已有stego字段，直接显示
                        contentHtml = `<img src="${imgSrc}" alt="隐写图片" style="max-width: 100%; max-height: 300px;">
                            <div class='stego-text' style='color:#d2691e;font-size:14px;margin-top:4px;'>隐藏信息：${msg.stego}</div>`;
                    } else if (window.stego && stego.decodeStegoImage) {
                        // 没有stego字段，自动解析
                        stego.decodeStegoImage(imgName, function(hiddenText) {
                            if (hiddenText && hiddenText.trim()) {
                                msg.stego = hiddenText;
                                needRefresh = true;
                                // 持久化到data.json
                                if (backend && backend.saveAllMessages && appData && appData.messages) {
                                    backend.saveAllMessages(appData.messages);
                                }
                                // 重新渲染
                                renderMessages(messageData);
                            }
                        });
                        // 先只显示图片，解析后自动刷新
                        contentHtml = `<img src="${imgSrc}" alt="隐写图片" style="max-width: 100%; max-height: 300px;">`;
                    } else {
                        // 没有stego后端，直接显示图片
                        contentHtml = `<img src="${imgSrc}" alt="隐写图片" style="max-width: 100%; max-height: 300px;">`;
                    }
                } else {
                    // 普通图片
                    contentHtml = `<img src="${imgSrc}" alt="图片" style="max-width: 100%; max-height: 300px;">`;
                }
            } else if (typeof msg.content === 'string' && msg.content.startsWith('语音: ')) {
                const audioName = msg.content.replace('语音: ', '').trim();
                const audioSrc = `./audio/${audioName}`;
                contentHtml = `<audio controls><source src="${audioSrc}" type="audio/wav">Your browser does not support the audio element.</audio>`;
                // 如果有识别文本，显示在下方，否则显示识别按钮
                if (msg.recognized_text && msg.recognized_text.trim()) {
                    contentHtml += `<div class="recognized-text" style="color:#007bff;font-size:14px;margin-top:4px;">识别文本：${msg.recognized_text}</div>`;
                } else {
                    contentHtml += `<button class="recognize-btn" data-audio="${audioName}" style="margin-top:4px; background:none; border:none; cursor:pointer;" title="语音转文字"><i class="fas fa-wave-square" style="font-size:18px;color:#007bff;"></i></button>`;
                }
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

    // 绑定识别按钮点击事件
    setTimeout(() => {
        document.querySelectorAll('.recognize-btn').forEach(btn => {
            btn.onclick = function() {
                const audioName = btn.getAttribute('data-audio');
                if (window.audioRecorder && audioRecorder.recognizeSpeechFromFile) {
                    audioRecorder.recognizeSpeechFromFile(audioName, function(text) {
                        // 找到对应消息，写入 recognized_text 字段
                        for (const day of messageData) {
                            for (const msg of day.messages) {
                                if (msg.content === '语音: ' + audioName) {
                                    msg.recognized_text = text;
                                    if (backend && backend.saveAllMessages) {
                                        backend.saveAllMessages(appData.messages);
                                    }
                                    renderMessages(messageData);
                                    return;
                                }
                            }
                        }
                    });
                } else {
                    alert('后端未实现 recognizeSpeechFromFile');
                }
            };
        });
    }, 0);

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
        time: timeString,
        read: true
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

// 插入emoji到光标处
function insertAtCursor(input, text) {
    const start = input.selectionStart;
    const end = input.selectionEnd;
    const value = input.value;
    input.value = value.slice(0, start) + text + value.slice(end);
    input.selectionStart = input.selectionEnd = start + text.length;
    input.focus();
}

// 发送表情包消息
function sendEmojiMessage(emoji) {
    if (!currentContactId) return;
    const now = new Date();
    const timeString = getCurrentTimeWithSeconds();
    const todayDate = now.toLocaleDateString();

    // 本地保存
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
        content: emoji,
        time: timeString,
        read: true
    });

    // 界面更新
    const messageElement = document.createElement('div');
    messageElement.className = 'message-bubble message-sent';
    messageElement.innerHTML = `
        ${emoji}
        <div class="message-time">${timeString}</div>
    `;
    document.getElementById('new-messages').appendChild(messageElement);
    scrollToBottom();

    // 后端保存
    if (backend && backend.saveMessage) {
        backend.saveMessage(currentContactId, 'user', emoji, timeString, todayDate);
    }

    // 联系人置顶
    const idx = appData.contacts.findIndex(c => c.id == currentContactId);
    if (idx > 0) {
        const [contact] = appData.contacts.splice(idx, 1);
        appData.contacts.unshift(contact);
        renderContacts(appData.contacts);
    }
    setTimeout(refreshCurrentContactMessages, 500);
}

function setupAudioRecording() {
    const micBtn = document.getElementById('mic-action');
    if (!micBtn) {
        console.error('未找到麦克风按钮');
        return;
    }
    let micIcon = micBtn.querySelector('i');
    let isRecording = false;
    micBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        if (!window.audioRecorder) {
            alert('未检测到Qt录音模块');
            return;
        }
        if (!isRecording) {
            window.audioRecorder.startRecording();
            isRecording = true;
            micIcon.classList.add('recording');
            micIcon.style.color = '#ff3b30';
            micBtn.title = '点击结束录音';
        } else {
            window.audioRecorder.stopRecording();
            isRecording = false;
            micIcon.classList.remove('recording');
            micIcon.style.color = '';
            micBtn.title = '点击开始录音';
        }
    });
}

function sendAudioMessage(filePath) {
    if (!currentContactId) return;
    const now = new Date();
    const timeString = getCurrentTimeWithSeconds();
    const todayDate = now.toLocaleDateString();
    if (backend && backend.saveMessage) {
        backend.saveMessage(currentContactId, 'user', '语音: ' + filePath, timeString, todayDate);
        console.log('调用后端保存语音消息');
    } else {
        alert('后端未连接，语音消息未保存');
    }
    setTimeout(refreshCurrentContactMessages, 500);
}

// 隐写弹窗及逻辑
function showStegoModal() {
    // 如果已存在弹窗则不重复创建
    if (document.getElementById('stego-modal')) {
        document.getElementById('stego-modal').style.display = 'flex';
        return;
    }
    // 创建弹窗
    const modal = document.createElement('div');
    modal.id = 'stego-modal';
    modal.style = 'position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:999;background:rgba(0,0,0,0.32);display:flex;align-items:center;justify-content:center;';
    modal.innerHTML = `
      <div class="stego-modal-content">
        <div class="stego-modal-title">图片隐写</div>
        <div class="stego-modal-section">
          <label class="stego-upload-label">
            <input type="file" id="stego-image-input" accept="image/*" hidden>
            <span class="stego-upload-btn">选择图片</span>
          </label>
          <img id="stego-image-preview" class="stego-image-preview" style="display:none;">
        </div>
        <div class="stego-modal-section">
          <textarea id="stego-text-input" maxlength="100" placeholder="请输入要隐藏的文字（支持中文，最多100字）"></textarea>
          <div class="stego-text-count"><span id="stego-char-count">0</span>/100</div>
        </div>
        <div class="stego-modal-actions">
          <button id="stego-encode-btn" class="stego-main-btn">生成隐写图片</button>
          <button id="stego-cancel-btn" class="stego-cancel-btn">取消</button>
        </div>
        <div id="stego-result" class="stego-result"></div>
      </div>
    `;
    document.body.appendChild(modal);
    // 关闭按钮
    document.getElementById('stego-cancel-btn').onclick = function() {
        modal.style.display = 'none';
    };
    // 图片选择按钮（移除多余的 JS 绑定，label 默认行为即可）
    // document.querySelector('.stego-upload-btn').onclick = function() {
    //     document.getElementById('stego-Image-input').click();
    // };
    // 图片预览
    document.getElementById('stego-Image-input').onchange = function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(evt) {
                document.getElementById('stego-Image-preview').src = evt.target.result;
                document.getElementById('stego-Image-preview').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    };
    // 字数统计
    const textInput = document.getElementById('stego-text-input');
    const charCount = document.getElementById('stego-char-count');
    textInput.addEventListener('input', function() {
        charCount.textContent = this.value.length;
    });
    // 生成隐写图片
    document.getElementById('stego-encode-btn').onclick = function() {
        const fileInput = document.getElementById('stego-Image-input');
        const text = textInput.value.trim();
        const resultDiv = document.getElementById('stego-result');
        if (!fileInput.files[0]) {
            resultDiv.textContent = '请先选择图片';
            return;
        }
        if (!text) {
            resultDiv.textContent = '请输入要隐藏的文字';
            return;
        }
        // 读取图片为base64
        const reader = new FileReader();
        reader.onload = function(evt) {
            const base64img = evt.target.result;
            // 调用后端 stego encode，传入发送人序号
            if (window.stego && stego.encodeStegoImage) {
                document.getElementById('stego-encode-btn').disabled = true;
                resultDiv.textContent = '生成中...';
                stego.encodeStegoImage(String(currentContactId), base64img, text, function(stegoImgPath) {
                    resultDiv.textContent = '隐写图片已生成并发送！';
                    // 立即插入到界面
                    const messageElement = document.createElement('div');
                    messageElement.className = 'message-bubble message-sent';
                    const imgSrc = `./image/${stegoImgPath}`;
                    messageElement.innerHTML = `
                        <img src="${imgSrc}" alt="隐写图片" style="max-width: 100%; max-height: 300px;">
                        <div class="message-time">${getCurrentTimeWithSeconds()}</div>
                    `;
                    document.getElementById('new-messages').appendChild(messageElement);
                    scrollToBottom();
                    // 这里可以自动发送图片消息
                    if (backend && backend.saveMessage && currentContactId) {
                        const now = new Date();
                        const timeString = getCurrentTimeWithSeconds();
                        const todayDate = now.toLocaleDateString();
                        backend.saveMessage(currentContactId, 'user', '图片: ' + stegoImgPath, timeString, todayDate);
                    }
                    setTimeout(refreshCurrentContactMessages, 1200);
                    setTimeout(() => { modal.style.display = 'none'; }, 1200);
                });
            } else {
                resultDiv.textContent = '后端未实现 encodeStegoImage';
            }
        };
        reader.readAsDataURL(fileInput.files[0]);
    };
}
