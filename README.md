# Repurposing the Bobcat Miner 300 (RK3566) into an Armbian Linux Server & Meshtastic / Reticulum Node

[![Platform](https://img.shields.io/badge/SoC-Rockchip%20RK3566-blue.svg)](https://www.rock-chips.com/)
[![OS](https://img.shields.io/badge/OS-Armbian%20(Debian%20Bookworm)-red.svg)](https://www.armbian.com/)
[![Mesh](https://img.shields.io/badge/Project-Meshtastic%20%7C%20Reticulum-green.svg)](https://meshtastic.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A complete, field-tested guide to liberating the **Bobcat Miner 300 (G290 / G295 revision, FCC ID: `2AZCKMINER300`)** from its locked-down factory Helium firmware and converting it into an autonomous, 24/7 **Armbian Linux server** installed permanently on its internal **64GB eMMC** storage.

Ideal for running a high-power **Meshtastic Base Station** (via attached USB LoRa transceiver), an 8-channel **LoRaWAN / The Things Network gateway** using the onboard Semtech SX1302 concentrator, an off-grid **Reticulum (`rns`) node**, or a general-purpose ARM64 Linux home server.

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
5. [Setting Up the Onboard Semtech SX1302 LoRa Concentrator](#setting-up-the-onboard-semtech-sx1302-lora-concentrator)
   * [Power & Reset GPIO Details](#-critical-hardware-detail-power--reset-gpios)
   * [Hardware Initialization Script](#step-1-install-the-hardware-initialization-script)
   * [Enable 24/7 Hardware Power on Boot](#step-2-enable-247-hardware-power-on-boot)
   * [Verify Hardware Health & Register Communication](#step-3-verify-hardware-health--register-communication)
6. [Wireless Architecture: LoRaWAN, Meshtastic & Reticulum](#wireless-architecture-lorawan-meshtastic--reticulum)
   * [1. Onboard Semtech SX1302: Commercial LoRaWAN Gateway](#1-onboard-semtech-sx1302-commercial-lorawan-gateway)
   * [2. Meshtastic Architecture: USB Microcontroller Node vs. Native SX1262 Integration](#2-meshtastic-architecture-usb-microcontroller-node-vs-native-sx1262-integration)
   * [3. Reticulum & NomadNet: Native 24/7 Off-Grid Mesh](#3-reticulum--nomadnet-native-247-off-grid-mesh)
7. [Troubleshooting & Gotchas](#troubleshooting--gotchas)
8. [License & Acknowledgments](#license--acknowledgments)


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

While logged in as root on the Bobcat (either booted from MicroSD or via serial shell):

```bash
# 1. Clone the operating system directly from SD to internal eMMC:
dd if=/dev/mmcblk0 of=/dev/mmcblk1 bs=4M count=700 status=progress
sync

# 2. Re-read partition table and mount the eMMC boot partition:
partprobe /dev/mmcblk1
mkdir -p /mnt/emmc_boot
mount -t vfat -o iocharset=ascii /dev/mmcblk1p1 /mnt/emmc_boot

# 3. Extract the exact eMMC Root PARTUUID:
EMMC_PARTUUID=$(blkid -s PARTUUID -o value /dev/mmcblk1p2)
echo "eMMC Root PARTUUID: ${EMMC_PARTUUID}"

# 4. Generate the universal U-Boot boot script for eMMC:
cat << EOF > /mnt/emmc_boot/boot.cmd
# Armbian RK3566 Universal Boot Script (eMMC & SD)
setenv bootargs "console=ttyS2,1500000 console=tty1 earlycon=uart8250,mmio32,0xfe660000 root=PARTUUID=${EMMC_PARTUUID} rootwait rw init=/sbin/init loglevel=8 keep_bootcon no_console_suspend"

if test -z "\${kernel_addr_r}"; then setenv kernel_addr_r 0x00280000; fi
if test -z "\${ramdisk_addr_r}"; then setenv ramdisk_addr_r 0x0a200000; fi
if test -z "\${fdt_addr_r}"; then setenv fdt_addr_r 0x08300000; fi
if test -z "\${devnum}"; then setenv devnum 0; fi

load mmc \${devnum}:1 \${kernel_addr_r} Image || load mmc 0:1 \${kernel_addr_r} Image || load mmc 1:1 \${kernel_addr_r} Image
load mmc \${devnum}:1 \${ramdisk_addr_r} uInitrd || load mmc 0:1 \${ramdisk_addr_r} uInitrd || load mmc 1:1 \${ramdisk_addr_r} uInitrd
load mmc \${devnum}:1 \${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb || load mmc 0:1 \${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb || load mmc 1:1 \${fdt_addr_r} dtb/rockchip/rk3566-bobcat.dtb

booti \${kernel_addr_r} \${ramdisk_addr_r} \${fdt_addr_r}
EOF

# 5. Compile the U-Boot boot.scr binary:
mkimage -C none -A arm64 -T script -d /mnt/emmc_boot/boot.cmd /mnt/emmc_boot/boot.scr
sync
umount /mnt/emmc_boot

# 6. Clean up and power off
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

## Setting Up the Onboard Semtech SX1302 LoRa Concentrator

The Bobcat Miner 300 contains an internal mini-PCIe slot housing a high-performance **Semtech SX1302 multi-channel LoRa Concentrator card**. 

### ⚡ Critical Hardware Detail: Power & Reset GPIOs
By default, the standard Linux kernel does **not** energize the mini-PCIe slot, leaving the LoRa card unpowered and unresponsive. To wake the SX1302 chip and communicate over SPI, you must control three specific Rockchip RK3566 GPIOs:

| Signal | SoC GPIO Number | Pin Name | Description |
| :--- | :--- | :--- | :--- |
| **LoRa Power Enable** | **`125`** | `GPIO3_D5` | Controls 3.3V power rails to the mini-PCIe slot (`1 = ON`) |
| **LoRa Extra Power**  | **`122`** | `GPIO3_D2` | Secondary power gating for RF front-end (`1 = ON`) |
| **SX1302 Reset**      | **`149`** | `GPIO4_B5` | Hardware reset line (Active High pulse, then Low for normal operation) |
| **LoRa SPI Interface**| — | **`/dev/spidev5.0`** | Primary SPI bus interface for SX1302 register communication |

### Step 1: Install the Hardware Initialization Script
Use the included [`scripts/reset_lgw.sh`](scripts/reset_lgw.sh) script:
```bash
sudo cp scripts/reset_lgw.sh /usr/local/bin/reset_lgw.sh
sudo chmod +x /usr/local/bin/reset_lgw.sh

# Power on and reset the LoRa module:
sudo /usr/local/bin/reset_lgw.sh start
```

### Step 2: Enable 24/7 Hardware Power on Boot
Install the systemd unit so the LoRa card is automatically energized whenever the Bobcat boots:
```bash
sudo cp scripts/lora-hardware-init.service /etc/systemd/system/lora-hardware-init.service
sudo systemctl daemon-reload
sudo systemctl enable --now lora-hardware-init.service
```

### Step 3: Verify Hardware Health & Register Communication
You can verify two-way communication with the SX1302 silicon using Semtech's native diagnostic suite:
```bash
git clone https://github.com/Lora-net/sx1302_hal.git /tmp/sx1302_hal
cd /tmp/sx1302_hal && make

# Run register diagnostics across SPI5:
cp /usr/local/bin/reset_lgw.sh libloragw/reset_lgw.sh
cd libloragw
./test_loragw_reg -d /dev/spidev5.0
```
Expected output confirming 100% healthy silicon:
```text
Opening SPI communication interface: /dev/spidev5.0
Note: chip version is 0x10 (v1.0)
## TEST#1: read all registers and check default value -> TEST#1 PASSED
## TEST#2: read/write test on all non-read-only registers -> TEST#2 PASSED
Closing SPI communication interface
```

---

## Wireless Architecture: LoRaWAN, Meshtastic & Reticulum

Understanding the radio capabilities of the repurposed Bobcat 300 will help you choose the best mesh setup for your needs:

### 1. Onboard Semtech SX1302: Commercial LoRaWAN Gateway (The Things Network)
The card in the mini-PCIe slot is an **8-channel commercial LoRaWAN concentrator** capable of receiving packets simultaneously on 8 distinct frequencies.

1. **Build the SX1302 HAL & Packet Forwarder**:
   ```bash
   git clone https://github.com/Lora-net/sx1302_hal.git /opt/sx1302_hal
   cd /opt/sx1302_hal
   # Patch loragw_hal.c to treat missing I2C STTS751 temperature sensor non-fatally
   make
   ```
2. **Configure US915 Frequency Plan & Gateway EUI**:
   Derive your unique 64-bit Gateway EUI from your ethernet MAC address (e.g. `00:11:22:33:44:55` -> `001122FFFE334455`) and set `server_address` to `nam1.cloud.thethings.network` on port `1700`.
3. **Automate via Systemd**:
   ```bash
   sudo cp scripts/ttn-packet-forwarder.service /etc/systemd/system/
   sudo systemctl enable --now ttn-packet-forwarder.service
   ```

### 2. Meshtastic Architecture: USB Microcontroller Node vs. Native SX1262 Integration

Meshtastic's peer-to-peer (P2P) protocol is engineered specifically for **single-channel transceivers** (like the **Semtech SX1262** or **SX1276**) rather than multi-channel concentrators. 

When repurposing the Bobcat Miner 300 for Meshtastic, there are two distinct architectural approaches:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ OPTION A: External USB Microcontroller Node (Heltec V3 / LilyGO T-Beam)           │
├──────────────────────────────────────────────────────────────────────────────────┤
│  [Heltec V3 (ESP32-S3)]  <──(Main Controller)──>  Runs Meshtastic C++ Firmware   │
│         │ (USB Serial)                                                           │
│  [Bobcat Miner (RK3566)] <──(Host Infrastructure)─> Runs ser2net (:4403) & Bots │
└──────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│ OPTION B: Native SX1262 LoRa Module via SPI / GPIO (Phase 2 - In Development)    │
├──────────────────────────────────────────────────────────────────────────────────┤
│  [Bobcat Miner (RK3566)] <──(Main Controller)──>  Runs native Linux meshtasticd  │
│         │ (Direct SPI/GPIO)                                                      │
│  [Waveshare SX1262 Chip] <──(Raw Radio Front-End)─> Direct RF Transmission       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

#### Approach A: External Microcontroller Node via USB (Available Today)
* **Controller**: The external microcontroller (**ESP32-S3** or **nRF52840** on the Heltec/T-Beam) acts as the **primary controller/brain** of the Meshtastic system, executing the core radio firmware and mesh routing logic.
* **Bobcat Role**: The Bobcat functions as high-capacity host infrastructure:
  1. Supplies continuous 12V-regulated power over USB.
  2. Bridges the radio's serial stream to TCP via `ser2net` on port **`4403`**, allowing any smartphone or PC on local Wi-Fi to configure the mesh via **[client.meshtastic.org](https://client.meshtastic.org)**.
  3. Executes automation relays ([`scripts/meshtastic_bridge.py`](scripts/meshtastic_bridge.py)) to mirror mesh traffic into private Discord/Telegram channels.
  ```bash
  sudo cp scripts/meshtastic-bridge.service /etc/systemd/system/
  sudo systemctl enable --now meshtastic-bridge.service
  ```

#### Approach B: Native SX1262 LoRa Integration via SPI/GPIO (Phase 2 Roadmap)
* **Controller**: The Bobcat Miner 300's **Rockchip RK3566 Quad-Core SoC** becomes the **native primary controller**, running the official Linux **`meshtasticd`** daemon directly inside Armbian.
* **Hardware Interface**: A raw **Semtech SX1262 transceiver** (such as a Waveshare SX1262 module or mini-PCIe form-factor card) interfaces directly with the RK3566 via SPI (`/dev/spidev5.0` / SPI0) and dedicated GPIO lines (Reset, Busy, DIO1 interrupt).
* **Key Advantages**:
  * **All-in-One Form Factor**: No external USB dongles, breakout boards, or loose cables outside the enclosure.
  * **Massive Compute Headroom**: Eliminates microcontroller RAM/flash constraints, enabling extensive message packet caching, fast encryption, and integrated edge routing.

### 3. Reticulum & NomadNet: Native 24/7 Off-Grid Mesh
Unlike Meshtastic, the **Reticulum Network Stack (`rnsd`)** and **NomadNet (`nomadnet`)** run 100% natively on the Bobcat out of the box without any extra dongles:
* **AutoInterface**: Automatically peers with any phone, PC, or device running Reticulum across your local Wi-Fi and Ethernet.
* **Encrypted Mesh Router**: Acts as an off-grid packet transport hub on TCP port **`4242`**.
* **Nomad Pages**: Serves your personal decentralized **`index.mu`** Micron pages and routes LXMF messages 24/7.

---

## High-Utility Edge Services

### 📚 Kiwix Offline Knowledge & Survival Library
Turn the Bobcat's high-speed 64GB eMMC into a zero-internet survival and knowledge repository:
* **Standalone Binary**: `kiwix-serve` running on port **`8088`**.
* **Offline ZIM Archives**: Houses offline copies of Wikipedia Simple, WikiHow, Medical references, and disaster manuals.
* **Access Anywhere**: Any phone, tablet, or PC on local Wi-Fi can browse Wikipedia with zero cellular or internet connection.
```bash
sudo cp scripts/kiwix.service /etc/systemd/system/
sudo systemctl enable --now kiwix.service
```

### 📡 Unified Base Station Web Dashboard
A lightweight, zero-dependency Python dashboard served on port **`80`** displaying live system metrics, LoRaWAN status, Meshtastic node info, and NomadNet pages:
* **Web UI**: `http://<BOBCAT_IP>/`
* **JSON API Endpoint**: `http://<BOBCAT_IP>/api/status` (compatible with [Homepage](https://gethomepage.dev) widgets)
```bash
sudo cp scripts/bobcat_web.py /usr/local/bin/
sudo cp scripts/bobcat-web.service /etc/systemd/system/
sudo systemctl enable --now bobcat-web.service
```

---

## 📋 Project Roadmap & Future Deployments

- [x] **Armbian eMMC Port:** Permanent autonomous boot on RK3566 with 64GB eMMC storage.
- [x] **SX1302 Concentrator Activation:** 8-channel LoRaWAN Packet Forwarder to The Things Network (TTN).
- [x] **Meshtastic Base Station:** 24/7 TCP Serial Bridge (`:4403`) for Heltec V3.
- [x] **Reticulum & NomadNet Hub:** Autonomous encrypted transport node (`:4242`) & Micron pages.
- [x] **Kiwix Offline Knowledge Library:** High-speed offline Wikipedia & survival archive (`:8088`).
- [x] **Meshtastic $\leftrightarrow$ Discord/Telegram Relay Bridge:** Bi-directional bot relay.
- [x] **Unified Control Panel & Homepage Integration:** Live dashboard on port `80` with `/api/status`.
- [x] **Failover DNS & Ad-Blocking:** Deploy Pi-hole v6 + Unbound with DNSSEC root recursive resolution and failover DNS on port `53` (`:8080`).
- [ ] **TTN $\rightarrow$ Local Command Center Bridge:** Connect TTN MQTT to Home Assistant / local command center for ultra long-range LoRa sensor automations and real-time telemetry.
- [ ] **ChirpStack Local Server:** Standalone private LoRaWAN Network Server for 100% cloudless local sensor deployments.


---

## Troubleshooting & Gotchas

### 1. Serial Receiving Endless `0x00` Null Bytes
* **Cause**: In UART, 0V (LOW) represents a Start Bit. If your adapter's **RX wire** is touching Ground (0V) or bridging to the metal shield, the adapter detects a permanent break condition and fills the buffer with `0x00`.
* **Fix**: Ensure the RX probe only touches the gold `TX` test pad and does not bridge to `GND`.

### 2. Kernel Panic: `Unable to mount root fs on unknown-block(179,2)` / Stale PARTUUID
* **Cause**: Hardcoding `/dev/mmcblk0p2` or a stale MicroSD card `PARTUUID` in `bootargs`. When an SD card is removed or system reboots from eMMC, device indices change (`/dev/mmcblk1`).
* **Fix**: Always query the target partition's true GUID (`blkid -s PARTUUID -o value /dev/mmcblk1p2`) or specify `root=/dev/mmcblk1p2 rootwait` in `boot.cmd` and recompile `boot.scr`.

### 3. The "Burnt Out" Ethernet Port Red Herring (Post-Outage Failure)
* **Symptom**: After a sudden power cut or surge, the Bobcat does not negotiate Ethernet link, the RJ45 link lights stay completely off, and the device is unreachable via IP.
* **Root Cause**: On the Rockchip RK3566, the onboard `Motorcomm YT8512B` Ethernet PHY is **driver-initialized**. If a corrupted bootloader configuration (such as a mismatched PARTUUID) causes the Linux kernel to panic during early boot, the kernel never gets to the network driver initialization step. The hardware is **100% undamaged**—it is simply stuck in an early bootloader panic loop.
* **Fix**: Attach a 3.3V UART serial adapter @ 1,500,000 baud to the TX/RX test pads to verify boot output, boot the kernel, and repair `/boot/boot.scr`.

### 4. Internal Micro-USB Port: Device/Client Mode (No Host 5V Power)
* **Symptom**: Plugging a USB-to-Ethernet adapter or USB drive into the internal Micro-USB port does not illuminate or detect devices (`lsusb` shows empty).
* **Cause**: The internal Micro-USB port on the Bobcat is hardware-strapped as an **OTG Client/Device port** for Rockchip Maskrom firmware flashing. It does not provide 5V VBUS power to host external USB accessories unless externally powered via an OTG Y-cable.
* **Fix**: Use the native onboard RJ45 Ethernet port (`end0`), which is fully supported at 100/1000 Mbps.

### 5. Silent Serial Console (`ttyFIQ0` vs `ttyS2`)
* **Cause**: Rockchip vendor trees sometimes set `console=ttyFIQ0,1500000`, which diverts `/dev/console` stdin to the kernel FIQ debugger.
* **Fix**: Always set `console=ttyS2,1500000 console=tty1` in `boot.cmd` so standard terminal input/output works reliably over the hardware test pads.

### 6. Debricking & eMMC Recovery without MicroSD via Hardware UART
If your Bobcat is bricked or caught in a boot loop and you have no spare MicroSD card:
1. Solder Dupont wires to the 3 test pads next to the Micro-USB port (`GND`, `TX` &rarr; Adapter RX, `RX` &rarr; Adapter TX).
2. Connect to the serial console at `1500000 8N1` (e.g. using a Raspberry Pi Zero or FTDI adapter).
3. Power cycle the Bobcat and send `Ctrl+C` repeatedly within 2 seconds to catch the U-Boot prompt (`=>`).
4. Manually load the kernel, initrd, and device tree from eMMC into RAM:
   ```text
   => setenv bootargs "console=ttyS2,1500000 console=tty1 root=/dev/mmcblk1p2 rootwait rw init=/sbin/init"
   => load mmc 0:1 0x00280000 Image
   => load mmc 0:1 0x0a200000 uInitrd
   => load mmc 0:1 0x08300000 dtb/rockchip/rk3566-bobcat.dtb
   => booti 0x00280000 0x0a200000 0x08300000
   ```
5. Once in the Linux root shell, update `/boot/boot.cmd` and recompile `/boot/boot.scr` with `mkimage`.

---

## License & Acknowledgments

* Licensed under the **MIT License**.
* Developed and tested by **Garrettopia** on the **Bobcat Miner 300 (RK3566 / G290 / G295)**.
* Dedicated to the **Meshtastic**, **LoRaWAN**, and open-source hardware communities. Reclaim your e-waste!

