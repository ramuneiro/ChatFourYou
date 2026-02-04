// Socket.IOの接続
const socket = io();

// DOM要素
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const usernameInput = document.getElementById('username-input');
const loginBtn = document.getElementById('login-btn');
const loginError = document.getElementById('login-error');
const currentUsername = document.getElementById('current-username');
const logoutBtn = document.getElementById('logout-btn');
const messagesContainer = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const imageInput = document.getElementById('image-input');
const imageBtn = document.getElementById('image-btn');
const imagePreview = document.getElementById('image-preview');
const previewImg = document.getElementById('preview-img');
const cancelImageBtn = document.getElementById('cancel-image-btn');

let username = null;
let selectedImage = null;

// ログイン処理
loginBtn.addEventListener('click', login);
usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') login();
});

function login() {
    const inputUsername = usernameInput.value.trim();
    
    if (!inputUsername) {
        loginError.textContent = 'ユーザー名を入力してください';
        return;
    }
    
    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username: inputUsername })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            username = data.username;
            currentUsername.textContent = username;
            loginScreen.classList.add('hidden');
            chatScreen.classList.remove('hidden');
            loadMessages();
            loginError.textContent = '';
        } else {
            loginError.textContent = data.message;
        }
    })
    .catch(error => {
        console.error('ログインエラー:', error);
        loginError.textContent = 'ログインに失敗しました';
    });
}

// ログアウト処理
logoutBtn.addEventListener('click', () => {
    username = null;
    chatScreen.classList.add('hidden');
    loginScreen.classList.remove('hidden');
    usernameInput.value = '';
    messagesContainer.innerHTML = '';
});

// メッセージ送信
sendBtn.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// 画像選択ボタン
imageBtn.addEventListener('click', () => {
    imageInput.click();
});

// 画像ファイル選択時
imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleImageSelect(file);
    }
});

// 画像キャンセルボタン
cancelImageBtn.addEventListener('click', () => {
    selectedImage = null;
    imagePreview.classList.add('hidden');
    imageInput.value = '';
});

// ドラッグ&ドロップイベント
messagesContainer.addEventListener('dragover', (e) => {
    e.preventDefault();
    messagesContainer.classList.add('drag-over');
});

messagesContainer.addEventListener('dragleave', () => {
    messagesContainer.classList.remove('drag-over');
});

messagesContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    messagesContainer.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.match('image/(jpeg|png)')) {
        handleImageSelect(file);
    } else {
        alert('JPEG または PNG 画像のみアップロードできます');
    }
});

function handleImageSelect(file) {
    // ファイルサイズ（16MB）
    if (file.size > 16 * 1024 * 1024) {
        alert('ファイルサイズは16MB以下にしてください');
        return;
    }
    
    selectedImage = file;
    
    // プレビュー表示
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        imagePreview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
}

function sendMessage() {
    const message = messageInput.value.trim();
    
    // 画像がある場合は画像を送信
    if (selectedImage) {
        uploadAndSendImage(message);
        return;
    }
    
    if (!message) return;
    
    socket.emit('send_message', { message: message });
    messageInput.value = '';
}

async function uploadAndSendImage(message) {
    const formData = new FormData();
    formData.append('image', selectedImage);
    
    try {
        const response = await fetch('/upload-image', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 画像URLとメッセージを送信
            socket.emit('send_message', { 
                message: message || '画像を送信しました',
                image_url: data.image_url
            });
            
            // リセット
            selectedImage = null;
            imagePreview.classList.add('hidden');
            imageInput.value = '';
            messageInput.value = '';
        } else {
            alert('画像のアップロードに失敗しました: ' + data.message);
        }
    } catch (error) {
        console.error('画像アップロードエラー:', error);
        alert('画像のアップロードに失敗しました');
    }
}

// メッセージを読み込み
function loadMessages() {
    fetch('/messages')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            messagesContainer.innerHTML = '';
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(msg => displayMessage(msg));
            }
            scrollToBottom();
        })
        .catch(error => {
            console.error('メッセージ読み込みエラー:', error);
            messagesContainer.innerHTML = '<div class="error-message">メッセージの読み込みに失敗しました</div>';
        });
}

// メッセージを表示
function displayMessage(msg) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    // msg_id優先、なければid
    const messageId = msg.msg_id || msg.id;
    messageDiv.dataset.messageId = messageId;

    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';

    const usernameSpan = document.createElement('span');
    usernameSpan.className = 'message-username';
    usernameSpan.textContent = msg.username || '';

    const timeSpan = document.createElement('span');
    timeSpan.className = 'message-time';
    timeSpan.textContent = formatTime(msg.created_at);

    headerDiv.appendChild(usernameSpan);
    headerDiv.appendChild(timeSpan);

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // 画像がある場合は画像を表示
    if (msg.image_url) {
        const img = document.createElement('img');
        img.src = msg.image_url;
        img.className = 'message-image';
        img.alt = 'アップロード画像';
        contentDiv.appendChild(img);
    }
    
    // テキストメッセージを表示
    const textDiv = document.createElement('div');
    const messageText = msg.context || msg.message || '';
    // URLをリンクに変換
    textDiv.innerHTML = linkifyText(messageText);
    contentDiv.appendChild(textDiv);

    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(contentDiv);

    // 削除ボタンを追加（全ユーザーが削除可能）
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete-btn';
    deleteBtn.textContent = '削除';
    deleteBtn.onclick = () => deleteMessage(messageId);
    messageDiv.appendChild(deleteBtn);

    messagesContainer.appendChild(messageDiv);
}

// メッセージ削除
function deleteMessage(messageId) {
    if (!confirm('このメッセージを削除しますか?')) return;
    
    fetch(`/messages/${messageId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            alert('削除に失敗しました');
        }
    })
    .catch(error => {
        console.error('削除エラー:', error);
        alert('削除に失敗しました');
    });
}

// 時刻フォーマット
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
}

// テキスト内のURLをリンクに変換
function linkifyText(text) {
    // URLを検出する正規表現
    const urlPattern = /(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
    
    // HTMLエスケープ
    const escapeHtml = (str) => {
        return str.replace(/[&<>"']/g, (match) => {
            const escape = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            };
            return escape[match];
        });
    };
    
    // テキストをエスケープしてから改行を<br>に変換し、URLをリンクに変換
    const escapedText = escapeHtml(text);
    const textWithBreaks = escapedText.replace(/\n/g, '<br>');
    return textWithBreaks.replace(urlPattern, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

// スクロール
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

socket.on('connect', () => {
    console.log('サーバーに接続しました');
});

socket.on('disconnect', () => {
    console.log('サーバーから切断されました');
});

socket.on('new_message', (data) => {
    displayMessage(data);
    scrollToBottom();
});

socket.on('message_deleted', (data) => {
    const messageDiv = document.querySelector(`[data-message-id="${data.msg_id}"]`);
    if (messageDiv) {
        messageDiv.remove();
    }
});

socket.on('error', (data) => {
    alert(data.message);
});
