#!/usr/bin/env python3
"""
switchport_audit.py

Connects to a Cisco IOS switch with Netmiko, discovers every switchport
on the device, and examines each one: administrative mode, operational
mode, and access/native VLAN.

Usage:
    python3 switchport_audit.py
"""

from getpass import getpass

from netmiko import ConnectHandler
from netmiko.exceptions import NetMikoTimeoutException, NetMikoAuthenticationException

# --- Connection details -----------------------------------------------
# Update host/username for your switch. Password and enable secret are
# no longer hardcoded -- getpass() prompts for them at runtime instead,
# so nothing sensitive sits in this file or in your shell history.
device = {
    "device_type": "cisco_ios",
    "host": "192.168.5.133",     # sw1 -- change to your switch's IP
    "username": "cisco",
    "password": getpass("Password: "),
    "secret": getpass("Enable secret: "),
}


def get_switchport_names(conn):
    """
    Return a list of every switchport interface name on the device,
    pulled from 'show interfaces status' (this command only lists
    switched interfaces -- routed ports and subinterfaces won't
    show up here, which is exactly what we want).
    """
    output = conn.send_command("show interfaces status", use_textfsm=True)

    # use_textfsm returns a list of dicts when ntc-templates has a
    # matching template installed. If it's not installed, Netmiko
    # falls back to returning the raw text instead -- handle both.
    if isinstance(output, list):
        return [entry["port"] for entry in output]

    # Fallback: skip the header line, take the first column of each row.
    names = []
    for line in output.splitlines()[1:]:
        line = line.strip()
        if line:
            names.append(line.split()[0])
    return names


def examine_switchport(conn, interface):
    """
    Run 'show interfaces <interface> switchport' against one interface
    and pull out the fields that matter most for a quick audit: admin
    mode, operational mode, access VLAN, and native VLAN.
    """
    output = conn.send_command(f"show interfaces {interface} switchport")

    result = {"interface": interface}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Administrative Mode:"):
            result["admin_mode"] = line.split(":", 1)[1].strip()
        elif line.startswith("Operational Mode:"):
            result["oper_mode"] = line.split(":", 1)[1].strip()
        elif line.startswith("Access Mode VLAN:"):
            result["access_vlan"] = line.split(":", 1)[1].strip()
        elif line.startswith("Trunking Native Mode VLAN:"):
            result["native_vlan"] = line.split(":", 1)[1].strip()

    return result


def main():
    try:
        conn = ConnectHandler(**device)
    except NetMikoAuthenticationException:
        print("Auth failed -- check username/password/secret.")
        return
    except NetMikoTimeoutException:
        print("Couldn't reach the switch -- check IP and SSH reachability.")
        return

    conn.enable()

    interfaces = get_switchport_names(conn)
    print(f"Found {len(interfaces)} switchports on {device['host']}\n")

    # The for loop: walk every discovered switchport and examine it.
    for interface in interfaces:
        info = examine_switchport(conn, interface)
        print(
            f"{info['interface']:<20} "
            f"admin={info.get('admin_mode', '?'):<10} "
            f"oper={info.get('oper_mode', '?'):<10} "
            f"access_vlan={info.get('access_vlan', '?'):<6} "
            f"native_vlan={info.get('native_vlan', '?')}"
        )

    conn.disconnect()


if __name__ == "__main__":
    main()
