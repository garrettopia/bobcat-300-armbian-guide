#!/bin/sh
# ==============================================================================
# Bobcat Miner 300 (RK3566, G290 / G295) - Semtech SX1302 LoRa Power & Reset
# ==============================================================================
# Hardware GPIO Mapping:
#   - RESET_GPIO = 149 (GPIO4_B5)
#   - POWER_GPIO = 125 (GPIO3_D5)
#   - EXTRA_GPIO = 122 (GPIO3_D2)
#   - SPI Device = /dev/spidev5.0
# ==============================================================================

case "$1" in
    start)
        # Export GPIOs if not already exposed
        for pin in 125 122 149; do
            if [ ! -d /sys/class/gpio/gpio$pin ]; then
                echo $pin > /sys/class/gpio/export 2>/dev/null || true
            fi
            echo out > /sys/class/gpio/gpio$pin/direction 2>/dev/null || true
        done

        # 1. Enable power rails to the mini-PCIe LoRa slot
        echo 1 > /sys/class/gpio/gpio125/value
        echo 1 > /sys/class/gpio/gpio122/value

        # 2. Pulse SX1302 reset line (Active High pulse, then Low for normal operation)
        echo 1 > /sys/class/gpio/gpio149/value
        sleep 0.1
        echo 0 > /sys/class/gpio/gpio149/value
        sleep 0.2

        echo "[+] Semtech SX1302 LoRa concentrator powered and ready on /dev/spidev5.0"
        ;;
    stop)
        # Power down mini-PCIe slot
        echo 0 > /sys/class/gpio/gpio125/value 2>/dev/null || true
        echo 0 > /sys/class/gpio/gpio122/value 2>/dev/null || true
        echo "[-] SX1302 LoRa hardware powered down."
        ;;
    *)
        echo "Usage: $0 {start|stop}"
        exit 1
        ;;
esac

exit 0
