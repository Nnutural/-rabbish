# 分包

当然，这是一个非常重要且核心的功能。直接在消息体中塞入大块数据（如整个文件内容）是不可行的，因为它会超出网络缓冲区的大小，导致发送失败或数据损坏。

实现分包传输需要我们设计一个简单的**应用层协议**。这个协议的核心思想是：

1. **开始传输 (Initiation)**: 发送方先告诉接收方：“我要开始给你发一个大文件了，它叫directory.json，总共有N个包，总大小是X字节。”
2. **数据分块 (Chunking)**: 发送方将数据切成一个个小块，然后为每个小块打包，并附上序列号（例如，“这是第i个包”）。
3. **结束传输 (Termination)**: 所有分块发送完毕后，发送方再告诉接收方：“文件发完了。”
4. **数据重组 (Reassembly)**: 接收方根据收到的“开始”消息准备接收，然后根据序列号将收到的数据块按顺序拼接起来，直到收到“结束”消息，最后将拼接好的数据进行处理。

下面，我将以**服务器向客户端发送通讯录**为例，详细说明如何修改代码来实现这个协议。

---

### 第1步：修改 schema.py - 定义分包协议的结构体

我们需要定义三个新的消息类型来管理传输过程。为了通用性，我们不叫DirectoryChunkMsg，而是叫DataChunkMsg，这样它也可以用于文件、图片等。

在 schema.py 中，我们可以添加一个新的 MsgTag 分类和对应的 dataclass：

Generated python

```python
# schema.py

# ... 在 MsgTag Enum 中添加一个新的分类 ...
class MsgTag(Enum):
    # ... 原有的 tags ...

    # --- File Transfer Protocol ---
    StartTransfer = 31
    DataChunk = 32
    EndTransfer = 33

# ... 在文件末尾添加新的 dataclass 定义 ...

# =================================================================
#               FILE TRANSFER DATACLASSES
# =================================================================

@dataclass
class StartTransferMsg:
    """
    通用大文件/数据传输开始的信令 (Tag: 31)
    可以用于 S->C, C->S, P2P
    """
    transfer_id: str  # 唯一标识本次传输，使用UUID
    file_name: str    # 传输内容的描述性名称 (e.g., "directory.json", "avatar.jpg")
    total_size: int   # 总字节数
    total_chunks: int # 总分块数
    chunk_size: int   # 每个分块的大小
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.StartTransfer, init=False)

@dataclass
class DataChunkMsg:
    """
    数据块消息 (Tag: 32)
    """
    transfer_id: str  # 关联到哪次传输
    chunk_index: int  # 当前是第几个块 (从0开始)
    data: bytes       # 数据块的二进制内容
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.DataChunk, init=False)

@dataclass
class EndTransferMsg:
    """
    数据传输结束的信令 (Tag: 33)
    """
    transfer_id: str
    status: str       # 'success' or 'cancelled'
    time: int = field(default_factory=get_timestamp)
    tag: MsgTag = field(default=MsgTag.EndTransfer, init=False)
```

