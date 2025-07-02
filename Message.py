from enum import Enum
import ctypes
import time

# --- 协议定义 (保持不变) ---
PACKET_SIZE = 2048
MAX = PACKET_SIZE - 4  # 2044 bytes

class MsgTag(Enum): # 4 Bytes
    # C to S
    Registser = 1 # 注册 {username, secret, email, time}
    Login = 2 # 登录 {username, secret, time, address()}
    Logout = 3 # 注销 {username, time}
    GetDirectionary = 4 # 获取通信录 {username, time}
    GetHistory = 5 # 获取聊天记录 {ChatID, data, time} (source, dest) -> ChatID, MessageID -> ChatID
    GetPbulicKey = 6 # 获取一个好友的公钥？ {userID, dest, time}
    Alive = 7 # 在线/心跳 {userID, time}
    BackUp = 8 # 备份聊天记录 {flag,userID, dest, data, time}

    # P2P
    Messagae = 11 # 消息 {MessageID, source(userID), dest, content, time} // {MessageID, ChatID} MessageID -> ChatID
    Voice = 12 # 语音 {VoiceID, source, dest, data, time}
    File = 13 # 文件 {FileID, source, dest, data, time}
    Picture = 14 # 图片载体 {PictureID, source, dest, data, time}

    # S to C
    SuccessRegister = 21 # 注册成功 {username, userID, time}
    SuccessLogin = 22 # 登录成功 {username, userID, time} 上线
    SuccessLogout = 23 # 注销成功 {username, userID, time} 下线
    SuccessBackUp = 24 # 备份成功 {userID, time}
    History = 25 # 聊天记录 {flag, userID, dest, data, time}
    Directionary = 26 # 通信录 {userID, data, time}
    PulicKey = 27 # 公钥 {userID, dest, data, time}
    FailRegister = 28 # 注册失败 {userID, errortype, time} 
    FailLogin = 29 # 登录失败 {userID, errortype, time}
    # UpdataeAlive = 30


# ==================== 主要修改在这里 ====================
# 重新分配 Msg_Info 内部字段的长度以支持中文，并确保总大小为 MAX
class Msg_Info(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        # 增大了 username 和 email 的空间
        ("username",    ctypes.c_char * 64),     # 可容纳约21个汉字
        ("secret",      ctypes.c_char * 32),
        ("email",       ctypes.c_char * 64),     # 可容纳约21个汉字
        ("userID",      ctypes.c_char * 16),
        ("source",      ctypes.c_char * 16),
        ("dest",        ctypes.c_char * 16),
        ("MessageID",   ctypes.c_char * 32),
        ("content",     ctypes.c_char * 1736),   # 消息内容，占据大部分剩余空间
        ("ChatID",      ctypes.c_char * 16),
        ("time",        ctypes.c_char * 32),
        ("errortype",   ctypes.c_char * 20)
    ]
# =======================================================


# --- 其他结构体 (保持不变, 因为它们构成了 Union) ---
class Msg_Voice_Data(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("VoiceID", ctypes.c_char * 16),
        ("source", ctypes.c_char * 8),
        ("dest", ctypes.c_char * 8),
        ("time", ctypes.c_char * 16),
        ("data", ctypes.c_char * (MAX - 16 - 8 - 8 - 16))
    ]

class Msg_File_Data(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("FileID", ctypes.c_char * 16),
        ("source", ctypes.c_char * 8),
        ("dest", ctypes.c_char * 8),
        ("time", ctypes.c_char * 16),
        ("data", ctypes.c_char * (MAX - 16 - 8 - 8 - 16))
    ]

class Msg_Picture_Data(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("PictureID", ctypes.c_char * 16),
        ("source", ctypes.c_char * 8),
        ("dest", ctypes.c_char * 8),
        ("time", ctypes.c_char * 16),
        ("data", ctypes.c_char * (MAX - 16 - 8 - 8 - 16))
    ]

class Msg_History_Data(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("flag", ctypes.c_char * 1), # 0: 获取历史消息 1: 备份历史消息
        ("userID", ctypes.c_char * 8),
        ("dest", ctypes.c_char * 8),
        ("data", ctypes.c_char * (MAX - 1 - 8 - 8 - 16)), # 消息内容
        ("time", ctypes.c_char * 16)
    ]

