import json
import os
import time
from typing import List, Dict, Any, Set, Union
from datetime import datetime

# 导入时间戳函数
from schema import get_timestamp

class ContactManager:
    """
    管理单个用户的通讯录和消息记录。
    每个用户都有一个独立的JSON文件来存储其联系人和消息。
    """
    def __init__(self, username: str):
        self.username = username
        self.filepath = os.path.join('data', 'directory', f"{self.username}.json")
        self.contacts: List[Dict[str, Any]] = []
        self.messages: Dict[str, List[Dict[str, Any]]] = {}
        self._load_data()

    def _load_data(self):
        """从文件加载通讯录和消息，如果文件不存在则初始化为空。"""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.contacts = data.get("contacts", [])
                self.messages = data.get("messages", {})
        except (FileNotFoundError, json.JSONDecodeError):
            self.contacts = []
            self.messages = {}

    def _save_data(self):
        self.contacts.sort(key=lambda c: c.get('time', 0), reverse=True)
        for i, contact in enumerate(self.contacts):
            contact['id'] = i + 1
            
        data_to_save = {
            "contacts": self.contacts,
            "messages": self.messages
        }
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

    def get_contact_by_name(self, name: str) -> Union[Dict[str, Any], None]:
        """通过名称查找联系人"""
        for contact in self.contacts:
            if contact.get("name") == name:
                return contact
        return None

    def update_or_add_contact(self, name: str, address: str, preview: str):
        """
        更新或添加一个联系人。
        (此函数逻辑不变, 但现在调用的是已更新的 _save_data)
        """
        found = False
        current_time = get_timestamp()
        
        for contact in self.contacts:
            if contact.get("name") == name:
                contact["address"] = address
                contact["preview"] = preview
                contact["time"] = current_time
                found = True
                break
        
        if not found:
            new_contact = {
                "id": -1,
                "name": name,
                "status": "offline",
                "preview": preview,
                "time": current_time,
                "address": address
            }
            self.contacts.append(new_contact)
            
        self._save_data() # 调用已更新的保存函数
        print(f"[通讯录日志] 用户 {self.username} 的通讯录已更新，联系人: {name}")
        
    def add_message(self, friend_username: str, sender_type: str, content: str):
        """
        添加一条消息到记录中，按对方用户名分类。
        
        Args:
            friend_username (str): 聊天对象的用户名。
            sender_type (str): 发送者类型 ('user' 代表自己, 'contact' 代表对方)。
            content (str): 消息内容。
        """
        # 准备要添加的消息体，使用时间戳
        new_message = {
            "sender": sender_type,
            "content": content,
            "time": int(time.time())
        }

        # 如果之前没有和这位好友的聊天记录，则创建一个新列表
        if friend_username not in self.messages:
            self.messages[friend_username] = []
        
        # 将新消息追加到对应好友的聊天记录中
        self.messages[friend_username].append(new_message)
        
        # 保存更新后的数据
        self._save_data()
        print(f"[消息记录] 已为用户 {self.username} 添加与 {friend_username} 的新消息。")
    # --- 新增结束 ---

    def get_contacts_with_status(self, online_users_set: Set[str]) -> List[Dict[str, Any]]:
        """
        获取通讯录列表，并根据在线用户集合实时更新联系人状态。
        """
        for contact in self.contacts:
            if contact.get("name") in online_users_set:
                contact["status"] = "online"
            else:
                contact["status"] = "offline"
        return self.contacts

