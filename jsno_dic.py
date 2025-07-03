import json
from re import A
import threading
import time
from queue import Queue
import json
import os
import socket as skt
from typing import List, Dict, Any, Set

# 导入时间戳函数
from schema import get_timestamp
dic = {}
name_status_map = {}

# def thread_job():
#     print("T1 start\n")
#     for i in range(10):
#         time.sleep(1)
#     print("T1 finish\n")

# def t2_job():
#     print("T2 start\n")
#     print("T2 finish\n")

# def main():
#     # t = threading.Thread(target = thread_job, name = "T1")
#     # t2 = threading.Thread(target = t2_job, name = "T2")
#     # t.start() # 启动线程
#     # t2.start()
#     # # t.join() # 在该行等待线程结束
#     # print("all done\n")


# if __name__ == "__main__":
#     main()





# import socket

# def bind_to_free_port():
#     """
#     创建一个socket并绑定到一个由操作系统自动分配的空闲端口。
#     返回绑定好的socket和它实际使用的端口号。
#     """
#     try:
#         # 1. 创建一个socket
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
#         # 2. 调用bind，主机地址设为 "0.0.0.0" 或 "127.0.0.1"，端口号设为 0
#         # "0.0.0.0" 表示监听所有可用的网络接口
#         sock.bind(("0.0.0.0", 0)) 
        
#         # 3. bind之后，通过getsockname()获取操作系统实际分配的端口号
#         port = sock.getsockname()[1]
        
#         print(f"操作系统已成功分配端口: {port}")
        
#         return sock, port
        
#     except Exception as e:
#         print(f"无法绑定到空闲端口: {e}")
#         return None, None

# # --- 使用 ---
# # 1. 获取一个绑定好空闲端口的socket
# p2p_server_sock, my_p2p_port = bind_to_free_port()

# if p2p_server_sock:
#     # 2. 现在你可以用这个socket去listen
#     p2p_server_sock.listen(5)
#     print(f"P2P监听已在端口 {my_p2p_port} 上启动...")


class ContactManager:
    """
    管理单个用户的通讯录。
    每个用户都有一个独立的JSON文件来存储其联系人列表。
    """
    def __init__(self, username: str):
        self.username = username
        # 为每个用户创建一个独立的通讯录文件
        self.filepath = os.path.join('data', 'directory', f"{self.username}.json")
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
        # # 1. 根据时间戳对联系人进行降序排序
        # self.contacts.sort(key=lambda c: c.get('time', 0), reverse=True)
        
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

# user_dic = ContactManager("11")
# user_dic._save_contacts()

# 1. 创建一个socket
sock = skt.socket(skt.AF_INET, skt.SOCK_STREAM)

# 2. 调用bind，主机地址设为 "0.0.0.0" 或 "127.0.0.1"，端口号设为 0
# "0.0.0.0" 表示监听所有可用的网络接口
sock.bind(("0.0.0.0", 0)) 

# 3. bind之后，通过getsockname()获取操作系统实际分配的端口号
port = sock.getsockname()[1]

print(f"操作系统已成功分配端口: {port}")



'''

# 1. 为 'bob' 创建一个管理器
bob_manager = ContactManager("bob")

# 2. 获取他当前的联系人（应该是空的）
print("Bob的初始联系人:", bob_manager.get_contacts())

# 3. 添加一个新联系人 'charlie'
print("\n-> 添加 Charlie")
bob_manager.add_or_update_contact({
    "name": "charlie",
    "status": "offline",
    "address": "127.0.0.1:50002",
    "time": int(time.time()) - 3600 # 假设一小时前联系过
})
time.sleep(1) # 暂停一秒，确保时间戳不同

# 4. 添加另一个联系人 'david'
print("\n-> 添加 David")
bob_manager.add_or_update_contact({
    "name": "david",
    "status": "offline",
    "address": "127.0.0.1:50003",
    "time": int(time.time()) # 刚刚联系
})

# 5. 查看 Bob 的通讯录
# 注意：David 应该在 Charlie 前面，因为他的时间戳更新，且ID应该是1
print("\nBob的当前通讯录 (已自动排序和分配ID):")
for contact in bob_manager.get_contacts():
    print(contact)

# 6. 更新 'charlie' 的状态为 online，并更新时间戳
print("\n-> 更新 Charlie 的状态")
bob_manager.add_or_update_contact({
    "name": "charlie",
    "status": "online",
    "time": int(time.time()) # 更新为当前时间
})

# 7. 再次查看通讯录
# 现在 Charlie 应该是列表中的第一个，因为他的时间戳最新！
print("\nBob的最终通讯录 (Charlie 现在是第一个):")
for contact in bob_manager.get_contacts():
    print(contact)

# 8. 查看生成的JSON文件内容
print(f"\n查看文件 '{bob_manager.filepath}' 的内容:")
with open(bob_manager.filepath, 'r') as f:
    print(f.read())
'''





def json_dic():
    with open("data.json", "r", encoding = "utf-8") as f:
        dic = json.load(f )

    # print(dic)

    contacts = dic.get("contacts")
    for key in contacts:
        print(key.get("name"), key.get("status"))
        pass

    # name_status_map = {c["name"]: c["status"] for c in dic.get("contacts", [])}
    # for name, status in name_status_map.items():
    #     if status == "online":
    #         print(name, status)

    # print(name_status_map.keys())

    # while True:
    #     choice = input("which friend do you want to send message to: ").strip()
    #     if choice in name_status_map.keys(): # 判断人名是否在本地联系人列表中然后判断是否在线
    #         if name_status_map[choice] == "online":
    #             print("=======Now you are chatting with {} =======".format(choice))
    #         else:
    #             print("=======The user is offline =======".format(choice))
    #     else:
    #         print("=======The user is not in your contact list =======".format(choice))
    #         print("RECHOICE: ")


def thread_job():
    print("T1 start\n")
    for i in range(10):
        time.sleep(0.2)
    print("T1 finish\n")

def t2_job():
    print("T2 start\n")
    print("T2 finish\n")

def job(l,q):
    for i in range(len(l)):
        l[i] = l[i]**2
    q.put(l)


def multithread():
    q = Queue()
    threads = []
    data = [[1,2,3],[4,5,6],[7,8,9],[10,11,12]]
    for i in range(4):
        t = threading.Thread(target = job, args=(data[i],q))
        t.start()
        threads.append(t)
    for thread in threads:
        thread.join()

    results = []
    for _ in range(4):
        results.append(q.get())
    print(results)




lock = threading.Lock()
A = 0

def main():

    t1 = threading.Thread(target = job1)
    t2 = threading.Thread(target = job2)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

def job1():
    global A, lock
    lock.acquire()
    for i in range(10):
        A += 1
        print('job1', A)
    lock.release()

def job2():
    global A, lock
    lock.acquire()
    for i in range(10):
        A += 10
        print('job2', A)
    lock.release()
    #multithread()


    # t = threading.Thread(target = thread_job, name = "T1")
    # t2 = threading.Thread(target = t2_job, name = "T2")
    # t.start() # 启动线程
    # t2.start()
    # t2.join() # 在该行等待线程结束
    # t.join()
    # print("all done\n")
    
    
    
    # json_dic()


#if __name__ == "__main__":
 #   main()
