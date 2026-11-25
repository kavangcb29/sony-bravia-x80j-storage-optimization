"""Audit Android TV storage breakdown and app usage history over ADB."""

import argparse
import json
import re
import subprocess


def run_adb(args):
    res = subprocess.run(["adb"] + args, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def main():
    parser = argparse.ArgumentParser(description="Audit storage and app usage on Sony Bravia / Android TV.")
    parser.add_argument("--ip", required=True, help="Local IP address of the TV (e.g. 192.168.1.50)")
    parser.add_argument("--port", default="5555", help="ADB port (default: 5555)")
    args = parser.parse_args()

    subprocess.run(["adb", "connect", f"{args.ip}:{args.port}"], check=True)

    print("=== FILESYSTEM USAGE ===")
    _, df_out, _ = run_adb(["shell", "df", "-h"])
    for line in df_out.splitlines():
        if any(k in line for k in ("Filesystem", "/data", "/storage/emulated", "/mnt/expand")):
            print(line)

    _, r3_out, _ = run_adb(["shell", "pm", "list", "packages", "-3"])
    third_party = {l.replace("package:", "").strip() for l in r3_out.splitlines() if l.strip()}

    _, r_leanback, _ = run_adb([
        "shell", "cmd", "package", "query-activities",
        "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LEANBACK_LAUNCHER",
    ])
    _, r_launcher, _ = run_adb([
        "shell", "cmd", "package", "query-activities",
        "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER",
    ])
    launchable = set()
    for out in (r_leanback, r_launcher):
        for m in re.finditer(r"packageName=([^\s]+)", out):
            launchable.add(m.group(1))

    _, dis_out, _ = run_adb(["shell", "pm", "list", "packages", "-d"])
    disabled = {l.replace("package:", "").strip() for l in dis_out.splitlines() if l.strip()}

    _, disk_out, _ = run_adb(["shell", "dumpsys", "diskstats"])
    names, app_s, dat_s, csh_s = [], [], [], []
    for line in disk_out.splitlines():
        s = line.strip()
        if s.startswith("Package Names: "):
            names = json.loads(s[15:])
        elif s.startswith("App Sizes: "):
            app_s = json.loads(s[11:])
        elif s.startswith("App Data Sizes: "):
            dat_s = json.loads(s[16:])
        elif s.startswith("Cache Sizes: "):
            csh_s = json.loads(s[13:])

    sizes = {n: (app_s[i] + dat_s[i] + csh_s[i]) / (1024 * 1024) for i, n in enumerate(names)}

    _, usage_out, _ = run_adb(["shell", "dumpsys", "usagestats"])
    standby = {}
    for line in usage_out.splitlines():
        s = line.strip()
        if s.startswith("package=") and " u=0 " in s and "usedByUser=" in s:
            m_pkg = re.search(r"package=([^\s]+)", s)
            m_bkt = re.search(r"bucket=(\d+)", s)
            m_ubu = re.search(r"usedByUser=([^\s]+)", s)
            if m_pkg:
                standby[m_pkg.group(1)] = (
                    int(m_bkt.group(1)) if m_bkt else -1,
                    m_ubu.group(1) if m_ubu else "?",
                )

    bucket_names = {5: "EXEMPT", 10: "ACTIVE", 20: "WORKING", 30: "FREQUENT", 40: "RARE", 45: "RESTRICTED", 50: "NEVER"}
    rows = []
    for pkg in sorted((third_party | launchable) - disabled):
        kind = "3rd-Party" if pkg in third_party else "Pre-installed"
        sz = sizes.get(pkg, 0.0)
        bkt, ubu = standby.get(pkg, (-1, "N/A"))
        rows.append((bkt, -sz, pkg, kind, sz, bucket_names.get(bkt, str(bkt)), ubu))

    rows.sort(reverse=True)
    print(f"\n{'Package':42} | {'Type':13} | {'Size':8} | {'Bucket':10} | {'TimeSinceUserUsed'}")
    print("-" * 102)
    for _, _, pkg, kind, sz, bkt_str, ubu in rows:
        print(f"{pkg:42} | {kind:13} | {sz:6.1f}MB | {bkt_str:10} | {ubu}")


if __name__ == "__main__":
    main()
