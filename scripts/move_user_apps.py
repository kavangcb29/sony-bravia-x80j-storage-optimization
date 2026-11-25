"""Move all third-party installed apps onto the adopted USB storage volume."""

import argparse
import re
import subprocess
import sys


def adb_shell(cmd):
    return subprocess.run(["adb", "shell"] + cmd, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description="Move 3rd-party Android TV apps to adopted USB storage.")
    parser.add_argument("--ip", required=True, help="Local IP address of the TV (e.g. 192.168.1.50)")
    parser.add_argument("--port", default="5555", help="ADB port (default: 5555)")
    parser.add_argument("--uuid", help="Target private volume UUID (auto-detected if omitted)")
    args = parser.parse_args()

    subprocess.run(["adb", "connect", f"{args.ip}:{args.port}"], check=True)

    uuid = args.uuid
    if not uuid:
        vols = adb_shell(["sm", "list-volumes", "private"]).stdout
        m = re.search(r"private:\S+\s+mounted\s+([0-9a-fA-F-]+)", vols)
        if not m:
            print("No mounted private USB volume found. Run adopt_usb_storage.py first.")
            sys.exit(1)
        uuid = m.group(1)

    print(f"Target USB volume UUID: {uuid}")
    pkgs_out = adb_shell(["pm", "list", "packages", "-3"]).stdout
    packages = [l.replace("package:", "").strip() for l in pkgs_out.splitlines() if l.strip()]

    moved, skipped = 0, 0
    for pkg in packages:
        adb_shell(["am", "force-stop", pkg])
        res = adb_shell(["pm", "move-package", pkg, uuid])
        out = (res.stdout + " " + res.stderr).strip()
        if res.returncode == 0 and "Success" in out:
            moved += 1
            print(f"MOVED: {pkg}")
        else:
            skipped += 1
            print(f"SKIP:  {pkg} -> {out}")

    print(f"\nSummary: Moved={moved}, Skipped={skipped}")
    print(adb_shell(["df", "-h", "/data", f"/mnt/expand/{uuid}"]).stdout)


if __name__ == "__main__":
    main()
