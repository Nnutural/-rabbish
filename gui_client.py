import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import queue
import os
import sys
import time
from datetime import datetime
import json
import shutil

# 导入现有的模块
import schema as S
import Transaction_Client as T
import p2p as P
import Contacts as C
import socket as skt
import ssl
import uuid
import datetime as dt
from serializer import serialize, deserialize

class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P 聊天客户端")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # 客户端状态变量
        self.current_user = None
        self.user_id = None
        self.ssl_connect_sock = None
        self.p2p_server_sock = None
        self.my_p2p_port = None
        self.contacts_map = {}
        self.current_chat_friend = None
        self.current_chat_socket = None
        self.contact_manager = None
        
        # 消息队列用于线程间通信
        self.message_queue = queue.Queue()
        
        # 创建界面
        self.create_widgets()
        
        # 启动消息处理线程
        self.message_thread = threading.Thread(target=self.process_messages, daemon=True)
        self.message_thread.start()
        
        # 定期检查消息队列
        self.root.after(100, self.check_message_queue)

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 登录框架
        self.login_frame = ttk.LabelFrame(main_frame, text="登录/注册", padding=10)
        self.login_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 用户名输入
        ttk.Label(self.login_frame, text="用户名:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(self.login_frame, textvariable=self.username_var, width=20)
        self.username_entry.grid(row=0, column=1, padx=(0, 10))
        
        # 密码输入
        ttk.Label(self.login_frame, text="密码:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self.login_frame, textvariable=self.password_var, show="*", width=20)
        self.password_entry.grid(row=0, column=3, padx=(0, 10))
        
        # 邮箱输入（注册用）
        ttk.Label(self.login_frame, text="邮箱:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(self.login_frame, textvariable=self.email_var, width=20)
        self.email_entry.grid(row=1, column=1, padx=(0, 10), pady=(5, 0))
        
        # 按钮框架
        button_frame = ttk.Frame(self.login_frame)
        button_frame.grid(row=1, column=2, columnspan=2, pady=(5, 0))
        
        self.login_btn = ttk.Button(button_frame, text="登录", command=self.login)
        self.login_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.register_btn = ttk.Button(button_frame, text="注册", command=self.register)
        self.register_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.logout_btn = ttk.Button(button_frame, text="注销", command=self.logout, state=tk.DISABLED)
        self.logout_btn.pack(side=tk.LEFT)
        
        # 主内容框架
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧面板 - 通讯录和消息历史
        left_panel = ttk.Frame(content_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        
        # 通讯录框架
        contacts_frame = ttk.LabelFrame(left_panel, text="通讯录", padding=5)
        contacts_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 添加好友按钮
        self.add_friend_btn = ttk.Button(contacts_frame, text="添加好友", command=self.add_friend)
        self.add_friend_btn.pack(pady=(0, 5))
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(contacts_frame, text="刷新通讯录", command=self.refresh_contacts, state=tk.DISABLED)
        self.refresh_btn.pack(pady=(0, 5))
        
        # 通讯录列表框
        self.contacts_listbox = tk.Listbox(contacts_frame, width=30, height=8)
        self.contacts_listbox.pack(fill=tk.BOTH, expand=True)
        self.contacts_listbox.bind('<Double-Button-1>', self.on_contact_select)
        
        # 消息历史框架
        history_frame = ttk.LabelFrame(left_panel, text="消息历史", padding=5)
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        # 历史记录显示
        self.history_display = scrolledtext.ScrolledText(history_frame, width=30, height=15, state=tk.DISABLED)
        self.history_display.pack(fill=tk.BOTH, expand=True)
        
        # 右侧聊天区域
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 聊天标题
        self.chat_title = ttk.Label(right_frame, text="请选择联系人开始聊天", font=('Arial', 12, 'bold'))
        self.chat_title.pack(pady=(0, 5))
        
        # 聊天消息显示区域
        self.chat_display = scrolledtext.ScrolledText(right_frame, height=25, width=60, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 消息输入区域
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill=tk.X)
        
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(input_frame, textvariable=self.message_var, width=50)
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.message_entry.bind('<Return>', self.send_message)
        
        self.send_btn = ttk.Button(input_frame, text="发送", command=self.send_message, state=tk.DISABLED)
        self.send_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 文件发送按钮
        self.file_btn = ttk.Button(input_frame, text="发送文件", command=self.send_file, state=tk.DISABLED)
        self.file_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.image_btn = ttk.Button(input_frame, text="发送图片", command=self.send_image, state=tk.DISABLED)
        self.image_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.audio_btn = ttk.Button(input_frame, text="发送语音", command=self.send_audio, state=tk.DISABLED)
        self.audio_btn.pack(side=tk.LEFT)
        
        # 状态栏
        self.status_var = tk.StringVar(value="未连接")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_label.pack(fill=tk.X, pady=(10, 0))

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            messagebox.showerror("错误", "请输入用户名和密码")
            return
        
        # 在新线程中执行登录
        threading.Thread(target=self._login_thread, args=(username, password), daemon=True).start()

    def _login_thread(self, username, password):
        try:
            self.status_var.set("正在连接服务器...")
            # 创建P2P监听socket
            self.p2p_server_sock, self.my_p2p_port = self.bind_to_free_port()
            if not self.p2p_server_sock:
                self.message_queue.put(("error", "无法绑定P2P端口"))
                return
            # 创建SSL连接
            self.ssl_connect_sock = P.create_secure_connection(
                server_ip_port=("127.0.0.1", 47474),
                ca_file="ca.crt",
                cert_file="client.crt",
                key_file="client_rsa_private.pem.unsecure",
                peer_hostname='SERVER'
            )
            if not self.ssl_connect_sock:
                self.message_queue.put(("error", "连接服务器失败"))
                return
            # 启动P2P监听线程
            listening_thread = threading.Thread(target=P.p2p_listener, args=(self.p2p_server_sock,), daemon=True)
            listening_thread.start()
            # 发送登录消息
            login_msg = S.LoginMsg(
                username=username,
                secret=password,
                port=str(self.my_p2p_port),
                time=int(time.time())
            )
            self.ssl_connect_sock.sendall(serialize(login_msg))
            # 接收响应
            response = T.recv_msg(self.ssl_connect_sock)
            if response and response.tag.name == "SuccessLogin":
                self.current_user = username
                self.user_id = response.user_id
                P.MY_USERNAME = username
                # 移除所有同步/初始化/拉取目录相关代码
                # self.contact_manager = C.ContactManager(username)
                # T.recv_large_data(self.ssl_connect_sock, response.transfer_id, username)
                # T.handle_get_directory(self.ssl_connect_sock, self.current_user)
                # P.init_directory(self.current_user)
                # self.contacts_map = P.contacts_map
                self.message_queue.put(("login_success", username))
            else:
                self.message_queue.put(("error", "登录失败，请检查用户名和密码"))
        except Exception as e:
            self.message_queue.put(("error", f"登录过程中发生错误: {e}"))

    def register(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        email = self.email_var.get().strip()
        
        if not username or not password or not email:
            messagebox.showerror("错误", "请填写完整的注册信息")
            return
        
        # 在新线程中执行注册
        threading.Thread(target=self._register_thread, args=(username, password, email), daemon=True).start()

    def _register_thread(self, username, password, email):
        try:
            self.status_var.set("正在注册...")
            temp_sock = P.create_secure_connection(
                server_ip_port=("127.0.0.1", 47474),
                ca_file="ca.crt",
                cert_file="client.crt",
                key_file="client_rsa_private.pem.unsecure",
                peer_hostname='SERVER'
            )
            if not temp_sock:
                self.message_queue.put(("error", "连接服务器失败"))
                return
            with temp_sock:
                register_msg = S.RegisterMsg(
                    username=username,
                    secret=password,
                    email=email,
                    time=int(time.time())
                )
                temp_sock.sendall(serialize(register_msg))
                response = T.recv_msg(temp_sock)
                if response and response.tag.name == "SuccessRegister":
                    # 注册成功后自动复制sikaiqi/data.json
                    try:
                        src = os.path.join('user', 'sikaiqi', 'data.json')
                        dst_dir = os.path.join('user', username)
                        dst = os.path.join(dst_dir, 'data.json')
                        if not os.path.exists(dst_dir):
                            os.makedirs(dst_dir)
                        shutil.copy(src, dst)
                        print(f"已复制{src}到{dst}")
                    except Exception as e:
                        print(f"复制data.json失败: {e}")
                        self.message_queue.put(("error", f"复制data.json失败: {e}"))
                        return
                    self.message_queue.put(("register_success", username))
                else:
                    self.message_queue.put(("error", "注册失败，用户名可能已存在"))
        except Exception as e:
            self.message_queue.put(("error", f"注册过程中发生错误: {e}"))

    def logout(self):
        if self.current_user and self.ssl_connect_sock:
            try:
                logout_msg = S.LogoutMsg(username=self.current_user, time=int(time.time()))
                self.ssl_connect_sock.sendall(serialize(logout_msg))
                
                # 清理状态
                self.current_user = None
                self.user_id = None
                self.contacts_map = {}
                self.current_chat_friend = None
                self.contact_manager = None
                
                self.message_queue.put(("logout_success", None))
                
            except Exception as e:
                self.message_queue.put(("error", f"注销过程中发生错误: {e}"))

    def refresh_contacts(self):
        self.load_contacts_from_local()

    def load_contacts_from_local(self):
        # 只从本地data.json加载通讯录
        if not self.current_user:
            return
        user_dir = str(self.current_user)
        data_path = os.path.join('user', user_dir, 'data.json')
        if not os.path.exists(data_path):
            return
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        contacts = data.get('contacts', [])
        self.contacts_map = {c['name']: c for c in contacts}
        self.contacts_listbox.delete(0, tk.END)
        for c in contacts:
            status = c.get('status', 'unknown')
            self.contacts_listbox.insert(tk.END, f"{c['name']} ({status})")
        # 自动加载第一个联系人聊天历史
        if contacts:
            self.contacts_listbox.selection_set(0)
            self.on_contact_select(None)

    def on_contact_select(self, event):
        if not self.contacts_listbox.curselection():
            return
        selection = self.contacts_listbox.get(self.contacts_listbox.curselection())
        friend_name = selection.split(" (")[0]
        if friend_name in self.contacts_map:
            friend_details = self.contacts_map[friend_name]
            self.load_chat_history(friend_name)  # 无论在线离线都显示历史
            if friend_details.get("status") == "online":
                self.current_chat_friend = friend_name
                self.chat_title.config(text=f"与 {friend_name} 聊天中")
                self.send_btn.config(state=tk.NORMAL)
                self.file_btn.config(state=tk.NORMAL)
                self.image_btn.config(state=tk.NORMAL)
                self.audio_btn.config(state=tk.NORMAL)
            else:
                self.current_chat_friend = None
                self.chat_title.config(text=f"{friend_name} 当前离线")
                self.send_btn.config(state=tk.DISABLED)
                self.file_btn.config(state=tk.DISABLED)
                self.image_btn.config(state=tk.DISABLED)
                self.audio_btn.config(state=tk.DISABLED)

    def load_chat_history(self, friend_name):
        if not self.current_user:
            return
        user_dir = str(self.current_user)
        data_path = os.path.join('user', user_dir, 'data.json')
        if not os.path.exists(data_path):
            return
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        contacts = data.get('contacts', [])
        friend = next((c for c in contacts if c.get('name') == friend_name), None)
        if not friend:
            return
        messages = data.get('messages', {})
        friend_id = str(friend.get('id'))
        history = messages.get(friend_id, [])
        self.history_display.config(state=tk.NORMAL)
        self.history_display.delete(1.0, tk.END)
        if not history:
            self.history_display.insert(tk.END, "暂无聊天记录\n")
        else:
            for group in history[-20:]:
                date = group.get('date', '')
                self.history_display.insert(tk.END, f"[{date}]\n")
                for msg in group.get('messages', []):
                    sender = "我" if msg.get('sender') == 'user' else friend_name
                    content = msg.get('content', '')
                    time_str = msg.get('time', '未知时间')
                    self.history_display.insert(tk.END, f"[{time_str}] {sender}: {content}\n")
        self.history_display.see(tk.END)
        self.history_display.config(state=tk.DISABLED)

    def send_message(self, event=None):
        if not self.current_chat_friend:
            return
        content = self.message_var.get().strip()
        if not content:
            return
        # 本地假通信：只要status为online就写入本地data.json
        user_dir = str(self.current_user) if self.current_user else ''
        data_path = os.path.join('user', user_dir, 'data.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        contacts = data.get('contacts', [])
        friend = next((c for c in contacts if c.get('name') == self.current_chat_friend), None)
        if not friend or friend.get('status') != 'online':
            messagebox.showerror("错误", f"{self.current_chat_friend} 当前不在线，无法发送消息")
            return
        # 写入本地messages
        messages = data.setdefault('messages', {})
        friend_id = str(friend.get('id'))
        if friend_id not in messages:
            messages[friend_id] = []
        today = datetime.now().strftime('%Y-%m-%d')
        # 查找今天的消息组
        today_group = None
        for group in messages[friend_id]:
            if group.get('date') == today:
                today_group = group
                break
        if not today_group:
            today_group = {'date': today, 'messages': []}
            messages[friend_id].append(today_group)
        now_time = datetime.now().strftime('%H:%M')
        today_group['messages'].append({
            'sender': 'user',
            'content': content,
            'time': now_time
        })
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        self.message_queue.put(("send_message", f"我: {content}"))
        self.message_var.set("")
        self.load_chat_history(self.current_chat_friend)

    def send_file(self):
        if not self.current_chat_friend:
            return
        
        file_path = filedialog.askopenfilename(title="选择要发送的文件")
        if file_path:
            threading.Thread(target=self._send_file_thread, args=(file_path, 'file'), daemon=True).start()

    def send_image(self):
        if not self.current_chat_friend:
            return
        
        file_path = filedialog.askopenfilename(
            title="选择要发送的图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            threading.Thread(target=self._send_file_thread, args=(file_path, 'image'), daemon=True).start()

    def send_audio(self):
        if not self.current_chat_friend:
            return
        
        file_path = filedialog.askopenfilename(
            title="选择要发送的语音文件",
            filetypes=[("音频文件", "*.wav *.mp3 *.ogg *.flac")]
        )
        if file_path:
            threading.Thread(target=self._send_file_thread, args=(file_path, 'audio'), daemon=True).start()

    def _send_file_thread(self, file_path, file_type):
        try:
            if not self.current_user:
                self.message_queue.put(("error", "用户未登录，无法发送文件"))
                return
            if not self.current_chat_friend:
                self.message_queue.put(("error", "未选择联系人"))
                return
            # 本地假通信：只要status为online就写入本地data.json
            user_dir = str(self.current_user) if self.current_user else ''
            data_path = os.path.join('user', user_dir, 'data.json')
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            contacts = data.get('contacts', [])
            friend = next((c for c in contacts if c.get('name') == self.current_chat_friend), None)
            if not friend or friend.get('status') != 'online':
                self.message_queue.put(("error", f"{self.current_chat_friend} 当前不在线，无法发送{file_type}"))
                return
            file_name = os.path.basename(file_path)
            # 复制文件到用户目录
            save_dir = os.path.join('user', str(self.current_user), file_type)
            os.makedirs(save_dir, exist_ok=True)
            dest_path = os.path.join(save_dir, file_name)
            with open(file_path, 'rb') as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            # 写入本地messages，作为一条系统消息
            messages = data.setdefault('messages', {})
            friend_id = str(friend.get('id'))
            if friend_id not in messages:
                messages[friend_id] = []
            today = datetime.now().strftime('%Y-%m-%d')
            today_group = None
            for group in messages[friend_id]:
                if group.get('date') == today:
                    today_group = group
                    break
            if not today_group:
                today_group = {'date': today, 'messages': []}
                messages[friend_id].append(today_group)
            now_time = datetime.now().strftime('%H:%M')
            today_group['messages'].append({
                'sender': 'user',
                'content': f'[发送{file_type}]{file_name}',
                'time': now_time
            })
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            self.message_queue.put(("send_file", f"已发送{file_type}: {file_name}"))
            self.load_chat_history(self.current_chat_friend)
        except Exception as e:
            self.message_queue.put(("error", f"发送{file_type}时出错: {e}"))

    def bind_to_free_port(self):
        try:
            sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)
            sock.bind(("0.0.0.0", 11000))
            port = sock.getsockname()[1]
            return sock, port
        except Exception as e:
            return None, None

    def process_messages(self):
        while True:
            try:
                msg_type, data = self.message_queue.get(timeout=1)
                self.root.after(0, self._handle_message, msg_type, data)
            except queue.Empty:
                continue

    def _handle_message(self, msg_type, data):
        if msg_type == "login_success":
            self.status_var.set(f"已登录: {data}")
            self.current_user = data
            self.login_btn.config(state=tk.DISABLED)
            self.register_btn.config(state=tk.DISABLED)
            self.logout_btn.config(state=tk.NORMAL)
            self.refresh_btn.config(state=tk.NORMAL)
            self.load_contacts_from_local()
        elif msg_type == "register_success":
            messagebox.showinfo("成功", f"用户 {data} 注册成功！")
        elif msg_type == "logout_success":
            self.status_var.set("未连接")
            self.login_btn.config(state=tk.NORMAL)
            self.register_btn.config(state=tk.NORMAL)
            self.logout_btn.config(state=tk.DISABLED)
            self.refresh_btn.config(state=tk.DISABLED)
            self.send_btn.config(state=tk.DISABLED)
            self.file_btn.config(state=tk.DISABLED)
            self.image_btn.config(state=tk.DISABLED)
            self.audio_btn.config(state=tk.DISABLED)
            self.chat_title.config(text="请选择联系人开始聊天")
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.history_display.config(state=tk.NORMAL)
            self.history_display.delete(1.0, tk.END)
            self.history_display.config(state=tk.DISABLED)
        elif msg_type == "contacts_updated":
            self.load_contacts_from_local()
        elif msg_type == "send_message":
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"{data}\n")
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
            if self.current_chat_friend:
                self.load_chat_history(self.current_chat_friend)
        elif msg_type == "receive_message":
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"{data}\n")
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
            if self.current_chat_friend:
                self.load_chat_history(self.current_chat_friend)
        elif msg_type == "send_file":
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"[系统] {data}\n")
            self.chat_display.see(tk.END)
            self.chat_display.config(state=tk.DISABLED)
        elif msg_type == "error":
            messagebox.showerror("错误", data)

    def check_message_queue(self):
        self.root.after(100, self.check_message_queue)

    def add_friend(self):
        if not self.current_user:
            messagebox.showerror("错误", "请先登录后再添加好友！")
            return
        add_win = tk.Toplevel(self.root)
        add_win.title("添加好友")
        add_win.geometry("300x150")
        add_win.resizable(False, False)
        ttk.Label(add_win, text="好友名字:").pack(pady=(10, 0))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(add_win, textvariable=name_var)
        name_entry.pack(pady=5)
        ttk.Label(add_win, text="IP:端口:").pack()
        address_var = tk.StringVar()
        address_entry = ttk.Entry(add_win, textvariable=address_var)
        address_entry.pack(pady=5)
        def on_ok():
            name = name_var.get().strip()
            address = address_var.get().strip()
            if not name or not address:
                messagebox.showerror("错误", "名字和IP:端口不能为空！")
                return
            if ':' not in address:
                messagebox.showerror("错误", "IP:端口格式不正确！")
                return
            try:
                user_dir = str(self.current_user) if self.current_user else ''
                data_path = os.path.join('user', user_dir, 'data.json')
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                contacts = data.get('contacts', [])
                for c in contacts:
                    if c.get('name') == name:
                        messagebox.showerror("错误", "该好友已存在！")
                        return
                # 新增：尝试从user/sikaiqi/data.json中查找该联系人
                ref_data_path = os.path.join('user', 'sikaiqi', 'data.json')
                status = 'offline'
                if os.path.exists(ref_data_path):
                    with open(ref_data_path, 'r', encoding='utf-8') as f:
                        ref_data = json.load(f)
                    ref_contacts = ref_data.get('contacts', [])
                    for rc in ref_contacts:
                        if rc.get('name') == name and rc.get('address') == address:
                            status = rc.get('status', 'offline')
                            break
                new_id = max([c.get('id', 0) for c in contacts] + [0]) + 1
                contacts.append({
                    'id': new_id,
                    'name': name,
                    'status': status,  # 用查到的status
                    'address': address
                })
                data['contacts'] = contacts
                with open(data_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("成功", f"已添加好友：{name}")
                self.refresh_contacts()
                add_win.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"添加失败: {e}")
        ok_btn = ttk.Button(add_win, text="确定", command=on_ok)
        ok_btn.pack(pady=10)
        name_entry.focus()

def main():
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 