#!/usr/bin/env python3
"""vlan_push_j2.py - render VLAN config from a Jinja2 template and push it
to multiple switches in parallel with Netmiko.

Usage:
    python vlan_push_j2.py switches.yaml --dry-run   # render only
    python vlan_push_j2.py switches.yaml --save      # push, then write memory
"""
import argparse
import getpass
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml
from jinja2 import Environment, FileSystemLoader
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

env = Environment(loader=FileSystemLoader("."), trim_blocks=True, lstrip_blocks=True)


def load_inventory(path):
    with open(path) as fh:
        data = yaml.safe_load(fh) or {}
    devices = data.get("devices", [])
    if not devices:
        raise ValueError(f"{path}: no 'devices' defined")
    for dev in devices:
        for vlan in dev.get("vlans", []):
            if not 1 <= int(vlan["id"]) <= 4094:
                raise ValueError(f"{dev['name']}: bad VLAN id {vlan['id']}")
            if " " in str(vlan["name"]) or len(str(vlan["name"])) > 32:
                raise ValueError(f"{dev['name']}: VLAN name '{vlan['name']}' must be "
                                 "32 characters or less with no spaces")
    return data.get("defaults", {}), devices


def push(dev, defaults, username, password, commands, save):
    """Push rendered commands to one switch. Returns (name, ok, detail)."""
    name = dev["name"]
    timeout = dev.get("timeout", defaults.get("timeout", 15))
    params = {
        "device_type": dev.get("device_type", defaults.get("device_type", "cisco_ios")),
        "host": dev["host"], "username": username, "password": password,
        "timeout": timeout, "conn_timeout": timeout,
    }
    try:
        with ConnectHandler(**params) as conn:
            output = conn.send_config_set(commands)
            if "% Invalid" in output or "% Incomplete" in output:
                return name, False, f"switch rejected a command:\n{output}"
            table = conn.send_command("show vlan brief")
            missing = [str(v["id"]) for v in dev["vlans"]
                       if not any(line.split()[:1] == [str(v["id"])] for line in table.splitlines())]
            if missing:
                return name, False, f"VLANs missing after push: {', '.join(missing)}"
            if save:
                conn.save_config()
        return name, True, f"{len(dev['vlans'])} VLANs configured" + (", saved" if save else "")
    except NetmikoAuthenticationException:
        return name, False, "authentication failed"
    except NetmikoTimeoutException:
        return name, False, "unreachable: connection timed out"
    except OSError as exc:
        return name, False, f"unreachable: {exc}"
    except Exception as exc:
        return name, False, f"{type(exc).__name__}: {exc}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("inventory")
    parser.add_argument("--template", default="vlans.j2")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true", help="render config, send nothing")
    parser.add_argument("--save", action="store_true", help="write memory after a good push")
    args = parser.parse_args()

    try:
        defaults, devices = load_inventory(args.inventory)
        template = env.get_template(args.template)
    except Exception as exc:
        sys.exit(f"Setup error: {exc}")

    # Render one config per device from the same template
    rendered = {d["name"]: template.render(d).splitlines() for d in devices}

    if args.dry_run:
        for name, lines in rendered.items():
            print(f"===== {name} =====")
            print("\n".join(lines), "\n")
        return

    username = input("Username: ")
    password = getpass.getpass("Password: ")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(
            lambda d: push(d, defaults, username, password, rendered[d["name"]], args.save),
            devices))

    failed = 0
    for name, ok, detail in results:
        failed += not ok
        print(f"[{'OK' if ok else 'FAIL':4}] {name}: {detail}")
    print(f"\n{len(results) - failed} succeeded, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
