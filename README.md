# Repurposing the Bobcat Miner 300 (RK3566) into an Armbian Linux Server & Meshtastic / Reticulum Node

[![Platform](https://img.shields.io/badge/SoC-Rockchip%20RK3566-blue.svg)](https://www.rock-chips.com/)
[![OS](https://img.shields.io/badge/OS-Armbian%20(Debian%20Bookworm)-red.svg)](https://www.armbian.com/)
[![Mesh](https://img.shields.io/badge/Project-Meshtastic%20%7C%20Reticulum-green.svg)](https://meshtastic.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A complete, field-tested guide to liberating the **Bobcat Miner 300 (G290 / G295 revision, FCC ID: `2AZCKMINER300`)** from its locked-down factory Helium firmware and converting it into an autonomous, 24/7 **Armbian Linux server** installed permanently on its internal **64GB eMMC** storage.

Ideal for running a high-power **Meshtastic Base Station (`meshtasticd`)** using the onboard Semtech LoRa concentrator, an off-grid **Reticulum (`rns`) node**, or a general-purpose ARM64 Linux home server.

---

## Table of Contents
1. [Hardware Specifications](#hardware-specifications)
2. [Prerequisites & Tools Required](#prerequisites--tools-required)
3. [UART Pinout & Connection Guide](#uart-pinout--connection-guide)
4. [Step-by-Step Bring-Up Guide](#step-by-step-bring-up-guide)
   * [Step 1: Obtain the Base Armbian Image](#step-1-obtain-the-base-armbian-image)
   * [Step 2: Prepare & Patch the MicroSD Card](#step-2-prepare--patch-the-microsd-card)
   * [Step 3: First Boot & Interactive Shell Access](#step-3-first-boot--interactive-shell-access)
   * [Step 4: Permanent Clone to Internal 64GB eMMC](#step-4-permanent-clone-to-internal-64gb-emmc)
   * [Step 5: Standalone Autonomous Boot](#step-5-standalone-autonomous-boot)
5. [Setting Up Meshtastic & Reticulum](#setting-up-meshtastic--reticulum)
   * [Onboard LoRa Concentrator (SPI5)](#onboard-lora-concentrator-spi5)
   * [Installing Meshtastic Native Linux Daemon (`meshtasticd`)](#installing-meshtasticd)
   * [Installing Reticulum Network Stack (`rns`)](#installing-reticulum)
6. [Troubleshooting & Gotchas](#troubleshooting--gotchas)
7. [License & Acknowledgments](#license--acknowledgments)

---

## Hardware Specifications

| Component | Hardware Details | Linux Device / Interface |
| :--- | :--- | :--- |
| **SoC / CPU** | Rockchip RK3566 (Quad-Core ARM Cortex-A55 @ 1.8 GHz) | `aarch64` |
| **RAM** | 2 GB LPDDR4X (Trained by BootROM @ 1056 MHz) | Physical RAM |
| **Internal Storage** | 64 GB eMMC 5.1 Flash (High-Speed HS200 mode) | `/dev/mmcblk1` (57.6 GiB usable) |
| **Removable Storage**| External MicroSD / TF Slot | `/dev/mmcblk0` |
| **Ethernet** | Motorcomm YT8531 Gigabit RGMII PHY | `end0` (10/100/1000 Mbps) |
| **Wi-Fi / Bluetooth**| Broadcom BCM43455 / BCM4329 (SDIO / UART) | `wlan0` / `hci0` |
| **LoRa Concentrator**| Semtech SX1302 / SX1308 on internal mini-PCIe | `/dev/spidev5.0` & `/dev/spidev5.1` |
| **Front Status LEDs**| GPIO Controlled (Active-Low) | `/sys/class/leds/led-*` |
| **Serial Debug Port**| 3.3V TTL Console Test Pads | **1,500,000 baud** (8N1) |

---

## Prerequisites & Tools Required

1. **Bobcat Miner 300** (Model G290 / G295 with RK3566 board).
2. **12V DC (2A or higher) Power Adapter** (standard 5.5mm x 2.1mm barrel jack).
3. **USB-to-TTL UART Adapter (3.3V)** (e.g. DSD TECH SH-U09C2, FT232RL, or CP2102). *Ensure it supports 1,500,000 baud.*
4. **3 Wires / Paperclips / Pogo Pins** (to contact test pads without soldering).
5. **MicroSD Card** (8 GB or larger, class 10 / UHS-1 recommended).
6. **Ethernet Cable** (recommended for initial setup).

---

## UART Pinout & Connection Guide

Inside the Bobcat Miner 300 enclosure, located adjacent to the internal Micro-USB port, are circular copper test pads:

```text
       [ Internal Micro-USB Port ]
  -----------------------------------------
               ( )  ( )  ( )
               GND   TX   RX
  -----------------------------------------
```

* **GND** -> Connect to Serial Adapter **GND**
* **TX**  -> Connect to Serial Adapter **RX** (Bobcat transmits, Adapter receives)
* **RX**  -> Connect to Serial Adapter **TX** (Bobcat receives, Adapter transmits)
* **VCC / 3.3V / 5V** -> **DO NOT CONNECT!** (Board is powered by 12V DC barrel jack).

> [!IMPORTANT]
> The Rockchip RK3566 BootROM and U-Boot console run strictly at **1,500,000 baud** (not 115,200).  
> Make sure your serial client (minicom, screen, or Python) is configured for `1500000 8N1`.

---

## Step-by-Step Bring-Up Guide

### Step 1: Obtain the Base Armbian Image
Download the community Armbian image for the RK3566 Bobcat Miner (`BobcatArmbian29x.img` or equivalent Rockchip64 kernel 6.x build).

### Step 2: Prepare & Patch the MicroSD Card
Due to differences in how the Linux kernel enumerates storage devices without an initramfs, standard images often fail on first boot with:
`Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(179,2)`

We resolved this by using filesystem `PARTUUID` and compiling `boot.scr` with `uInitrd`.

Use the automated preparation script in this repository:
```bash
sudo python3 scripts/flash_and_prep_sd.py \
  --device /dev/sdX \
  --image /path/to/BobcatArmbian29x.img \
  --wifi-ssid "YOUR_WIFI_SSID" \
  --wifi-pass "YOUR_WIFI_PASSWORD" \
  --ssh-key ~/.ssh/id_ed25519.pub
```

This script automatically:
1. Writes the image to the card using `dd`.
2. Inspects partition 2 and extracts its exact GPT `PARTUUID`.
3. Injects `uInitrd` and compiles a universal `boot.scr` with `mkimage`.
4. Pre-configures NetworkManager Wi-Fi profiles and SSH keys.

---

### Step 3: First Boot & Interactive Shell Access
1. Insert the prepared MicroSD card into the Bobcat's TF slot.
2. Connect your 3.3V UART adapter (1,500,000 baud).
3. Plug in the 12V DC barrel power jack.
4. Within 15–20 seconds, the board will boot through U-Boot and launch the Linux kernel.
5. In the console, Armbian's first-run wizard will prompt:
   ```text
   Choose default system command shell:
   1) bash
   2) zsh
   ```
   Select `1` for bash. If prompted to create a user, press `Ctrl+C` to drop directly into the root prompt:
   ```bash
   root@bobcat-29x:~#
   ```

---

### Step 4: Permanent Clone to Internal 64GB eMMC

Running off a MicroSD card long-term leads to SD wear and slower I/O. The Bobcat has a high-speed **64GB eMMC 5.1** chip soldered directly on the PCB.

While logged in as root on the Bobcat:

```bash
# 1. Clone the operating system directly from SD to internal eMMC:
dd if=/dev/mmcblk0 of=/dev/mmcblk1 bs=4M count=700 status=progress
sync

# 2. Mount the eMMC boot partition:
mkdir -p /mnt/emmc_boot
mount -t vfat -o iocharset=ascii /dev/mmcblk1p1 /mnt/emmc_boot

# 3. Create the universal U-Boot script on eMMC:
cat << 'EOF' > /mnt/emmc_boot/boot.cmd
# Armbian RK3566 Universal Boot Script (eMMC & SD)
setenv bootargs "console=tty1 console=ttyS2,1500000 console=ttyFIQ0,1500000 earlycon=uart8250,mmio32,0xfe660000 root=PARTUUID=f337a2ab-32cc-594f-a090-3a7d85a53c48 rootwait rw init=/sbin/init loglevel=8 keep_bootcon no_console_suspend"

if test -z "${kernel_addr_r}"; then setenv kernel_addr_r 0x00280000; fi
if test -z "${ramdisk_addr_r}"; then setenv ramdisk_addr_r 0x0a200000; fi
if test -z "${fdt_addr_r}"; then setenv fdt_addr_r 0x08300000; fi
if test -z "${devnum}"; then setenv devnum 0; fi

load mmc ${devnum}:1 ${kernel_addr_r} Image || load mmc 0:1 ${kernel_addr_r} Image || load mmc 1:1 ${kernel_addr_r} Image
load mmc ${devnum}:1 ${ramdisk_addr_r} uInitrd || load mmc 0:1 ${ramdisk_addr_r} uInitrd || load mmc 1:1 ${ramdisk_addr_r} uInitrd
load mmc ${devnum}:1 ${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb || load mmc 0:1 ${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb || load mmc 1:1 ${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb

booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}
EOF

# 4. Compile the U-Boot boot.scr binary:
mkimage -C none -A arm64 -T script -d /mnt/emmc_boot/boot.cmd /mnt/emmc_boot/boot.scr
sync
umount /mnt/emmc_boot

# 5. Clean up and power off
poweroff
```

---

### Step 5: Standalone Autonomous Boot

1. **Unplug the 12V DC power plug.**
2. **Remove the MicroSD card** from the slot.
3. **Remove the serial paperclips / wires.**
4. Plug 12V power back in.

The Bobcat will boot directly from eMMC in **under 10 seconds**:
* The front status LED engages the Linux kernel **double-blink heartbeat** (`blink-blink... pause... blink-blink...`).
* The root partition automatically expands to **56.8 GB** (54 GB free).
* Connects automatically to your local network via Gigabit Ethernet (`end0`) and Wi-Fi (`wlan0`).

Access it via SSH:
```bash
ssh root@<BOBCAT_IP>
```

---

## Setting Up Meshtastic & Reticulum

### Onboard LoRa Concentrator (SPI5)
The Bobcat Miner 300 contains an internal mini-PCIe slot housing a **Semtech SX1302 / SX1308** multi-channel LoRa concentrator card. In Linux, the SPI bus is exposed as:
* `/dev/spidev5.0`
* `/dev/spidev5.1`

### Installing Meshtastic Native Linux Daemon (`meshtasticd`)
You can turn the Bobcat into a high-capacity Meshtastic router or base station:

1. **Add the Meshtastic repository:**
   ```bash
   sudo apt update && sudo apt install -y curl gpg
   curl -fsSL https://raw.githubusercontent.com/meshtastic/meshtastic-debian-repo/main/meshtastic.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/meshtastic.gpg
   echo "deb [signed-by=/etc/apt/trusted.gpg.d/meshtastic.gpg] https://meshtastic.github.io/meshtastic-debian-repo/ stable main" | sudo tee /etc/apt/sources.list.d/meshtastic.list
   sudo apt update
   sudo apt install -y meshtasticd
   ```

2. **Configure `/etc/meshtasticd/config.yaml`:**
   Configure the SPI interface to point to `/dev/spidev5.0`:
   ```yaml
   Lora:
     Module: sx1302
     Device: /dev/spidev5.0
     Channel: 0
   ```

3. **Start and enable the service:**
   ```bash
   sudo systemctl enable --now meshtasticd
   ```

### Installing Reticulum (`rns`)
Reticulum is a cryptography-based, off-grid mesh networking stack:

```bash
sudo apt install -y python3-pip python3-venv
pip3 install --break-system-packages rns

# Initialize Reticulum
rnsd --version
```
Edit `~/.reticulum/config` to bridge across your local Ethernet/Wi-Fi and the LoRa interface for long-distance off-grid packets.

---

## Troubleshooting & Gotchas

### 1. Serial Receiving Endless `0x00` Null Bytes
* **Cause**: In UART, 0V (LOW) represents a Start Bit. If your adapter's **RX wire** is touching Ground (0V) or bridging to the metal shield, the adapter detects a permanent break condition and fills the buffer with `0x00`.
* **Fix**: Ensure the RX probe only touches the gold `TX` test pad and does not bridge to `GND`.

### 2. Kernel Panic: `Unable to mount root fs on unknown-block(179,2)`
* **Cause**: Hardcoding `/dev/mmcblk0p2` in `bootargs`. When an SD card is inserted, device enumeration indices shift between `mmcblk0` and `mmcblk1`.
* **Fix**: Always specify `root=PARTUUID=<GUID>` in `bootargs`. The Linux kernel parses GPT partition GUIDs natively without relying on device numbers.

### 3. Wi-Fi Device Marked `unmanaged` in NetworkManager
* **Cause**: If an interface is listed in Debian's legacy `/etc/network/interfaces`, NetworkManager ignores it.
* **Fix**: Remove `/etc/network/interfaces` and restart NetworkManager:
  ```bash
  rm -f /etc/network/interfaces
  systemctl restart NetworkManager
  ```

### 4. Case-Sensitive Wi-Fi SSIDs
* In Linux / NetworkManager, SSIDs are case-sensitive. Ensure capitalization matches your router (e.g. `Freewifi` vs `freewifi`).

---

## License & Acknowledgments

* Licensed under the **MIT License**.
* Developed and tested by **Garrettopia**.
* Dedicated to the **Meshtastic** and open-source hardware communities. Reclaim your e-waste!
