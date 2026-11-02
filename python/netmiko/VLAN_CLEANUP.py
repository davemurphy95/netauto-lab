#!/usr/bin/env python3
"""vlan_cleanup.py - scan switches for VLANs and delete all user VLANs.

Reads the same devices.yaml as config_push.py (only host / name / device_type
/ timeout are used; the vlans section is ignored). Two phases:
  1. SCAN   - every switch is queried in parallel for its VLANs
  2. DELETE - after you confirm, the VLANs are removed in parallel and re-checked

Default VLAN 1 and the reserved legacy VLANs 1002-1005 cannot be deleted on
IOS and are always skipped. Use --dry-run to scan only.

Usage:
    python vlan_cleanup.py devices.yaml --dry-run
    python vlan_cleanup.py devices.yaml --save
"""
import argparse
import getpass
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

PROTECTED = {1, 1002, 1003, 1004, 1005}
VLAN_LINE = re.compile(r"^(\d+)\s+(\S+)\s+(active|act/\S+|suspended|sus/\S+)", re.I)


def load_devices(path):
    with open(path) as fh:
        data = yaml.safe_load(fh) or {}
    devices = data.get("devices", [])
    if not devices:
        raise ValueError(f"{path}: no 'devices' defined")
    return data.get("defaults", {}), devices


def parse_vlans(show_vlan_brief):
    """Return {vlan_id: name} for deletable VLANs (continuation port lines are ignored)."""
    vlans = {}
    for line in show_vlan_brief.splitlines():
        match = VLAN_LINE.match(line)
        if match and int(match.group(1)) not in PROTECTED:
            vlans[int(match.group(1))] = match.group(2)
    return vlans


def connect_params(dev, defaults, username, password):
    timeout = dev.get("timeout", defaults.get("timeout", 15))
    return {
        "device_type": dev.get("device_type", defaults.get("device_type", "cisco_ios")),
        "host": dev["host"], "username": username, "password": password,
        "timeout": timeout, "conn_timeout": timeout,
    }


def run_on_device(dev, defaults, username, password, action):
    """Run action(conn) on one device. Returns (ok, detail, data); never raises."""
    try:
        with ConnectHandler(**connect_params(dev, defaults, username, password)) as conn:
            return True, "", action(conn)
    except NetmikoAuthenticationException:
        return False, "authentication failed", None
    except NetmikoTimeoutException:
        return False, "unreachable: connection timed out", None
    except OSError as exc:
        return False, f"unreachable: {exc}", None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}", None


def scan_action(conn):
    return parse_vlans(conn.send_command("show vlan brief"))


def make_delete_action(save):
    def delete_action(conn):
        before = parse_vlans(conn.send_command("show vlan brief"))
        if before:
            conn.send_config_set([f"no vlan {vid}" for vid in sorted(before)])
        left = parse_vlans(conn.send_command("show vlan brief"))
        if save and not left:
            conn.save_config()
        return before, left
    return delete_action


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("inventory", help="devices.yaml")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true", help="scan and report only")
    parser.add_argument("--save", action="store_true", help="write memory after a clean delete")
    args = parser.parse_args()

    try:
        defaults, devices = load_devices(args.inventory)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        sys.exit(f"Inventory error: {exc}")

    username = os.environ.get("LAB_USER") or input("Username: ")
    password = os.environ.get("LAB_PASS") or getpass.getpass("Password: ")
    names = [d.get("name", d["host"]) for d in devices]

    # ---- phase 1: scan ----
    print(f"Scanning {len(devices)} switch(es)...\n")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        scans = list(pool.map(lambda d: run_on_device(d, defaults, username, password, scan_action), devices))

    reachable, total = [], 0
    for dev, name, (ok, detail, vlans) in zip(devices, names, scans):
        if not ok:
            print(f"[FAIL] {name} ({dev['host']}): {detail}")
            continue
        reachable.append(dev)
        total += len(vlans)
        listing = ", ".join(f"{v} ({n})" for v, n in sorted(vlans.items())) or "none"
        print(f"[SCAN] {name} ({dev['host']}): {len(vlans)} deletable VLAN(s): {listing}")

    if args.dry_run or total == 0:
        print("\nDry run, nothing changed." if args.dry_run else "\nNo deletable VLANs found.")
        sys.exit(0 if len(reachable) == len(devices) else 1)

    # ---- confirmation ----
    print(f"\nThis will DELETE {total} VLAN(s) on {len(reachable)} switch(es).")
    print("Ports in a deleted VLAN become inactive until reassigned.")
    if input("Type 'yes' to continue: ").strip().lower() != "yes":
        sys.exit("Aborted, nothing changed.")

    # ---- phase 2: delete ----
    action = make_delete_action(args.save)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        deletes = list(pool.map(lambda d: run_on_device(d, defaults, username, password, action), reachable))

    failures = len(devices) - len(reachable)
    print()
    for dev, (ok, detail, data) in zip(reachable, deletes):
        name = dev.get("name", dev["host"])
        if not ok:
            failures += 1
            print(f"[FAIL] {name} ({dev['host']}): {detail}")
            continue
        before, left = data
        if left:
            failures += 1
            print(f"[FAIL] {name}: VLANs still present: {', '.join(map(str, sorted(left)))}")
        else:
            print(f"[OK]   {name}: deleted {len(before)} VLAN(s)" + (", saved" if args.save else ""))
    print(f"\n{len(devices) - failures} succeeded, {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
