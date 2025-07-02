import json
name_status_map = {}

def init_directory(ssl_connect_sock):
    ''' 输出本地联系人列表 '''
    directionary = {}

    with open("data.json", "r", encoding = "UTF-8") as f:
        directionary = json.load(f)

    # contacts = directionary.get("contacts")
    # for key in contacts:
    #     print(key.get("name"), key.get("status"))
    # 只保存名字和状态，其他信息忽略
    name_status_map = {c["name"]: c["status"] for c in directionary.get("contacts", [])}
    for name, status in name_status_map.items():
        print(name, status)


def choose_friend(ssl_connect_sock, choice):
    if choice == "exit":
        return None # 这里会直接退出程序

    if choice in name_status_map.keys(): # 判断人名是否在本地联系人列表中然后判断是否在线
        if name_status_map[choice] == "online":
            print("=======Now you are chatting with {} =======".format(choice))
            return True
        else:
            print("=======The user is offline =======".format(choice))
            return True
    else:
        print("=======The user is not in your contact list =======".format(choice))
        print("RECHOICE: ")
        return True
    '''
    ????
    提前建立连接还是等用户选择后建立连接
    之后进入哪一步？
    '''