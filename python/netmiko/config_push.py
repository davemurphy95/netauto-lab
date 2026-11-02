#!/usr/bin/env python3
"""config_push.py - push VLANs and interface descriptions to IOSv switches.

Reads a YAML file describing one or more devices, connects to each with
Netmiko (in parallel), pushes the configuration, and prints a per-device
pass/fail summary. Credentials come from the LAB_USER / LAB_PASS
environment variables (or an interactive prompt), never from the YAML.

Usage:
    python config_push.py devices.yaml --dry-run
    python config_push.py devices.yaml --save --workers 5
"""
import argparse
import getpass
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)


# ---------- loading and validation ----------
def load_inventory(path):
    """Read and validate the YAML file. Returns (defaults, devices)."""
    with open(path) as fh:
        data = yaml.safe_load(fh) or {}
    defaults = data.get("defaults", {})
    devices = data.get("devices", [])
    if not devices:
        raise ValueError(f"{path}: no 'devices' defined")
    for dev in devices:
        if "host" not in dev:
            raise ValueError(f"device entry missing 'host': {dev}")
        for vlan in dev.get("vlans", []):
            if not 1 <= int(vlan["id"]) <= 4094:
                raise ValueError(f"{dev['host']}: bad VLAN id {vlan['id']}")
            if not str(vlan.get("name", "")).strip():
                raise ValueError(f"{dev['host']}: VLAN {vlan['id']} needs a name")
    return defaults, devices


def build_config(dev):
    """Turn a device's desired state into a list of IOS config lines."""
    lines = []
    for vlan in dev.get("vlans", []):
        lines += [f"vlan {vlan['id']}", f" name {vlan['name']}"]
    for intf in dev.get("interfaces", []):
        lines += [f"interface {intf['name']}", f" description {intf['description']}"]
    return lines


# ---------- per-device work (runs in a worker thread) ----------
def push_to_device(dev, defaults, username, password, dry_run, save):
    """Connect, push, verify. Always returns a result dict; never raises."""
    name = dev.get("name", dev["host"])
    result = {"name": name, "host": dev["host"], "ok": False, "detail": ""}
    commands = build_config(dev)

    if dry_run:
        result.update(ok=True, detail=f"dry run, {len(commands)} lines not sent")
        result["commands"] = commands
        return result

    params = {
        "device_type": dev.get("device_type", defaults.get("device_type", "cisco_ios")),
        "host": dev["host"],
        "username": username,
        "password": password,
        "timeout": dev.get("timeout", defaults.get("timeout", 15)),
        "conn_timeout": dev.get("timeout", defaults.get("timeout", 15)),
    }
    try:
        with ConnectHandler(**params) as conn:
            conn.send_config_set(commands)
            vlan_table = conn.send_command("show vlan brief")
            missing = [str(v["id"]) for v in dev.get("vlans", [])
                       if not any(line.split()[:1] == [str(v["id"])]
                                  for line in vlan_table.splitlines())]
            if missing:
                result["detail"] = f"pushed, but VLANs not found afterwards: {', '.join(missing)}"
                return result
            if save:
                conn.save_config()
        result.update(ok=True, detail=f"{len(commands)} lines pushed"
                                      + (", saved" if save else ""))
    except NetmikoAuthenticationException:
        result["detail"] = "authentication failed (check LAB_USER / LAB_PASS)"
    except NetmikoTimeoutException:
        result["detail"] = "unreachable: connection timed out"
    except OSError as exc:  # refused, no route, DNS failure
        result["detail"] = f"unreachable: {exc}"
    except Exception as exc:  # keep one bad device from killing the run
        result["detail"] = f"{type(exc).__name__}: {exc}"
    return result


# ---------- main ----------
def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("inventory", help="YAML file of devices, VLANs, interfaces")
    parser.add_argument("--workers", type=int, default=5, help="parallel connections")
    parser.add_argument("--dry-run", action="store_true", help="print config, send nothing")
    parser.add_argument("--save", action="store_true", help="write memory after a successful push")
    args = parser.parse_args()

    try:
        defaults, devices = load_inventory(args.inventory)
    except (OSError, ValueError, yaml.YAMLError, KeyError) as exc:
        sys.exit(f"Inventory error: {exc}")

    username = os.environ.get("LAB_USER") or input("Username: ")
    password = os.environ.get("LAB_PASS") or getpass.getpass("Password: ")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(push_to_device, d, defaults, username, password,
                               args.dry_run, args.save) for d in devices]
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            print(f"[{'OK' if res['ok'] else 'FAIL':4}] {res['name']} ({res['host']}): {res['detail']}")
            if args.dry_run:
                print("\n".join(f"        {line}" for line in res["commands"]))

    failed = [r for r in results if not r["ok"]]
    print(f"\n{len(results) - len(failed)} succeeded, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
