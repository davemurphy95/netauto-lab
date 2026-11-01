#!/usr/bin/env python3
"""
Connects to R1, R2, and R3 in a Cisco CML environment concurrently
(using threads) and displays the output of 'show ip interface brief'
on each device.
"""

import threading
from getpass import getpass
from netmiko import ConnectHandler

# --- Device inventory ---
DEVICES = {
    "r1": {"host": "192.168.5.137"},
    "r2": {"host": "192.168.5.138"},
    "r3": {"host": "192.168.5.140"}
}

# Lock to keep printed output from interleaving between threads
print_lock = threading.Lock()


def get_show_ip_int_brief(name, info, username, password):
    device = {
        "device_type": "cisco_ios",
        "host": info["host"],
        "username": username,
        "password": password,
    }

    try:
        connection = ConnectHandler(**device)
        output = connection.send_command("show ip interface brief")
        connection.disconnect()
        result = output
    except Exception as e:
        result = f"Failed to connect: {e}"

    with print_lock:
        print(f"\n{'=' * 60}")
        print(f"{name} ({info['host']})")
        print('=' * 60)
        print(result)


def main():
    username = input("Username: ")
    password = getpass("Password: ")

    threads = []
    for name, info in DEVICES.items():
        t = threading.Thread(
            target=get_show_ip_int_brief,
            args=(name, info, username, password)
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
