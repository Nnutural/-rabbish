import time
import random
import hashlib
import json
import os
from dataclasses import asdict
from typing import Any, Dict, List
from shema import *

def hash_password(password: str) -> str:
    """使用SHA-256对密码进行哈希处理。"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(provided_password: str, stored_hash: str) -> bool:
    """验证提供的密码是否与存储的哈希值匹配。"""
    return hash_password(provided_password) == stored_hash

# 更新：将数据库文件路径指向 data/ 文件夹
USER_DB_FILE = os.path.join('data', 'users.json') # 定义数据库文件名

def load_database(filename: str) -> List[Dict[str, Any]]:
    """
    从JSON文件加载用户数据库。
    如果文件不存在或为空，则创建一个默认数据库并保存。
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not data: # 处理空文件的情况
                raise FileNotFoundError
            print(f"[服务器日志] 从 {filename} 加载数据库成功。")
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"[服务器日志] 未找到或无法解析 {filename}。正在创建新的数据库...")
        
        # 更新：在创建文件前，确保data目录存在
        db_dir = os.path.dirname(filename)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        default_db = [
            {}
        ]
        save_database(filename, default_db)
        return default_db

def save_database(filename: str, db: List[Dict[str, Any]]) -> None:
    """将用户数据库保存到JSON文件。"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)
    print(f"[服务器日志] 数据库已保存到 {filename}。")


# 启动时加载数据库
USER_DATABASE = load_database(USER_DB_FILE)


def send_to_client(client_address: str, message_obj: Any) -> None:
    """一个模拟的函数，用于向特定客户端发送响应。"""
    payload = asdict(message_obj)
    tag_enum = payload.pop('tag')
    print(f"--- [S -> C] 正在向 {client_address} 发送响应 ---")
    print(f"响应类型: {tag_enum.name} (Tag: {tag_enum.value})")
    print(f"响应负载: {payload}")
    print("-------------------------------------------\n")


def _execute_registration(client_address: str, message: RegisterMsg) -> None:
    """执行注册的核心业务逻辑。"""
    if any(user['username'] == message.username for user in USER_DATABASE):
        response = FailRegisterMsg(username=message.username, errortype=FailType.USERNAME_EXISTS.value)
        send_to_client(client_address, response)
        return
    
    new_user_id = random.randint(1001, 9999)
    while any(user['userID'] == new_user_id for user in USER_DATABASE):
        new_user_id = random.randint(1001, 9999)

    pass_hash = hash_password(message.secret)

    new_user_record = {
        "userID": new_user_id,
        "username": message.username,
        "email": message.email,
        "pass_hash": pass_hash,
        "created_at": get_timestamp(),
        "revoked": False
    }
    USER_DATABASE.append(new_user_record)
    
    save_database(USER_DB_FILE, USER_DATABASE)
    
    print(f"[服务器日志] 用户 '{message.username}' 创建成功, userID: {new_user_id}。\n")
    response = SuccessRegisterMsg(username=message.username, userID=new_user_id)
    send_to_client(client_address, response)


def _execute_login(client_address: str, message: LoginMsg) -> None:
    """执行登录验证的核心逻辑。"""
    print(f"[服务器日志] 收到来自 {client_address} 的登录请求。\n")

    user_record = None
    login_identifier = message.username or message.userID

    for record in USER_DATABASE:
        if (message.username and record['username'] == message.username) or \
           (message.userID and record['userID'] == message.userID):
            user_record = record
            break
    
    if not user_record:
        print(f"[服务器日志] 校验失败: 提供的标识符 '{login_identifier}' 未找到对应用户。\n")
        response = FailLoginMsg(username=message.username, errortype=FailType.USER_NOT_FOUND.value)
        send_to_client(client_address, response)
        return

    if user_record.get("revoked", False):
        print(f"[服务器日志] 校验失败: 用户 '{user_record['username']}' 的账户已被封禁。\n")
        response = FailLoginMsg(username=user_record['username'], errortype=FailType.ACCOUNT_REVOKED.value)
        send_to_client(client_address, response)
        return

    if verify_password(message.secret, user_record['pass_hash']):
        print(f"[服务器日志] 用户 '{user_record['username']}' 验证成功。\n")
        response = SuccessLoginMsg(username=user_record['username'], userID=user_record['userID'])
        send_to_client(client_address, response)
    else:
        print(f"[服务器日志] 校验失败: 用户 '{user_record['username']}' 的密码不正确。\n")
        response = FailLoginMsg(username=user_record['username'], errortype=FailType.INCORRECT_SECRET.value)
        send_to_client(client_address, response)


def server_handle_message(client_address: str, received_message: Any) -> None:
    """先确认消息标识，再调用相应的处理函数。"""
    if not hasattr(received_message, 'tag'):
        print(f"[服务器警告] 收到来自 {client_address} 的消息缺少'tag'属性: {received_message}")
        return

    if received_message.tag == MsgTag.Register:
        if isinstance(received_message, RegisterMsg):
            _execute_registration(client_address, received_message)
    elif received_message.tag == MsgTag.Login:
        if isinstance(received_message, LoginMsg):
            _execute_login(client_address, received_message)
    else:
        print(f"[服务器日志] 收到一个未处理类型的消息 (Tag: {received_message.tag.name})，已忽略。")


"""用法示例
if __name__ == '__main__':
    
    if not any(u['username'] == 'alice' for u in USER_DATABASE):
        print("注册一个新用户 'alice'...\n")
        server_handle_message("client_setup", RegisterMsg("alice", "alice_pass", "alice@example.com"))
  
  登录：
  alice_record = next((u for u in USER_DATABASE if u['username'] == 'alice'), None)
  
  if alice_record:
        alice_id = alice_record["userID"]
        server_handle_message("client_123", LoginMsg(username="alice", secret="alice_pass"))
"""
        
