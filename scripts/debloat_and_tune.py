"""Trim app caches, tune UI animation scales, and disable Sony/Google TV bloatware."""

import argparse
import subprocess


BLOAT_PACKAGES = [
    # Telemetry & feedback
    "tv.samba.ssm",
    "tv.samba.ssm.ui",
    "com.sony.dtv.sonybugreportsys",
    "com.google.android.feedback",
    # Retail demo & promos
    "com.sony.dtv.demosupport",
    "com.sony.dtv.demosystemsupport",
    "com.sony.dtv.multiscreendemo",
    "com.sony.dtv.promos",
    "com.sony.dtv.livingfit",
    "com.sony.dtv.sonyselect",
    # Commercial / Hotel B2B services
    "com.sony.dtv.b2b.hotelmode",
    "com.sony.dtv.b2b.rs232csupport",
    "com.sony.dtv.b2b.vendorprotocol",
    "com.sony.dtv.b2b.prosettings",
    "com.sony.dtv.b2b.softap",
]


def adb_shell(cmd):
    return subprocess.run(["adb", "shell"] + cmd, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description="Debloat Sony Bravia TV and tune UI animations.")
    parser.add_argument("--ip", required=True, help="Local IP address of the TV (e.g. 192.168.1.50)")
    parser.add_argument("--port", default="5555", help="ADB port (default: 5555)")
    parser.add_argument("--scale", default="0.75", help="UI animation scale (default: 0.75)")
    parser.add_argument("--adguard-dns", action="store_true", help="Enable AdGuard Private DNS (dns.adguard-dns.com)")
    parser.add_argument("--enable", action="store_true", help="Rollback: re-enable bloat packages, reset scale to 1.0, and turn off Private DNS")
    args = parser.parse_args()

    subprocess.run(["adb", "connect", f"{args.ip}:{args.port}"], check=True)

    scale = "1.0" if args.enable else args.scale
    for key in ("window_animation_scale", "transition_animation_scale", "animator_duration_scale"):
        adb_shell(["settings", "put", "global", key, scale])
    print(f"Animation scales set to {scale}x")

    if args.enable:
        adb_shell(["settings", "put", "global", "private_dns_mode", "off"])
        for pkg in BLOAT_PACKAGES:
            r = adb_shell(["pm", "enable", pkg])
            print(f"ENABLE {pkg}: {r.stdout.strip()} {r.stderr.strip()}")
    else:
        if args.adguard_dns:
            adb_shell(["settings", "put", "global", "private_dns_mode", "hostname"])
            adb_shell(["settings", "put", "global", "private_dns_specifier", "dns.adguard-dns.com"])
            print("Enabled Private DNS: dns.adguard-dns.com")
        trim_res = adb_shell(["pm", "trim-caches", "999999999999"])
        print("Trimmed app caches:", trim_res.returncode)
        for pkg in BLOAT_PACKAGES:
            adb_shell(["am", "force-stop", pkg])
            adb_shell(["pm", "clear", pkg])
            r = adb_shell(["pm", "disable-user", "--user", "0", pkg])
            print(f"DISABLE {pkg}: {r.stdout.strip()} {r.stderr.strip()}")


if __name__ == "__main__":
    main()
