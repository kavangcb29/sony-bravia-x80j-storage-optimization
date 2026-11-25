"""Format an attached USB drive as private adoptable storage and set as primary target."""

import argparse
import re
import subprocess
import sys


def adb_shell(cmd):
    return subprocess.run(["adb", "shell"] + cmd, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description="Adopt USB 3.0 drive as primary Android TV storage.")
    parser.add_argument("--ip", required=True, help="Local IP address of the TV (e.g. 192.168.1.50)")
    parser.add_argument("--port", default="5555", help="ADB port (default: 5555)")
    parser.add_argument("--disk", help="Disk ID from 'sm list-disks' (e.g. disk:8,0)")
    parser.add_argument("--yes", action="store_true", help="Confirm erasing all partitions on the target disk")
    args = parser.parse_args()

    subprocess.run(["adb", "connect", f"{args.ip}:{args.port}"], check=True)

    disks_res = adb_shell(["sm", "list-disks"])
    disks = [d.strip() for d in disks_res.stdout.splitlines() if d.strip()]
    if not disks:
        print("No adoptable USB disks detected. Plug a USB 3.0 drive into the TV first.")
        sys.exit(1)

    target_disk = args.disk or disks[0]
    if target_disk not in disks:
        print(f"Disk '{target_disk}' not found. Available disks: {disks}")
        sys.exit(1)

    if not args.yes:
        print(f"Detected disk(s): {disks}")
        print(f"Re-run with '--disk {target_disk} --yes' to ERASE and adopt it as private storage.")
        sys.exit(0)

    print(f"Partitioning {target_disk} as private adoptable storage...")
    part_res = adb_shell(["sm", "partition", target_disk, "private"])
    if part_res.returncode != 0:
        print("Partitioning failed:", part_res.stdout, part_res.stderr)
        print("If an old NTFS/exFAT partition was locked by MediaScanner, reboot the TV and re-run.")
        sys.exit(1)

    vols_res = adb_shell(["sm", "list-volumes", "private"])
    m = re.search(r"private:\S+\s+mounted\s+([0-9a-fA-F-]+)", vols_res.stdout)
    if not m:
        print("Could not find mounted private volume UUID:\n", vols_res.stdout)
        sys.exit(1)
    uuid = m.group(1)
    print(f"Adopted private volume UUID: {uuid}")

    # Enable moving all apps and set default install location to external (Android 12 safe method)
    adb_shell(["settings", "put", "global", "force_allow_on_external", "1"])
    adb_shell(["settings", "put", "global", "default_install_location", "2"])

    # Unlock any secondary quiet-mode profiles before migrating primary storage
    users_res = adb_shell(["pm", "list", "users"])
    started_secondary = []
    for um in re.finditer(r"UserInfo\{(\d+):", users_res.stdout):
        uid = um.group(1)
        if uid != "0":
            adb_shell(["am", "start-user", "-w", uid])
            started_secondary.append(uid)

    print(f"Migrating primary shared storage (/sdcard) to {uuid}...")
    move_res = adb_shell(["pm", "move-primary-storage", uuid])
    print("Migration result:", move_res.stdout.strip(), move_res.stderr.strip())

    for uid in started_secondary:
        adb_shell(["am", "stop-user", uid])

    print("\nFinal Storage Layout:")
    print(adb_shell(["df", "-h", "/data", "/storage/emulated", f"/mnt/expand/{uuid}"]).stdout)


if __name__ == "__main__":
    main()