**content_copydownload**Use code [**with caution**](https://support.google.com/legal/answer/13505487).Python

**为什么这样做？**

- **通用性**: 这套结构体可以用来传输任何二进制数据，不仅仅是通讯录。
- **transfer_id**: 这是一个关键字段。它确保了即使有多个文件同时传输，接收方也能正确地将分块归属到对应的文件。
- **元数据**: StartTransferMsg 提供了所有必要的元数据，接收方可以用它来初始化接收缓冲区、显示进度条等。

---

### 第2步：在 Transaction_Server.py 中实现发送逻辑

我们需要一个新的辅助函数来处理分包发送的整个过程。

Generated python

```python
# Transaction_Server.py

# ... 导入 ...
import uuid
import math
from serializer import serialize # 确保已导入

# 定义一个常量
CHUNK_SIZE = 4096 # 每次发送 4KB，这是一个常用的大小

def send_large_data(sock, data_bytes: bytes, file_name: str):
    """
    将大的二进制数据分块发送给指定的socket。
    这个函数会处理整个 Start -> Chunk -> End 的流程。
    """
    try:
        # 1. 准备元数据
        transfer_id = str(uuid.uuid4())
        total_size = len(data_bytes)
        total_chunks = math.ceil(total_size / CHUNK_SIZE)

        # 2. 发送 StartTransferMsg
        start_msg = S.StartTransferMsg(
            transfer_id=transfer_id,
            file_name=file_name,
            total_size=total_size,
            total_chunks=total_chunks,
            chunk_size=CHUNK_SIZE
        )
        sock.sendall(serialize(start_msg))
        print(f"[服务器日志] 开始传输 '{file_name}' (ID: {transfer_id}), 共 {total_chunks} 块。")

        # 3. 循环发送 DataChunkMsg
        for i in range(total_chunks):
            start = i * CHUNK_SIZE
            end = start + CHUNK_SIZE
            data_chunk = data_bytes[start:end]
            
            chunk_msg = S.DataChunkMsg(
                transfer_id=transfer_id,
                chunk_index=i,
                data=data_chunk
            )
            sock.sendall(serialize(chunk_msg))
            # print(f"  > 已发送块 {i+1}/{total_chunks}") # 可选：用于调试
            # time.sleep(0.001) # 可选：防止网络拥塞，但TCP的流控通常能处理

        # 4. 发送 EndTransferMsg
        end_msg = S.EndTransferMsg(transfer_id=transfer_id, status='success')
        sock.sendall(serialize(end_msg))
        print(f"[服务器日志] 传输 '{file_name}' (ID: {transfer_id}) 完成。")
        return True

    except Exception as e:
        print(f"[服务器错误] 传输 '{file_name}' 失败: {e}")
        # (可选) 可以尝试发送一个 'cancelled' 的 EndTransferMsg
        try:
            end_msg = S.EndTransferMsg(transfer_id=transfer_id, status='cancelled')
            sock.sendall(serialize(end_msg))
        except Exception:
            pass # 如果发送也失败，就没办法了
        return False
```

**content_copydownload**Use code [**with caution**](https://support.google.com/legal/answer/13505487).Python

---

### 第3步：修改 handle_send_directory 和 server.py 的主循环

现在，handle_send_directory 的职责不再是返回一个消息，而是调用我们刚刚创建的 send_large_data 函数来主动发送一系列消息。

**这对你的 server.py 主循环是一个重大的架构改变！** 原来的 request -> process -> reply 模式不再适用。处理函数现在需要直接访问socket。

### **修改 server.py**

Generated python

```python
# server.py

# ...
def msg_process(ssl_connect_sock):
    try:
        received_msg = T.recv_msg(ssl_connect_sock)
        if received_msg is None:
            # ...
            return None

        # 将 socket 传递给处理函数
        if received_msg.tag.name == "Login":
            reply_msg = T.handle_login(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))
        
        elif received_msg.tag.name == "Register":
            reply_msg = T.handle_register(received_msg)
            ssl_connect_sock.sendall(serialize(reply_msg))
        
        # ... 其他简单回复的消息 ...

        # **重要改变**：对于需要分包的请求，处理函数自己负责发送，不再返回reply_msg
        elif received_msg.tag.name == "GetDirectory":
            T.handle_send_directory(ssl_connect_sock, received_msg) # 直接调用，不接收返回值
        
        # ...
        
        # 对于简单消息，可以保留原来的模式，或者统一风格
        # if reply_msg:
        #    ssl_connect_sock.sendall(serialize(reply_msg))

        return True # 表示处理成功，继续循环

    except ConnectionResetError:
        # ...
        return None
    except Exception as e:
        # ...
        return None
```

**content_copydownload**Use code [**with caution**](https://support.google.com/legal/answer/13505487).Python

### **修改 Transaction_Server.py**

Generated python

```python
# Transaction_Server.py

# ...

# 新的 `handle_send_directory` 签名需要接收 socket
def handle_send_directory(sock, msg: S.GetDirectoryMsg):
    print("I'm in send directory")
    # 假设你的通讯录数据在 'data/directory.json'
    try:
        with open('data/directory.json', 'rb') as f: # 以二进制模式读取
            directory_bytes = f.read()
        
        # 调用我们的分包发送函数
        send_large_data(sock, directory_bytes, "directory.json")

    except FileNotFoundError:
        print(f"[服务器错误] 未找到通讯录文件。")
        # 可以发送一个失败的信令，或者直接不回复
        # 为了简单，这里我们只打印日志
    except Exception as e:
        print(f"[服务器错误] 处理发送通讯录时出错: {e}")
```

**content_copydownload**Use code [**with caution**](https://support.google.com/legal/answer/13505487).Python

---

### 第4步：在客户端实现接收和重组逻辑

客户端的接收循环现在需要变得**有状态 (Stateful)**。它需要一个地方来存储正在进行中的文件传输。

在你的 client.py 中：

Generated python

```python
# client.py

# ...

# 在全局或一个类中，需要一个地方来存储正在进行的传输
active_transfers = {}

def client_msg_process(ssl_connect_sock):
    # 这个函数需要一个循环来持续接收消息
    # 你的原版 msg_process 只能处理一次回复，需要改造

    # 伪代码：假设你在一个循环里调用 recv_msg
    while True:
        received_msg = recv_msg(ssl_connect_sock)
        if received_msg is None:
            break

        # --- 新的分包处理逻辑 ---
        if received_msg.tag.name == "StartTransfer":
            transfer_id = received_msg.transfer_id
            print(f"\n[文件接收] 开始接收 '{received_msg.file_name}' ({received_msg.total_size} bytes)...")
            active_transfers[transfer_id] = {
                "file_name": received_msg.file_name,
                "total_chunks": received_msg.total_chunks,
                "data": bytearray(), # 使用 bytearray 高效拼接二进制数据
                "chunks_received": 0
            }

        elif received_msg.tag.name == "DataChunk":
            transfer_id = received_msg.transfer_id
            if transfer_id in active_transfers:
                transfer = active_transfers[transfer_id]
                transfer["data"].extend(received_msg.data)
                transfer["chunks_received"] += 1
                
                # 可选：打印进度
                progress = (transfer["chunks_received"] / transfer["total_chunks"]) * 100
                print(f"\r[文件接收] 进度: {progress:.2f}%", end="")

        elif received_msg.tag.name == "EndTransfer":
            transfer_id = received_msg.transfer_id
            if transfer_id in active_transfers:
                print(f"\n[文件接收] '{active_transfers[transfer_id]['file_name']}' 接收完成!")
                
                # 现在可以处理完整的数据了
                full_data = active_transfers[transfer_id]["data"]
                
                # 例如，如果是通讯录，就解析并保存
                if active_transfers[transfer_id]['file_name'] == 'directory.json':
                    try:
                        # 假设你的 P.init_directory 可以接收数据并处理
                        directory_dict = json.loads(full_data.decode('utf-8'))
                        with open("data.json", 'w', encoding='utf-8') as f:
                             json.dump(directory_dict, f, indent=2)
                        print("[客户端] 通讯录已更新。")
                    except Exception as e:
                        print(f"[客户端] 处理通讯录数据失败: {e}")
                
                # 清理
                del active_transfers[transfer_id]
        
        # --- 原有的消息处理逻辑 ---
        else:
            print(f"\n服务器回复: {received_msg}")
            # ... 你原来的 if/elif 判断 ...
```

**content_copydownload**Use code [**with caution**](https://support.google.com/legal/answer/13505487).Python

### 总结

这个分包传输机制为你提供了一个健壮且可重用的框架，可以轻松地扩展到发送历史记录、文件、照片等任何大块数据上，无论是服务器到客户端，还是P2P之间。关键在于**将传输过程抽象为 "Start-Chunk-End" 三个阶段**，并为它们定义通用的消息结构