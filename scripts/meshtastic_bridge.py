#!/usr/bin/env python3
import json
import os
import sys
import time
import requests
from pubsub import pub
import meshtastic.tcp_interface

CONFIG_FILE = "/etc/meshtastic_bridge.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "discord_webhook_url": "",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "ignore_self": True,
    "notify_on_boot": True
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Error loading config: {e}")
        return DEFAULT_CONFIG

def send_discord(webhook_url, sender_name, sender_id, text, snr=None, rssi=None):
    if not webhook_url:
        return
    payload = {
        "username": f"📻 {sender_name} ({sender_id})",
        "embeds": [
            {
                "description": text,
                "color": 3447003,
                "footer": {
                    "text": f"SNR: {snr if snr is not None else 'N/A'} dB • RSSI: {rssi if rssi is not None else 'N/A'} dBm"
                },
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        ]
    }
    try:
        r = requests.post(webhook_url, json=payload, timeout=5)
        if r.status_code not in (200, 204):
            print(f"[!] Discord error: {r.status_code} - {r.text}")
    except Exception as ex:
        print(f"[!] Failed to post to Discord: {ex}")

def send_telegram(token, chat_id, sender_name, sender_id, text, snr=None, rssi=None):
    if not token or not chat_id:
        return
    msg = f"📻 *{sender_name}* (`{sender_id}`):\n\n{text}\n\n_📶 SNR: {snr}dB | RSSI: {rssi}dBm_"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code != 200:
            print(f"[!] Telegram error: {r.status_code} - {r.text}")
    except Exception as ex:
        print(f"[!] Failed to post to Telegram: {ex}")

def on_receive(packet, interface):
    config = load_config()
    if not config.get("enabled", True):
        return

    try:
        decoded = packet.get("decoded", {})
        if decoded.get("portnum") != "TEXT_MESSAGE_APP":
            return

        text = decoded.get("text", "").strip()
        if not text:
            return

        sender_num = packet.get("from")
        sender_id = packet.get("fromId", hex(sender_num) if sender_num else "Unknown")
        my_node_num = interface.myInfo.my_node_num if interface.myInfo else None

        if config.get("ignore_self", True) and sender_num == my_node_num:
            return

        sender_name = sender_id
        if interface.nodes:
            for node_id, node_data in interface.nodes.items():
                if node_data.get("num") == sender_num:
                    sender_name = node_data.get("user", {}).get("longName", sender_id)
                    break

        snr = packet.get("rxSnr")
        rssi = packet.get("rxRssi")

        print(f"[+] Relaying message from {sender_name} ({sender_id}): {text}")

        discord_url = config.get("discord_webhook_url")
        if discord_url:
            send_discord(discord_url, sender_name, sender_id, text, snr, rssi)

        tg_token = config.get("telegram_bot_token")
        tg_chat = config.get("telegram_chat_id")
        if tg_token and tg_chat:
            send_telegram(tg_token, tg_chat, sender_name, sender_id, text, snr, rssi)

    except Exception as e:
        print(f"[!] Error processing packet: {e}")

def main():
    print("[*] Starting Meshtastic Relay Bridge...")
    config = load_config()

    while True:
        try:
            print("[*] Connecting to Meshtastic TCP interface at 127.0.0.1:4403...")
            pub.subscribe(on_receive, "meshtastic.receive.text")
            iface = meshtastic.tcp_interface.TCPInterface(hostname="127.0.0.1", portNumber=4403)
            print("[✓] Connected to radio node!")
            
            while True:
                time.sleep(10)
        except Exception as ex:
            print(f"[!] Connection failed/dropped: {ex}. Reconnecting in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()
