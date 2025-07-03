import json
import os
from typing import List, Dict, Any, Set

# 导入时间戳函数
from schema import get_timestamp

class ContactManager:
    """
    管理单个用户的通讯录。
    每个用户都有一个独立的JSON文件来存储其联系人列表。
    """
    def __init__(self, username: str):
        self.username = username
        # 为每个用户创建一个独立的通讯录文件
        self.filepath = os.path.join('data', 'contacts', f"{self.username}_contacts.json")
        self.contacts = self._load_contacts()

    def _load_contacts(self) -> List[Dict[str, Any]]:
        """从文件加载通讯录，如果文件不存在则返回空列表。"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("contacts", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_contacts(self):
        """
        保存通讯录到文件。
        在保存前，会根据最近通信时间戳对联系人进行排序，并重新生成ID。
        """
        # 1. 根据时间戳对联系人进行降序排序
        self.contacts.sort(key=lambda c: c.get('time', 0), reverse=True)
        
        # 2. 重新生成ID
        for i, contact in enumerate(self.contacts):
            contact['id'] = i + 1
            
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump({"contacts": self.contacts}, f, indent=4, ensure_ascii=False)

    def update_or_add_contact(self, name: str, address: str, preview: str):
        """
        更新或添加一个联系人。
        如果联系人已存在，则更新其信息和时间戳。
        如果不存在，则添加为新联系人。
        """
        found = False
        current_time = get_timestamp()
        
        for contact in self.contacts:
            if contact.get("name") == name:
                # 更新现有联系人
                contact["address"] = address
                contact["preview"] = preview
                contact["time"] = current_time
                found = True
                break
        
        if not found:
            # 添加新联系人
            new_contact = {
                "id": -1, # id将在保存时重新计算
                "name": name,
                "status": "offline", # 初始状态为离线，将在获取时更新
                "preview": preview,
                "time": current_time,
                "address": address
            }
            self.contacts.append(new_contact)
            
        self._save_contacts()
        print(f"[通讯录日志] 用户 {self.username} 的通讯录已更新，联系人: {name}")

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

ONLINE_USERS: Set[str] = set()

def _execute_login(user_ip: str, message: LoginMsg) -> Union[SuccessLoginMsg, FailLoginMsg]:
    user_record = next((u for u in USER_LIST if u.get('username') == message.username), None)
    
    if not user_record:
        return FailLoginMsg(username=message.username, error_type=FailType.USER_NOT_FOUND.value)

    if verify_password(message.secret, user_record.get('pass_hash', '')):
        username = user_record['username']
        user_id = user_record.get('user_id', '') # 获取内部ID
        
        user_record['address'] = f"{user_ip}:{message.port}"
        ONLINE_USERS.add(username)
        save_users_to_json(USER_DB_FILE, USER_LIST)
        print(f"[在线状态] {username} 已上线。当前在线: {ONLINE_USERS}")
        
        # 获取并序列化通讯录
        manager = ContactManager(username=username)
        contacts = manager.get_contacts_with_status(ONLINE_USERS)
        directory_data = json.dumps(contacts)

#登出时去除在线名单
def _execute_logout(message: LogoutMsg) -> SuccessLogoutMsg:
    username = message.username
    user_record = next((u for u in USER_LIST if u.get('username') == username), None)
    
    if username in ONLINE_USERS:
        ONLINE_USERS.remove(username)
    user_id = user_record.get('user_id', '') if user_record else ''
    return SuccessLogoutMsg(username=username, user_id=user_id)

def _handle_communication(sender_username: str, receiver_username: str, message_preview: str):
    """进行一次通信，并更新双方的通讯录。"""
    sender_record = next((u for u in USER_LIST if u.get('username') == sender_username), None)
    receiver_record = next((u for u in USER_LIST if u.get('username') == receiver_username), None)

    if not sender_record or not receiver_record:
        print("[通信错误] 发送方或接收方不存在。")
        return

    # 更新发送方的通讯录 (添加接收方)
    sender_manager = ContactManager(username=sender_username)
    sender_manager.update_or_add_contact(
        name=receiver_record['username'],
        address=receiver_record.get('address', ''),
        preview=f"我: {message_preview}"
    )

    # 更新接收方的通讯录 (添加发送方)
    receiver_manager = ContactManager(username=receiver_username)
    receiver_manager.update_or_add_contact(
        name=sender_record['username'],
        address=sender_record.get('address', ''),
        preview=message_preview
    )

