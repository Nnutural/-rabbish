import hashlib
import json
import os
import uuid 
from dataclasses import asdict
from typing import Any, Dict, List

from schema import *


def hash_password(password: str) -> str:
    """使用SHA-256对密码进行哈希处理。"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(provided_password: str, stored_hash: str) -> bool:
    """验证提供的密码是否与存储的哈希值匹配。"""
    return hash_password(provided_password) == stored_hash

USER_DB_FILE = os.path.join('data', 'users.json')

def load_users_from_json(filename: str) -> List[Dict[str, Any]]:
    """
    从JSON文件加载用户列表。
    如果文件不存在，则返回一个空列表。
    """
    try:
        # 确保目录存在
        db_dir = os.path.dirname(filename)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 更新：如果文件不存在或为空返回空列表
        print(f"[服务器日志] 未找到或无法解析 {filename}。将使用空的用户列表启动。")
        return []

def save_users_to_json(filename: str, users: List[Dict[str, Any]]) -> None:
    """将用户列表保存到JSON文件。"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)
    print(f"[服务器日志] 用户数据已保存到 {filename}。")


# 启动时加载用户数据
USER_LIST = load_users_from_json(USER_DB_FILE)


def send_to_client(client_address: str, message_obj: Any) -> None:
    """一个模拟的函数，用于向特定客户端发送响应。"""
    payload = asdict(message_obj)
    tag_enum = payload.pop('tag')


def _execute_registration(client_address: str, message: RegisterMsg) -> None:
    """执行注册的核心业务逻辑。"""
    if any(user.get('username') == message.username for user in USER_LIST):
        response = FailRegisterMsg(username=message.username, errortype=FailType.USERNAME_EXISTS.value)
        send_to_client(client_address, response)
        return
    
    # 2. 更新：使用uuid生成唯一的字符串ID
    new_user_id = str(uuid.uuid4())
    pass_hash = hash_password(message.secret)

    # 创建新的用户记录，使用 user_id
    new_user_record = {
        "user_id": new_user_id,
        "username": message.username,
        "email": message.email,
        "pass_hash": pass_hash,
        "created_at": get_timestamp()
    }
    USER_LIST.append(new_user_record)
    
    # 将更新后的用户列表保存到文件
    save_users_to_json(USER_DB_FILE, USER_LIST)
    
    print(f"[服务器日志] 用户 '{message.username}' 创建成功, user_id: {new_user_id}。\n")
    response = SuccessRegisterMsg(username=message.username, user_id=new_user_id)
    send_to_client(client_address, response)


def _execute_login(client_address: str, message: LoginMsg) -> None:
    """执行登录验证的核心业务逻辑。"""
    print(f"[服务器日志] 收到来自 {client_address} 的登录请求。\n")

    user_record = None
    login_identifier = message.username or message.user_id

    # 更新：所有 userID -> user_id
    for record in USER_LIST:
        if (message.username and record.get('username') == message.username) or \
           (message.user_id and record.get('user_id') == message.user_id):
            user_record = record
            break
    
    if not user_record:
        print(f"[服务器日志] 校验失败: 提供的标识符 '{login_identifier}' 未找到对应用户。\n")
        response = FailLoginMsg(username=message.username, errortype=FailType.USER_NOT_FOUND.value)
        send_to_client(client_address, response)
        return

    found_username = user_record.get('username')

    if verify_password(message.secret, user_record.get('pass_hash', '')):
        # 更新：检查 user_id
        if found_username and 'user_id' in user_record:
            print(f"[服务器日志] 用户 '{found_username}' 验证成功。\n")
            response = SuccessLoginMsg(username=found_username, user_id=user_record['user_id'])
            send_to_client(client_address, response)
        else:
            print(f"[服务器错误] 数据库记录不完整，无法为用户 '{login_identifier}' 创建成功登录响应。\n")
            response = FailLoginMsg(username=found_username, errortype=FailType.SERVER_ERROR.value)
            send_to_client(client_address, response)
    else:
        print(f"[服务器日志] 校验失败: 用户 '{found_username or login_identifier}' 的密码不正确。\n")
        response = FailLoginMsg(username=found_username, errortype=FailType.INCORRECT_SECRET.value)
        send_to_client(client_address, response)


def server_handle_message(client_address: str, received_message: Any) -> None:
    """模拟服务器的总入口，先确认消息标识，再调用相应的处理函数。"""
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

"""
if __name__ == '__main__':

    if not any(u.get('username') == 'alice' for u in USER_LIST):
        print("'alice'用户不存在，将自动注册...\n")
        server_handle_message("client_setup", RegisterMsg("alice", "alice_pass", "alice@example.com"))
        alice_record = next((u for u in USER_LIST if u.get('username') == 'alice'), None)

    if alice_record:
        alice_id = alice_record.get("user_id")
        server_handle_message("client_123", LoginMsg(username="alice", secret="alice_pass"))

       """
