#!/usr/bin/env python3
"""
Bobcat Miner 300 - U-Boot Console Interrupter & Boot Automation
===============================================================
Connects to the 3.3V TTL UART console at 1,500,000 baud, interrupts
autoboot by sending Ctrl+C, and allows sending custom boot commands.

Usage:
  python3 catch_uboot.py [--port /dev/ttyUSB0] [--baud 1500000]
"""

import argparse
import serial
import sys
import time

def main():
    parser = argparse.ArgumentParser(description="Catch U-Boot prompt on Bobcat Miner 300")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial device port (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=1500000, help="Baud rate (default: 1500000)")
    args = parser.parse_args()

    print(f"[*] Opening {args.port} at {args.baud} baud...", flush=True)
    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.05)
    except Exception as e:
        print(f"[-] Error opening serial port: {e}", file=sys.stderr)
        sys.exit(1)

    with ser:
        ser.reset_input_buffer()
        print("=" * 65)
        print("   BOBCAT U-BOOT CATCHER")
        print("   1. Connect UART adapter (GND, TX, RX) to test pads.")
        print("   2. Unplug 12V power for 2 seconds, then plug it back in!")
        print("=" * 65, flush=True)

        buf = ""
        start = time.time()
        while time.time() - start < 45:
            ser.write(b'\x03\r\n')
            time.sleep(0.04)
            if ser.in_waiting:
                chunk = ser.read(ser.in_waiting)
                text = chunk.decode('latin1', errors='replace')
                sys.stdout.write(text)
                sys.stdout.flush()
                buf += text
                if "=>" in buf:
                    print("\n\n[🎉 SUCCESS!] Caught U-Boot prompt ('=>')!")
                    print("[*] Entering interactive console (type commands or 'boot'). Ctrl+C to exit.\n")
                    while True:
                        try:
                            cmd = input("uboot> ")
                            ser.write((cmd + "\r\n").encode())
                            time.sleep(0.3)
                            while ser.in_waiting:
                                sys.stdout.write(ser.read(ser.in_waiting).decode('latin1', errors='replace'))
                                sys.stdout.flush()
                        except KeyboardInterrupt:
                            print("\nExiting.")
                            break
                    return

        print("\n[-] Timeout reached waiting for U-Boot prompt.")

if __name__ == "__main__":
    main()
