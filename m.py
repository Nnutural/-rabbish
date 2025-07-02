import ctypes

# 定义常量
PACKET_SIZE = 1012 # 1024 - sizeof(int)*3

# 1. 模拟 enum
# 在ctypes中，我们通常用整数来表示enum。
# ctypes.c_int 默认是4字节，对于Msg_Tag来说足够了。
class MsgTag:
    FILE_NAME = 1
    FILE_SIZE = 2
    READY_RECV = 3
    SEND_DATA = 4
    ALL_ACCPTED = 5
    GET_FILE_FAILED = 6
    FINISH = 7

# 2. 定义内部的 struct FileInfo 和 FileData
# 这些结构体也将继承自 ctypes.Structure
class FileInfo(ctypes.Structure):
    # _pack_ = 1 对应 C++ 的 #pragma pack(1)
    # 这确保了没有填充字节，所有成员紧密排列。
    _pack_ = 1
    _fields_ = [
        ("FileName", ctypes.c_char * 256),
        ("FileSize", ctypes.c_int)
    ]

class FileData(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("packetNo", ctypes.c_int),
        ("packetSize", ctypes.c_int),
        ("DataBuff", ctypes.c_char * PACKET_SIZE)
    ]

# 3. 定义 Union
# 所有字段共享同一块内存
class MsgPayload(ctypes.Union):
    _pack_ = 1
    _fields_ = [
        ("FileInfo", FileInfo),
        ("FileData", FileData)
    ]

# 4. 定义顶层的主结构体 MsgHeader
class MsgHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("msgID", ctypes.c_int), # 使用c_int来匹配C++的enum大小
        ("payload", MsgPayload)
    ]

# --- 使用示例 ---

# 1. 创建一个消息实例并填充数据 (发送方)
print("--- 创建并打包消息 ---")
# 我们要发送一个文件名的消息
msg_to_send = MsgHeader()
msg_to_send.msgID = MsgTag.FILE_NAME

# 访问union中的FileInfo部分
# 注意：需要将Python字符串编码为字节串
file_path = "D:/path/to/my/document.txt"
msg_to_send.payload.FileInfo.FileName = file_path.encode('utf-8')
# FileSize字段在FILE_NAME消息中未使用，但我们还是可以设置它
msg_to_send.payload.FileInfo.FileSize = 0 

# 2. 将结构体转换为字节串用于传输
# ctypes结构体可以直接被转换成bytes
buffer_to_send = bytes(msg_to_send)

# 验证大小是否正确
# msgID(4) + FileName(256) + FileSize(4) = 264
# msgID(4) + packetNo(4) + packetSize(4) + DataBuff(1012) = 1024
# union的大小是其最大成员的大小，即FileData (1024 - 4 - 4 = 1016)
# MsgHeader大小 = msgID(4) + union(max(260, 1020)) = 4 + 1020 = 1024 
# 这个计算似乎有点问题，让我们重新检查C++
# sizeof(int) = 4, PACKET_SIZE = 1012
# sizeof(FileInfo) = 256 + 4 = 260
# sizeof(FileData) = 4 + 4 + 1012 = 1020
# sizeof(union) = max(260, 1020) = 1020
# sizeof(MsgHeader) = sizeof(Msg_Tag) + sizeof(union) = 4 + 1020 = 1024
print(f"MsgHeader size: {ctypes.sizeof(MsgHeader)} bytes")
print(f"FileInfo size: {ctypes.sizeof(FileInfo)} bytes")
print(f"FileData size: {ctypes.sizeof(FileData)} bytes")
print(f"Payload (Union) size: {ctypes.sizeof(MsgPayload)} bytes")
print(f"Buffer size to send: {len(buffer_to_send)} bytes")

# 假设这里是网络传输...
# socket.sendall(buffer_to_send)


# 3. 从字节串中恢复结构体 (接收方)
print("\n--- 从字节串中解包消息 ---")
# 假设我们收到了这个buffer
received_buffer = buffer_to_send

# 从内存（字节串）中创建MsgHeader实例
msg_received = MsgHeader.from_buffer_copy(received_buffer)

# 检查msgID来决定如何解析union
print(f"Received msgID: {msg_received.msgID}")

if msg_received.msgID == MsgTag.FILE_NAME:
    # 访问FileInfo字段
    file_name_bytes = msg_received.payload.FileInfo.FileName
    # 将字节串解码回Python字符串
    received_file_name = file_name_bytes.decode('utf-8').rstrip('\x00')
    print(f"Interpreted as FILE_NAME. File name: '{received_file_name}'")

# --- 另一个例子：FileData ---
print("\n--- 创建并打包 SEND_DATA 消息 ---")
data_msg = MsgHeader()
data_msg.msgID = MsgTag.SEND_DATA
data_msg.payload.FileData.packetNo = 1
data_msg.payload.FileData.packetSize = 5
data_msg.payload.FileData.DataBuff = b'hello'

data_buffer = bytes(data_msg)

# 解包
data_msg_received = MsgHeader.from_buffer_copy(data_buffer)
if data_msg_received.msgID == MsgTag.SEND_DATA:
    p_no = data_msg_received.payload.FileData.packetNo
    p_size = data_msg_received.payload.FileData.packetSize
    p_data = data_msg_received.payload.FileData.DataBuff[:p_size] # 只读取有效的字节
    print(f"Interpreted as SEND_DATA. PacketNo: {p_no}, Size: {p_size}, Data: {p_data}")