class Msg_Payload(ctypes.Union):
    _pack_ = 1
    _fields_ = [
        ("Msg_Info", Msg_Info),
        ("Msg_Voice_Data", Msg_Voice_Data),
        ("Msg_File_Data", Msg_File_Data),
        ("Msg_Picture_Data", Msg_Picture_Data),
        ("Msg_History_Data", Msg_History_Data)
    ]

class MsgHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("msgID", ctypes.c_int),      # 4 Bytes
        ("Msg_Payload", Msg_Payload)  # MAX = 2044 Bytes
    ]


# --- 使用示例 ---
if __name__ == "__main__":
    
    # 1. 验证结构体大小是否符合预期
    print("--- 结构体大小验证 ---")
    print(f"Size of MsgHeader: {ctypes.sizeof(MsgHeader)} (预期: {PACKET_SIZE})")
    print(f"Size of Msg_Payload (Union): {ctypes.sizeof(Msg_Payload)} (预期: {MAX})")
    print(f"Size of Msg_Info: {ctypes.sizeof(Msg_Info)} (预期: {MAX})")
    print("-" * 25)

    # 2. 创建一个包含中文内容的注册消息
    print("\n--- 创建并填充中文消息 ---")
    msg_to_send = MsgHeader()
    msg_to_send.msgID = MsgTag.Registser.value

    # 定义包含中文的字符串
    username_cn = "测试用户"
    email_cn = "用户-测试@例子.com"
    content_cn = "你好，世界！这是一条来自Python的测试消息。"

    # 在赋值前必须编码为'utf-8'字节串
    username_bytes = username_cn.encode('utf-8')
    email_bytes = email_cn.encode('utf-8')
    content_bytes = content_cn.encode('utf-8')
    current_time_bytes = str(int(time.time())).encode('utf-8')
    
    print(f"中文用户名 '{username_cn}' 编码后占 {len(username_bytes)} 字节 (缓冲区大小: 64)")
    print(f"中文内容 '{content_cn[:10]}...' 编码后占 {len(content_bytes)} 字节 (缓冲区大小: 1736)")

    # 赋值给结构体
    msg_to_send.Msg_Payload.Msg_Info.username = username_bytes
    msg_to_send.Msg_Payload.Msg_Info.secret = b"a_very_secure_password"
    msg_to_send.Msg_Payload.Msg_Info.email = email_bytes
    msg_to_send.Msg_Payload.Msg_Info.content = content_bytes
    msg_to_send.Msg_Payload.Msg_Info.time = current_time_bytes
    print("消息结构体填充完毕。")

    # 3. 将结构体转换为字节串用于传输 (序列化)
    print("\n--- 序列化与反序列化测试 ---")
    buffer_to_send = bytes(msg_to_send)
    print(f"成功将结构体序列化为 {len(buffer_to_send)} 字节的缓冲区。")

    # 4. 从字节串中恢复结构体 (模拟接收方反序列化)
    received_msg = MsgHeader.from_buffer_copy(buffer_to_send)
    print("成功从字节缓冲区恢复结构体。")

    # 5. 检查并解码恢复的数据
    print("\n--- 验证恢复后的数据 ---")
    if received_msg.msgID == MsgTag.Registser.value:
        print("接收到 'Register' 消息，类型正确。")
        
        # 解码时，使用.decode('utf-8')，并用.rstrip('\x00')去除末尾的空字节
        username = received_msg.Msg_Payload.Msg_Info.username.decode('utf-8').rstrip('\x00')
        email = received_msg.Msg_Payload.Msg_Info.email.decode('utf-8').rstrip('\x00')
        content = received_msg.Msg_Payload.Msg_Info.content.decode('utf-8').rstrip('\x00')
        received_time = received_msg.Msg_Payload.Msg_Info.time.decode('utf-8').rstrip('\x00')
        
        print(f"  解析出的用户名: {username}")
        print(f"  解析出的Email: {email}")
        print(f"  解析出的内容: {content}")
        print(f"  解析出的时间戳: {received_time}")
        
        # 验证内容是否一致
        if username == username_cn and content == content_cn:
            print("\n[成功] 恢复的数据与原始中文数据完全一致！")
        else:
            print("\n[失败] 恢复的数据与原始数据不符！")
    else:
        print(f"接收到未知消息类型: {received_msg.msgID}")