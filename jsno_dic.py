import json
from re import A
import threading
import time
from queue import Queue
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


if __name__ == "__main__":
    main()
