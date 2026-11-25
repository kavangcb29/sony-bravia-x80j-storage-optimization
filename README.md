# Sony Bravia X80J — Storage Expansion, Debloat & Performance Guide

A complete diagnostic log, explanation, and ADB toolkit used to fix critical internal storage exhaustion (`4.0 GB` usable out of `16 GB` flash) and improve UI responsiveness on a **Sony Bravia X80J (2021/2022)** running Android 12 / Google TV.

---

## 1. TV Specifications (Verified via ADB)

| Specification | Value |
| :--- | :--- |
| **Marketing Model** | Sony Bravia X80J (2021 / 2022) |
| **Internal Model (`ro.product.model`)** | `BRAVIA 4K VH2` |
| **Product Name / Device** | `BRAVIA_VH2_PA` / `BRAVIA_VH2` |
| **SoC / Platform (`ro.board.platform`)** | MediaTek `mt5895` (ARMv8 Quad-core Cortex-A73) |
| **Usable RAM** | `2.8 GB` (`+ 100 MB` zram swap) |
| **OS Version** | Android 12 (API SDK `31`, Google TV) |
| **Build ID** | `BRAVIA_VH2_PA-user 12 STT2.230505.001.S136 682241 release-keys` |
| **Security Patch** | `2026-05-01` |
| **Seamless A/B Updates (`ro.build.ab_update`)** | `true` (Active slot: `_b`) |
| **Internal Flash Storage** | `16 GB` physical eMMC (`~4.0 GB` user `/data` partition) |

---

## 2. Why Does a 16 GB Sony TV Only Show ~4.0–4.4 GB of Usable Storage?

Although the TV physically contains a **16 GB eMMC** flash chip, Android TV on Sony Bravia VH2 models uses **Seamless A/B System Updates** (`ro.build.ab_update=true`). That means the firmware maintains **two full copies** of the operating system partitions (`_a` and `_b` slots) so OTA updates can install in the background without bricking the TV.

A massive portion of the 16 GB flash is permanently reserved at the bootloader/partition-table level for:
* **Dual system partitions** (`system_a` / `system_b`, `vendor_a` / `vendor_b`, `product_a` / `product_b`, `boot_a` / `boot_b`, `dtbo`, recovery)
* **Sony's proprietary picture, audio, and DRM frameworks** (Widevine, BRAVIA processing engines)
* **Pre-installed OEM/partner system apps** (currently occupying `/dev/block/dm-3` `2.3G`, `dm-4` `403M`, `dm-5` `801M` across active read-only partitions alone)

As a result, the user-writable `/data` partition (`/dev/block/mmcblk0p50`) is only **4.0 GB** (~4.4 GB unformatted), and cannot be safely resized without unlocking the bootloader (which would permanently break Widevine 4K/HDR DRM and risk bricking the TV).

---

## 3. Why This Was Done & Before/After Results

Before optimization, `/data` had dropped to **69 MB free (99% full)**, causing severe UI lag, freezing, and inability to install or update apps. Using wireless ADB, we expanded storage onto a **28 GB USB 3.0 drive** as encrypted Adoptable + Primary Storage, migrated user apps, flushed caches, removed unused apps, disabled background telemetry/retail bloat, and tuned UI animations.

| Metric | Before | After |
| :--- | :--- | :--- |
| **Internal `/data` Free Space** | **69 MB** (`99%` full) | **1.7 GB** (`56%` used) |
| **Primary Shared Storage (`/storage/emulated`)** | `4.0 GB` internal (`69 MB` free) | **28 GB** USB (`27 GB` free, `5%` used) |
| **Default Install Location** | `0 [auto]` | `2 [external]` + `force_allow_on_external=1` |
| **UI Animation Scales** | `1.0x` | `0.75x` |
| **Active Bloat / Telemetry Packages** | Running (`~390+ MB` RAM combined) | **15 packages disabled** |

---

## 4. Key Changes Applied

