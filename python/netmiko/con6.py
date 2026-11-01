import os
from dotenv import load_dotenv
from netmiko import ConnectHandler

load_dotenv()  # reads .env from the current folder

device = {
    "device_type": "cisco_ios",
    "host": "192.168.5.137",
    "username": os.environ["DEVICE_USER"],
    "password": os.environ["DEVICE_PASS"],
    "session_log": "route.txt",
}

with ConnectHandler(**device) as connection:
    output = connection.send_command("show ip ospf neighbor", use_textfsm=True)

print(output)
