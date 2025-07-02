import json
dic = {}
name_status_map = {}

with open("data.json", "r", encoding = "utf-8") as f:
    dic = json.load(f )

contacts = dic.get("contacts")
for key in contacts:
    # print(key.get("name"), key.get("status"))
    pass

name_status_map = {c["name"]: c["status"] for c in dic.get("contacts", [])}
for name, status in name_status_map.items():
    if status == "online":
        print(name, status)

print(name_status_map.keys())

while True:
    choice = input("which friend do you want to send message to: ").strip()
    if choice in name_status_map.keys(): # 判断人名是否在本地联系人列表中然后判断是否在线
        if name_status_map[choice] == "online":
            print("=======Now you are chatting with {} =======".format(choice))
        else:
            print("=======The user is offline =======".format(choice))
    else:
        print("=======The user is not in your contact list =======".format(choice))
        print("RECHOICE: ")
