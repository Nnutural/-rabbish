import json
from dataclasses import asdict, is_dataclass
from typing import Any
import inspect # 导入 inspect 模块
import schema as S # 你的协议文件

# 这个 Encoder 让 json.dumps 可以正确处理 dataclass 和 Enum
class CustomEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        # 确保 o 是一个 dataclass 实例，而不是 dataclass 类
        # inspect.isclass(o) 检查 o 是否是一个类
        if is_dataclass(o) and not inspect.isclass(o):
            return asdict(o)
        
        # 对 Enum 的处理保持不变
        if isinstance(o, S.MsgTag):
            return o.value
            
        return super().default(o)

def serialize(msg_obj: Any) -> bytes:
    """将 dataclass 对象序列化为[长度前缀 + JSON字节串]"""
    # 1. 将 dataclass 对象转换为 JSON 字符串
    json_str = json.dumps(msg_obj, cls=CustomEncoder)
    
    # 2. 将 JSON 字符串编码为 UTF-8 字节串
    json_bytes = json_str.encode('utf-8')
    
    # 3. 获取字节串的长度
    data_length = len(json_bytes)
    
    # 4. 将长度打包成一个4字节的大端序整数（长度前缀）
    length_prefix = data_length.to_bytes(4, 'big')
    
    # 5. 返回 [长度前缀] + [数据]
    return length_prefix + json_bytes

# --- 反序列化 ---

# 消息工厂：根据 tag 创建对应的 dataclass 对象
MESSAGE_CLASSES = {
    S.MsgTag.Login: S.LoginMsg,
    S.MsgTag.Register: S.RegisterMsg,
    S.MsgTag.Logout: S.LogoutMsg,
    S.MsgTag.GetDirectory: S.GetDirectoryMsg,
    S.MsgTag.GetHistory: S.GetHistoryMsg,
    S.MsgTag.GetPublicKey: S.GetPublicKeyMsg,
    S.MsgTag.Alive: S.AliveMsg,
    S.MsgTag.BackUp: S.BackupMsg,

    S.MsgTag.Message: S.MessageMsg,
    S.MsgTag.Voice: S.VoiceMsg,
    S.MsgTag.File: S.FileMsg,
    S.MsgTag.Image: S.ImageMsg,


    S.MsgTag.SuccessRegister: S.SuccessRegisterMsg,
    S.MsgTag.SuccessLogin: S.SuccessLoginMsg,
    S.MsgTag.SuccessLogout: S.SuccessLogoutMsg,
    S.MsgTag.SuccessBackUp: S.SuccessBackUpMsg,
    S.MsgTag.History: S.HistoryMsg,
    S.MsgTag.Directory: S.DirectoryMsg,
    S.MsgTag.PublicKey: S.PublicKeyMsg,
    S.MsgTag.FailRegister: S.FailRegisterMsg,
    S.MsgTag.FailLogin: S.FailLoginMsg, 
}

def deserialize(msg_dict: dict) -> Any:
    """根据字典中的'tag'，创建对应的 dataclass 对象"""
    tag_value = msg_dict.get('tag')
    if tag_value is None:
        raise ValueError("消息字典中缺少 'tag' 字段")
        
    MsgClass = MESSAGE_CLASSES.get(S.MsgTag(tag_value))
    
    if MsgClass is None:
        raise ValueError(f"未知的消息类型 tag: {tag_value}")
    
    # 移除 tag 字段，因为它在 dataclass 中是 init=False 的
    if 'tag' in msg_dict:
        del msg_dict['tag']
        
    return MsgClass(**msg_dict)