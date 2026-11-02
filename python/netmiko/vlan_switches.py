from getpass import getpass
from concurrent.futures import ThreadPoolExecutor
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

username = input("Username: ")
password = getpass("Password: ")

all_devices = [
    {'device_type': 'cisco_ios', 'host': '192.168.5.133',
     'username': username, 'password': password},
    {'device_type': 'cisco_ios', 'host': '192.168.5.134',
     'username': username, 'password': password},
]


def create_vlans(device):
    """Create VLANs 2-444 on one switch. Returns (host, success, log text)."""
    host = device['host']
    log = []
    try:
        with ConnectHandler(**device) as net_connect:
            for n in range(2, 445):
                log.append(f"Creating VLAN {n}")
                config_commands = [f'vlan {n}', f'name Python_VLAN_{n}']
                output = net_connect.send_config_set(config_commands)
                log.append(output)
                if "% Invalid" in output:
                    raise ValueError(f"Switch rejected config for VLAN {n}")
        return host, True, "\n".join(log)
    except NetmikoAuthenticationException:
        return host, False, "Authentication failed"
    except NetmikoTimeoutException:
        return host, False, "Unreachable: connection timed out"
    except Exception as exc:
        return host, False, "\n".join(log) + f"\n{type(exc).__name__}: {exc}"


with ThreadPoolExecutor(max_workers=len(all_devices)) as pool:
    results = list(pool.map(create_vlans, all_devices))

for host, ok, log in results:
    print(f"\n===== {host}: {'OK' if ok else 'FAILED'} =====")
    print(log)
