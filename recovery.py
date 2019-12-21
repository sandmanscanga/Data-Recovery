#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import subprocess
import datetime
import time
import json
import sys
import os


def run_cmd(command, errors=False):
    kwargs = dict(capture_output=True, text=True, shell=True)
    result = subprocess.run(command, **kwargs)
    results = (result.stdout, result.stderr)
    return results if errors else results[0]


def get_root_part_path():
    return run_cmd("findmnt -no SOURCE /")


def lsblk(part_path=None):
    cmd = "lsblk -OJb"
    if part_path is not None:
        cmd += f" {part_path}"
    return json.loads(run_cmd(cmd))


def get_avail_space(part_path):
    return int(lsblk(part_path)["blockdevices"][0]["fsavail"])


def get_target_disk_path():
    disks = []
    for device in lsblk()["blockdevices"]:
        is_disk = device["type"] == "disk"
        is_plug = device["hotplug"] == True
        if is_disk and is_plug:
            disks.append(device["path"])
    if len(disks) == 1:
        return disks[0]
    print("[!] Could not find target drive for recovery.")
    sys.exit(1)


def get_target_part_paths(disk_path):
    parts = []
    disk_dict = lsblk(get_target_disk_path())["blockdevices"][0]
    for child in disk_dict["children"]:
        parts.append(child["path"])
    return parts


def unmount_part(part):
    run_cmd(f"umount {part}")


def unmount_parts(parts):
    for part in parts:
        unmount_part(part)


def get_largest_part(parts):
    part_sizes = []
    for part in parts:
        part_size = int(lsblk(part)["blockdevices"][0]["size"])
        part_sizes.append(part_size)
    largest = max(part_sizes)
    index = [i for i, _ in enumerate(part_sizes) if largest == _]
    if len(index) != 0:
        return parts[index[0]]


def mount_target(target):
    mount_base = "/mnt/VOLATILE"
    run_cmd(f"mkdir {mount_base}")
    run_cmd(f"mount {target} {mount_base}")
    mounted = lsblk(target)["blockdevices"][0]["mountpoint"]
    if mounted is not None:
        return mount_base
    print("[!] Failed to mount the target partition.")
    sys.exit(1)


def check_target_path(mount_path):
    if os.path.isdir(f"{mount_path}/Users") is False:
        print("[!] Could not find 'Users' directory on target partition.")
        sys.exit(1)


def get_target_size(mount_path):
    result = run_cmd(f"du -sb {mount_path}/Users")
    return int(result.split()[0])


def check_remaining_space(source_bytes, target_bytes):
    remaining_space = source_bytes - target_bytes
    space = (((remaining_space / 1024) / 1024) / 1024)
    if space <= 1:
        print("[!] Not enough room on local hard drive to store the backup.")
        required_space = (((target_bytes / 1024) / 1024) / 1024)
        print(f"[!] Need at least {required_space}GB for the backup...")
        current_space = (((source_bytes / 1024) / 1024) / 1024)
        print(f"[!] Local hard drive only has {current_space}GB available...")
        sys.exit(1)


def get_customer_name():
    customer = input("[?] Enter the customer's name: ")
    customer = customer.replace("'", " ")
    customer = customer.replace('"', " ")
    customer = customer.replace(" ", "_")
    return customer


def prep_backup(customer):
    backup_dir = "/root/Customer_Backups"
    today = str(datetime.date.today())
    backup_path = "/".join((backup_dir, customer, today))
    if os.path.isdir(backup_path):
        print(f"[!] The specified backup directory {backup_path} already exists...")
        return None
    else:
        run_cmd(f"mkdir -p {backup_path}")
        return backup_path


def run_recovery(target, backup):
    os.system(f"cp -rvP {target} {backup}")


def main():
    root_path = get_root_part_path()
    root_avail = get_avail_space(root_path)

    disk = get_target_disk_path()
    parts = get_target_part_paths(disk)
    unmount_parts(parts)
    target = get_largest_part(parts)
    mount_path = mount_target(target)

    check_target_path(mount_path)
    target_size = get_target_size(mount_path)
    
    check_remaining_space(root_avail, target_size)

    customer = get_customer_name()
    backup_path = prep_backup(customer)
    if backup_path is None:
        unmount_part(target)
        sys.exit(1)

    print("[+] Running recovery in 5 seconds...")
    time.sleep(5)
    run_recovery(f"{mount_path}/Users", backup_path)
    print("\n[+] Synchronizing data.")
    print("[+] Do not remove the drive yet...")
    run_cmd("sync")
    time.sleep(3)
    unmount_part(target)
    print("\n[+] Recovery successful, you may now remove the customer drive.")
    print(f"[+] The backup is located at {backup_path}")
    print("\n[+] Don't forget to put in your notes and call the customer...")
    print("\n[+] Special Thanks to Adam")


if __name__ == "__main__":
    main()
