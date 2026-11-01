from getpass import getpass
from netmiko import ConnectHandler

device = {
    "device_type": "cisco_ios",
    "host": "192.168.5.137",
    "username": "cisco",
    "password": getpass("Device password: "),
    "session_log": "session1.txt",
}

with ConnectHandler(**device) as connection:
    output = connection.send_command("show ip ospf neighbor", use_textfsm=True)

print(output)
