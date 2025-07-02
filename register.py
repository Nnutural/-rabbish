import time
import random
import messagepy as mp
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Union, Any, Dict


class FailType(Enum):
    """注册失败原因枚举"""
    USERNAME_EXISTS = "Username already exists"
    EMAIL_EXISTS = "Email already registered"
    INVALID_INPUT = "Invalid username or password"
    SERVER_ERROR = "Internal server error"


def _execute_registration(client_address: str, message: mp.RegisterMsg) -> None:

    # 1. 检查用户名是否已存在
    if message.username in USER_DATABASE:
        print(f"[服务器日志] 校验失败: 用户名 '{message.username}' 已存在\n")
        response = mp.FailRegisterMsg(username=message.username, errortype=FailType.USERNAME_EXISTS.value)
        send_to_client(client_address, response)
        return

    # 2. 检查邮箱是否已被注册
    for user in USER_DATABASE.values():
        if user['email'] == message.email:
            print(f"[服务器日志] 校验失败: 邮箱 '{message.email}' 已被注册\n")
            response = FailRegisterMsg(username=message.username, errortype=FailType.EMAIL_EXISTS.value)
            send_to_client(client_address, response)
            return
            
    try:
        # 生成新的userID
        new_user_id = None
        MAX_ID_GENERATION_ATTEMPTS = 5000 # 设置一个尝试上限，防止在ID池满时死循环

        for _ in range(MAX_ID_GENERATION_ATTEMPTS):
            candidate_id = random.randint(1001, 9999)
            # 确认生成的ID是否已经被使用
            if not any(user['userID'] == candidate_id for user in USER_DATABASE.values()):
                new_user_id = candidate_id
                break # 找到了一个未被使用的ID，跳出循环
        
        # 如果循环结束后 new_user_id 仍然是 None，说明未找到可用的ID
        if new_user_id is None:
            print(f"[服务器错误] 无法生成唯一的用户ID，可能ID池已满。\n")
            response = FailRegisterMsg(username=message.username, errortype=FailType.SERVER_ERROR.value)
            send_to_client(client_address, response)
            return

        # 在数据库中创建新用户
        USER_DATABASE[message.username] = {
            "userID": new_user_id,
            "email": message.email,
            "secret": message.secret
        }
        print(f"[服务器日志] 用户 '{message.username}' 创建成功, userID: {new_user_id}。\n")

        # 构建并发送成功响应
        response = SuccessRegisterMsg(username=message.username, userID=new_user_id)
        send_to_client(client_address, response)

    except Exception as e:
        print(f"[服务器错误] 创建用户时发生异常: {e}\n")
        response = FailRegisterMsg(username=message.username, errortype=FailType.SERVER_ERROR.value)
        send_to_client(client_address, response)


def server_handle_message(client_address: str, received_message: Any) -> None:
    
    # 首先，确认消息标识是否为注册
    if received_message.tag == MsgTag.Register:
        # 确认是注册消息后，再进行类型检查并执行注册流程
        if isinstance(received_message, RegisterMsg):
            _execute_registration(client_address, received_message)
        else:
            print(f"[服务器错误] 消息Tag为Register，但对象类型不匹配: {type(received_message)}")
    else:
        # 如果是其他类型的消息，则忽略或分发到其他处理函数
        print(f"[服务器日志] 收到一个非注册类型的消息 (Tag: {received_message.tag.name})，已忽略。")

def _execute_login(client_address: str, message: LoginMsg) -> None:
    print(f"[服务器日志] 收到来自 {client_address} 的登录请求。\n")
    user_data = None
    login_username = message.username

    #  根据提供的标识符查找用户
    if message.username:
        user_data = USER_DATABASE.get(message.username)
    elif message.userID:
        for uname, udata in USER_DATABASE.items():
            if udata['userID'] == message.userID:
                user_data = udata
                login_username = uname
                break
    
    if not user_data:
        print(f"[服务器日志] 校验失败: 提供的标识符未找到对应用户。\n")
        response = FailLoginMsg(username=login_username, errortype=FailType.USER_NOT_FOUND.value)
        send_to_client(client_address, response)
        return

    # 验证密码哈希值是否匹配
    provided_secret_hash = _hash_secret(message.secret)
    
    if provided_secret_hash == user_data['secret']:
        # 验证成功
        print(f"[服务器日志] 用户 '{login_username}' 验证成功。\n")
        response = SuccessLoginMsg(username=login_username, userID=user_data['userID'])
        send_to_client(client_address, response)
    else:
        # 验证失败
        print(f"[服务器日志] 校验失败: 用户 '{login_username}' 的密码不正确。\n")
        response = FailLoginMsg(username=login_username, errortype=FailType.INCORRECT_SECRET.value)
        send_to_client(client_address, response)


if __name__ == '__main__':
    server_handle_message("client_1", client_1_request)
