#!/bin/bash
# ==============================================================================
# Bobcat Miner 300 (RK3566) - Internal 64GB eMMC Installation Script
# ==============================================================================
# Run this script directly on the Bobcat (either inside the initramfs shell or
# over SSH while running from MicroSD) to clone Armbian to the internal eMMC.
# ==============================================================================

set -e

echo "======================================================="
echo "  Bobcat Miner 300: Internal eMMC Armbian Installer    "
echo "======================================================="

# Verify root
if [ "$(id -u)" -ne 0 ]; then
    echo "[-] This script must be run as root." >&2
    exit 1
fi

# Detect devices
# When booted from SD:
# SD is mmcblk0 (in initramfs) or mmcblk1 (in regular Linux).
# eMMC is mmcblk1 (in initramfs) or mmcblk0 (in regular Linux).
# We identify eMMC by its size (~57-64 GB) and name (SLD64G / eMMC).

SRC_DEV=""
DST_DEV=""

for dev in /dev/mmcblk0 /dev/mmcblk1; do
    if [ -b "$dev" ]; then
        NAME=$(cat /sys/block/$(basename $dev)/device/name 2>/dev/null || echo "")
        SIZE=$(cat /sys/block/$(basename $dev)/size 2>/dev/null || echo 0)
        # 60416000 sectors * 512 = ~31 GB / 58 GB
        if echo "$NAME" | grep -iqE "SLD64|eMMC"; then
            DST_DEV="$dev"
        else
            SRC_DEV="$dev"
        fi
    fi
done

if [ -z "$DST_DEV" ]; then
    echo "[-] Could not automatically identify eMMC device. Available devices:"
    lsblk
    exit 1
fi

echo "[*] Source Device (MicroSD) : $SRC_DEV"
echo "[*] Target Device (eMMC)    : $DST_DEV"
echo ""
echo "WARNING: This will permanently overwrite the internal storage on $DST_DEV!"
read -p "Proceed with cloning Armbian to internal eMMC? (y/N): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "[-] Aborted."
    exit 0
fi

# 1. Clone bootloader, partition table, bootfs, and rootfs (first 3500 MB)
echo "[1/4] Cloning operating system to internal eMMC (this takes ~1-2 minutes)..."
dd if="$SRC_DEV" of="$DST_DEV" bs=4M count=700 status=progress
sync

# 2. Re-read partition table
echo "[2/4] Updating partition tables..."
partprobe "$DST_DEV" || true
sleep 2

# 3. Mount eMMC boot partition and ensure universal bootloader is compiled
echo "[3/4] Configuring universal bootloader on eMMC..."
MNT_BOOT="/tmp/emmc_boot_mnt"
mkdir -p "$MNT_BOOT"
mount -t vfat -o iocharset=ascii "${DST_DEV}p1" "$MNT_BOOT" || mount "${DST_DEV}p1" "$MNT_BOOT"

PARTUUID=$(blkid -s PARTUUID -o value "${DST_DEV}p2")
if [ -z "$PARTUUID" ]; then
    PARTUUID="f337a2ab-32cc-594f-a090-3a7d85a53c48"
fi

cat << EOF > "$MNT_BOOT/boot.cmd"
# Armbian RK3566 Universal Boot Script (SD & eMMC)
setenv bootargs "console=tty1 console=ttyS2,1500000 console=ttyFIQ0,1500000 earlycon=uart8250,mmio32,0xfe660000 root=PARTUUID=${PARTUUID} rootwait rw init=/sbin/init loglevel=8 keep_bootcon no_console_suspend"

if test -z "\${kernel_addr_r}"; then setenv kernel_addr_r 0x00280000; fi
if test -z "\${ramdisk_addr_r}"; then setenv ramdisk_addr_r 0x0a200000; fi
if test -z "\${fdt_addr_r}"; then setenv fdt_addr_r 0x08300000; fi
if test -z "\${devnum}"; then setenv devnum 0; fi

load mmc \${devnum}:1 \${kernel_addr_r} Image || load mmc 0:1 \${kernel_addr_r} Image || load mmc 1:1 \${kernel_addr_r} Image
load mmc \${devnum}:1 \${ramdisk_addr_r} uInitrd || load mmc 0:1 \${ramdisk_addr_r} uInitrd || load mmc 1:1 \${ramdisk_addr_r} uInitrd
load mmc \${devnum}:1 \${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb || load mmc 0:1 \${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb || load mmc 1:1 \${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb

booti \${kernel_addr_r} \${ramdisk_addr_r} \${fdt_addr_r}
EOF

mkimage -C none -A arm64 -T script -d "$MNT_BOOT/boot.cmd" "$MNT_BOOT/boot.scr"
sync
umount "$MNT_BOOT"

# 4. Check filesystem
echo "[4/4] Verifying root filesystem integrity on eMMC..."
e2fsck -fy "${DST_DEV}p2" || true
sync

echo ""
echo "======================================================="
echo "🎉 INSTALLATION COMPLETE!"
echo "1. Power down the Bobcat: 'poweroff' or unplug 12V power."
echo "2. Remove the MicroSD card from the slot."
echo "3. Power back on! The Bobcat will now boot permanently from internal eMMC."
echo "======================================================="