### A. Adoptable USB 3.0 Storage & Primary Storage Migration
1. **Partitioned USB drive (`disk:8,0`) as encrypted private storage:**
   ```bash
   adb shell sm partition disk:8,0 private
   ```
   *(Note: If an existing NTFS/exFAT partition on the USB is locked by Android's `ModernMediaScanner`, reboot the TV once after writing the new GPT table and re-run `sm partition disk:8,0 private`).*
2. **Unlocked moving all 3rd-party apps & forced external installs by default:**
   ```bash
   adb shell settings put global force_allow_on_external 1
   adb shell settings put global default_install_location 2
   ```
   *(Note: On Android 12, `pm set-install-location 2` throws a `SecurityException` under UID 2000; writing `default_install_location` directly via `settings put global` succeeds).*
3. **Migrated primary shared storage (`/sdcard`, `Android/obb`, `Android/data`) to the USB UUID:**
   ```bash
   adb shell pm move-primary-storage <VOLUME_UUID>
   ```
   *(Note: If `pm move-primary-storage` fails with `Failure [-10]` due to a locked secondary Google TV profile such as `user 10` in quiet mode, temporarily unlock it with `adb shell am start-user -w 10`, run the migration, and stop it afterward with `adb shell am stop-user 10`).*
4. **Moved 19 user-installed apps** onto the USB drive using `pm move-package <package> <VOLUME_UUID>`.

### B. UI Animation Speed (`0.75x`) & Cache Trim
* Tuned animations to `0.75x` (faster response while keeping visible motion):
  ```bash
  adb shell settings put global window_animation_scale 0.75
  adb shell settings put global transition_animation_scale 0.75
  adb shell settings put global animator_duration_scale 0.75
  ```
* Flushed accumulated thumbnail/preview caches across all apps:
  ```bash
  adb shell pm trim-caches 999999999999
  ```

### C. Disabled Telemetry, Retail Demo & Commercial B2B Bloat (15 Packages)
Force-stopped, cleared, and disabled for `user 0` (all reversible via `adb shell pm enable <package>`):
* **Telemetry / Feedback:** `tv.samba.ssm`, `tv.samba.ssm.ui` *(Samba TV ACR tracking)*, `com.sony.dtv.sonybugreportsys`, `com.google.android.feedback`
* **Retail Demo / Promos:** `com.sony.dtv.demosupport`, `com.sony.dtv.demosystemsupport`, `com.sony.dtv.multiscreendemo`, `com.sony.dtv.promos`, `com.sony.dtv.livingfit`, `com.sony.dtv.sonyselect`
* **Commercial / Hotel B2B Daemons:** `com.sony.dtv.b2b.hotelmode`, `com.sony.dtv.b2b.rs232csupport`, `com.sony.dtv.b2b.vendorprotocol`, `com.sony.dtv.b2b.prosettings`, `com.sony.dtv.b2b.softap`

### D. Unused App Audit & Cleanup
Audited via `dumpsys usagestats` (`AppStandby` buckets) and removed 6 unused 3rd-party apps (`com.finalwire.aida64`, `com.graymatrix.did`, `com.crunchyroll.crunchyroid`, `com.eros.now`, `com.balaji.alt`, `com.rkgames.basisgame`).

### E. System-Wide Ad Blocking (Private DNS)
Enabled Android 12's native DNS-over-TLS ad blocking using AdGuard DNS (blocks ad networks and tracking domains across apps without a VPN):
```bash
adb shell settings put global private_dns_mode hostname
adb shell settings put global private_dns_specifier dns.adguard-dns.com
```
*(Rollback: `adb shell settings put global private_dns_mode off`)*

### F. Ad-Free YouTube via SmartTube *(Keeping Official YouTube for Casting)*
DNS blocking cannot strip video ads inside the official YouTube TV app (`com.google.android.youtube.tv`). Instead of removing official YouTube (which is still useful for casting from phones), **SmartTube** (`org.smarttube.stable`) was installed directly onto the adopted USB drive using the `armeabi-v7a` build (Sony Bravia VH2 runs a 32-bit `armeabi-v7a` Android userland):
```bash
adb install --force-uuid <VOLUME_UUID> SmartTube_stable_armeabi-v7a.apk
```

---

## 5. Credits & Useful Links

* **SmartTube (Ad-Free Open-Source YouTube Client for Android TV):** Huge thanks to **[yuliskov/SmartTube](https://github.com/yuliskov/SmartTube)** for providing an open-source, ad-free, SponsorBlock-enabled YouTube client for Android TV.
  * Download official releases directly here: **[SmartTube Releases on GitHub](https://github.com/yuliskov/SmartTube/releases)** *(use the `armeabi-v7a` APK for Sony Bravia X80J)*.
* **AdGuard DNS:** System-wide DNS-over-TLS ad/tracker filtering (`dns.adguard-dns.com`).

---

## 6. Included Scripts

All scripts are in [`scripts/`](scripts/) and take `--ip <TV_IP_ADDRESS>`:

* [`scripts/audit_storage_and_usage.py`](scripts/audit_storage_and_usage.py) — Inspects `/data` & USB usage, top storage-consuming packages (`dumpsys diskstats`), and unused apps (`dumpsys usagestats`).
* [`scripts/adopt_usb_storage.py`](scripts/adopt_usb_storage.py) — Detects USB disks, partitions a selected disk as private adoptable storage, sets `force_allow_on_external=1` & `default_install_location=2`, and migrates primary storage.
* [`scripts/move_user_apps.py`](scripts/move_user_apps.py) — Moves all 3rd-party packages onto the adopted USB volume UUID.
* [`scripts/debloat_and_tune.py`](scripts/debloat_and_tune.py) — Trims app caches, sets animation scales (`0.75` by default), and disables (or `--enable` restores) the 15 bloatware/telemetry packages.

---

## 7. Further Hardware & UI Tips

* **Small USB SSD vs. USB Flash Drive vs. HDD:** A low-power **SATA SSD in a USB 3.0 UASP enclosure** (or Samsung T5/T7) is significantly faster and longer-lasting than standard USB flash drives due to much higher 4K random IOPS and wear leveling. Avoid spinning mechanical HDDs for adoptable storage (high latency + USB power draw issues).
* **Apps-Only Mode / Projectivy Launcher:** Enabling **Apps-only mode** (`Settings → Accounts & Sign-in → [Account] → Apps-only mode`) or switching to **Projectivy Launcher** eliminates Google TV's heavy trailer/recommendation feeds (`~135 MB` RAM).
* **5 GHz Wi-Fi vs. Ethernet:** The X80J's built-in Ethernet port is capped at `100 Mbps`; **5 GHz Wi-Fi** (or a USB 3.0 Gigabit Ethernet adapter) delivers faster download and high-bitrate streaming speeds.
