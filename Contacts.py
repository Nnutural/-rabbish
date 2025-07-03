import json
import os
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
        """
        保存通讯录和消息记录到文件。
        在保存前，会对联系人进行排序并重新生成ID。
        """
        # 1. 根据时间戳对联系人进行降序排序
        self.contacts.sort(key=lambda c: c.get('time', 0), reverse=True)
        
        # 2. 重新生成ID
        for i, contact in enumerate(self.contacts):
            contact['id'] = i + 1
            
        # 3. 准备要写入的数据
        data_to_save = {
            "contacts": self.contacts,
            "messages": self.messages
        }
        
        # 4. 写入文件
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)

    def get_contact_by_name(self, name: str) -> Union[Dict[str, Any], None]:
        """通过名称查找联系人"""
        for contact in self.contacts:
            if contact.get("name") == name:
                return contact
        return None

    def add_message(self, sender_name: str, receiver_name: str, content: str):
        """
        添加一条消息记录。
        """
        # 确定这条消息对于当前用户来说，是发送的还是接收的
        # self.username 是文件所有者的名字
        if self.username == sender_name:
            # 文件所有者是发送方，消息的另一方是接收方
            contact_person_name = receiver_name
            sender_type = "user"
        else:
            # 文件所有者是接收方，消息的另一方是发送方
            contact_person_name = sender_name
            sender_type = "contact"

        # 根据对方的名字找到其在通讯录中的ID
        contact_info = self.get_contact_by_name(contact_person_name)
        if not contact_info:
            # 如果对方不在通讯录里，理论上不应该发生，但作为防御
            print(f"[消息记录错误] 在 {self.username} 的通讯录中未找到 {contact_person_name}")
            return
        
        contact_id_str = str(contact_info['id'])
        
        # 准备消息体
        message_to_add = {
            "sender": sender_type,
            "content": content,
            "time": datetime.now().strftime("%H:%M")
        }

        # 获取当前日期
        today_date_str = get_timestamp()

        # 检查该联系人是否有消息记录
        if contact_id_str not in self.messages:
            self.messages[contact_id_str] = []

        # 查找今天的消息分组
        today_group = None
        for group in self.messages[contact_id_str]:
            if group.get("date") == today_date_str:
                today_group = group
                break
        
        if today_group:
            # 如果找到了今天的日期分组，直接添加消息
            today_group["messages"].append(message_to_add)
        else:
            # 如果没找到，创建一个新的日期分组
            new_group = {
                "date": today_date_str,
                "messages": [message_to_add]
            }
            self.messages[contact_id_str].append(new_group)

        self._save_data()
        print(f"[消息记录日志] 已为用户 {self.username} 添加与 {contact_person_name} 的新消息。")

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

