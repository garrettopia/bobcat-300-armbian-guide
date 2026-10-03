#!/usr/bin/env python3
"""
Bobcat Miner 300 (RK3566, G290 / G295) - Automated MicroSD Preparation Script
=============================================================================
This script safely writes the BobcatArmbian29x image to your MicroSD card and
automatically applies the critical bootloader fixes:
  1. Fixes rootfs PARTUUID in boot.cmd (eliminates kernel mount panics).
  2. Ensures initramfs (uInitrd) is loaded by U-Boot.
  3. Pre-configures Wi-Fi credentials for NetworkManager.
  4. (Optional) Injects your SSH public key for instant passwordless root access.
  5. Compiles boot.scr with mkimage and cleanly unmounts the card.

Usage:
  sudo python3 flash_and_prep_sd.py --device /dev/sdX --image /path/to/BobcatArmbian29x.img
"""

import argparse
import os
import subprocess
import sys
import time

PROTECTED_DEVICES = {"sda", "nvme0n1"}

def run_cmd(cmd, check=True):
    print(f"[*] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[-] Command failed: {res.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return res.stdout.strip()

def main():
    if os.geteuid() != 0:
        print("[-] This script must be run as root (sudo).", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Prepare Bobcat 300 Armbian MicroSD Card")
    parser.add_argument("--device", required=True, help="Target block device (e.g. /dev/sdb)")
    parser.add_argument("--image", required=True, help="Path to BobcatArmbian29x.img")
    parser.add_argument("--wifi-ssid", default="", help="Wi-Fi Network SSID (Optional)")
    parser.add_argument("--wifi-pass", default="", help="Wi-Fi Network Password (Optional)")
    parser.add_argument("--ssh-key", default="", help="Path to your id_ed25519.pub / id_rsa.pub (Optional)")
    args = parser.parse_args()

    dev_base = os.path.basename(args.device)
    if dev_base in PROTECTED_DEVICES:
        print(f"[-] Refusing to write to protected host device: {args.device}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.image):
        print(f"[-] Image file not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    print("=" * 65)
    print("   BOBCAT MINER 300 (RK3566) - SD CARD BUILDER")
    print(f"   Target Device : {args.device}")
    print(f"   Source Image  : {args.image}")
    print("=" * 65)

    confirm = input(f"WARNING: ALL DATA ON {args.device} WILL BE DESTROYED. Continue? (yes/no): ")
    if confirm.strip().lower() != "yes":
        print("[-] Aborted by user.")
        sys.exit(0)

    # 1. Unmount existing partitions
    print("[1/6] Unmounting any active partitions...")
    for i in range(1, 9):
        part = f"{args.device}{i}" if not args.device[-1].isdigit() else f"{args.device}p{i}"
        subprocess.run(["umount", part], capture_output=True)

    # 2. Write image with dd
    print(f"[2/6] Writing image to {args.device} (this takes ~1-2 minutes)...")
    cmd_dd = ["dd", f"if={args.image}", f"of={args.device}", "bs=4M", "status=progress", "conv=fsync"]
    subprocess.run(cmd_dd, check=True)
    subprocess.run(["sync"])
    subprocess.run(["partprobe", args.device])
    time.sleep(2)

    # 3. Mount partitions
    p_boot = f"{args.device}1" if not args.device[-1].isdigit() else f"{args.device}p1"
    p_root = f"{args.device}2" if not args.device[-1].isdigit() else f"{args.device}p2"

    mnt_boot = "/tmp/bobcat_mnt_boot"
    mnt_root = "/tmp/bobcat_mnt_root"
    os.makedirs(mnt_boot, exist_ok=True)
    os.makedirs(mnt_root, exist_ok=True)

    print(f"[3/6] Mounting {p_boot} and {p_root}...")
    run_cmd(["mount", p_boot, mnt_boot])
    run_cmd(["mount", p_root, mnt_root])

    # 4. Get Root PARTUUID
    partuuid = run_cmd(["blkid", "-s", "PARTUUID", "-o", "value", p_root])
    if not partuuid:
        partuuid = "f337a2ab-32cc-594f-a090-3a7d85a53c48"
    print(f"[+] Root PARTUUID: {partuuid}")

    # 5. Write and compile universal boot.cmd
    print("[4/6] Generating universal U-Boot script...")
    boot_cmd_content = f"""# Armbian RK3566 Universal Boot Script (SD & eMMC)
setenv bootargs "console=ttyS2,1500000 console=tty1 earlycon=uart8250,mmio32,0xfe660000 root=PARTUUID={partuuid} rootwait rw init=/sbin/init loglevel=8 keep_bootcon no_console_suspend"

if test -z "${{kernel_addr_r}}"; then setenv kernel_addr_r 0x00280000; fi
if test -z "${{ramdisk_addr_r}}"; then setenv ramdisk_addr_r 0x0a200000; fi
if test -z "${{fdt_addr_r}}"; then setenv fdt_addr_r 0x08300000; fi
if test -z "${{devnum}}"; then setenv devnum 1; fi

load mmc ${{devnum}}:1 ${{kernel_addr_r}} Image || load mmc 1:1 ${{kernel_addr_r}} Image || load mmc 0:1 ${{kernel_addr_r}} Image
load mmc ${{devnum}}:1 ${{ramdisk_addr_r}} uInitrd || load mmc 1:1 ${{ramdisk_addr_r}} uInitrd || load mmc 0:1 ${{ramdisk_addr_r}} uInitrd
load mmc ${{devnum}}:1 ${{fdt_addr_r}} dtb/rockchip/rk3566-bobcat.dtb || load mmc 1:1 ${{fdt_addr_r}} dtb/rockchip/rk3566-bobcat.dtb || load mmc 0:1 ${{fdt_addr_r}} dtb/rockchip/rk3566-bobcat.dtb

booti ${{kernel_addr_r}} ${{ramdisk_addr_r}} ${{fdt_addr_r}}
"""
    boot_cmd_path = os.path.join(mnt_boot, "boot.cmd")
    boot_scr_path = os.path.join(mnt_boot, "boot.scr")
    with open(boot_cmd_path, "w") as f:
        f.write(boot_cmd_content)

    run_cmd(["mkimage", "-C", "none", "-A", "arm64", "-T", "script", "-d", boot_cmd_path, boot_scr_path])

    # 6. Inject Optional Configurations (Wi-Fi, SSH)
    print("[5/6] Injecting network and credentials...")
    # Prevent NetworkManager unmanaged override by removing conflicting ifupdown entries
    interfaces_path = os.path.join(mnt_root, "etc", "network", "interfaces")
    if os.path.exists(interfaces_path):
        os.remove(interfaces_path)

    if args.wifi_ssid and args.wifi_pass:
        nm_dir = os.path.join(mnt_root, "etc", "NetworkManager", "system-connections")
        os.makedirs(nm_dir, exist_ok=True)
        conn_content = f"""[connection]
id={args.wifi_ssid}
uuid=a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d
type=wifi
autoconnect=true
autoconnect-priority=100

[wifi]
mode=infrastructure
ssid={args.wifi_ssid}

[wifi-security]
key-mgmt=wpa-psk
psk={args.wifi_pass}

[ipv4]
method=auto

[ipv6]
method=auto
"""
        conn_file = os.path.join(nm_dir, f"{args.wifi_ssid}.nmconnection")
        with open(conn_file, "w") as f:
            f.write(conn_content)
        os.chmod(conn_file, 0o600)
        print(f"[+] Pre-configured Wi-Fi: {args.wifi_ssid}")

    if args.ssh_key and os.path.exists(args.ssh_key):
        ssh_dir = os.path.join(mnt_root, "root", ".ssh")
        os.makedirs(ssh_dir, exist_ok=True)
        os.chmod(ssh_dir, 0o700)
        with open(args.ssh_key, "r") as f_in:
            pub_key = f_in.read().strip()
        auth_keys = os.path.join(ssh_dir, "authorized_keys")
        with open(auth_keys, "a") as f_out:
            f_out.write(f"\n{pub_key}\n")
        os.chmod(auth_keys, 0o600)
        print(f"[+] Injected SSH public key from: {args.ssh_key}")

    # 7. Unmount cleanly
    print("[6/6] Flushing disk buffers and unmounting...")
    subprocess.run(["sync"])
    subprocess.run(["umount", mnt_boot])
    subprocess.run(["umount", mnt_root])
    subprocess.run(["sync"])
    subprocess.run(["eject", args.device])

    print("\n" + "=" * 65)
    print("🎉 SUCCESS! MicroSD card is ready.")
    print("1. Insert the card into your Bobcat Miner 300.")
    print("2. Connect Ethernet or wait for Wi-Fi auto-connection.")
    print("3. Power on with 12V DC adapter.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
