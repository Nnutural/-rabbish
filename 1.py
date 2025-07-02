import time
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Union, Any, Dict


def get_timestamp() -> int:
    """获取当前的Unix时间戳"""
    return int(time.time())

class MsgTag(Enum):
    """消息类型标识枚举"""
    Register = 1       
    Login = 2          
    Logout = 3         
    GetDirectory = 4    
    GetHistory = 5      
    GetPublicKey = 6    
    Alive = 7          
    BackUp = 8          


@dataclass
class RegisterMsg:
    """注册消息 (Tag: 1)"""
    username: str
    secret: str
    email: str
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.Register, init=False)

@dataclass
class LoginMsg:
    """登录消息 (Tag: 2)"""
    username: str
    secret: str
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.Login, init=False)

@dataclass
class LogoutMsg:
    """登出消息 (Tag: 3)"""
    username: str
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.Logout, init=False)

@dataclass
class GetDirectoryMsg:
    """获取通信录消息 (Tag: 4)"""
    username: str
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.GetDirectory, init=False)

@dataclass
class GetHistoryMsg:
    """获取聊天记录消息 (Tag: 5)"""
    ChatID: Union[str, int]
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.GetHistory, init=False)

@dataclass
class GetPublicKeyMsg:
    """获取公钥消息 (Tag: 6)"""
    userID: Union[str, int]
    dest: Union[str, int]
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.GetPublicKey, init=False)

@dataclass
class AliveMsg:
    """心跳消息 (Tag: 7)"""
    userID: Union[str, int]
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.Alive, init=False)

@dataclass
class BackupMsg:
    """备份聊天记录消息 (Tag: 8)"""
    source_user_id: Union[str, int] 
    dest: Union[str, int]
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.BackUp, init=False)

def register(username: str, secret: str, email: str) -> None:
    """发送注册请求"""
    send_to_server(RegisterMsg(username=username, secret=secret, email=email))

def login(username: str, secret: str) -> None:
    """发送登录请求"""
    send_to_server(LoginMsg(username=username, secret=secret))

def logout(username: str) -> None:
    """发送注销请求"""
    send_to_server(LogoutMsg(username=username))

def get_directory(username: str) -> None:
    """发送获取通信录请求"""
    send_to_server(GetDirectoryMsg(username=username))

def get_history(chat_id: Union[str, int]) -> None:
    """发送获取聊天记录请求"""
    send_to_server(GetHistoryMsg(ChatID=chat_id))

def get_public_key(user_id: Union[str, int], dest_user_id: Union[str, int]) -> None:
    """发送获取好友公钥请求"""
    send_to_server(GetPublicKeyMsg(userID=user_id, dest=dest_user_id))

def send_alive(user_id: Union[str, int]) -> None:
    """发送在线包"""
    send_to_server(AliveMsg(userID=user_id))

def backup_history(user_id: Union[str, int], dest_user_id: Union[str, int]) -> None:
    """发送备份聊天记录请求"""
    send_to_server(BackupMsg(source_user_id=user_id, dest=dest_user_id))

