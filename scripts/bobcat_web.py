#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import os
import json

PORT = 80

def get_sys_info():
    uptime = subprocess.getoutput("uptime -p").replace("up ", "")
    df = subprocess.getoutput("df -h / | awk 'NR==2 {print $4 \" free of \" $2}'")
    rnstatus = subprocess.getoutput("rnstatus 2>/dev/null | grep -E 'Peers|Transport Instance' | head -n 2")
    
    nomad_page = ""
    if os.path.exists("/root/.nomadnetwork/storage/pages/index.mu"):
        with open("/root/.nomadnetwork/storage/pages/index.mu", "r", errors="ignore") as f:
            nomad_page = f.read()
            
    return uptime, df, rnstatus, nomad_page

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Garrettopia Edge Station | Bobcat 300</title>
    <style>
        :root {{
            --bg: #0d1117;
            --card-bg: #161b22;
            --border: #30363d;
            --accent: #58a6ff;
            --green: #3fb950;
            --mesh-green: #67ea94;
            --purple: #bc8cff;
            --orange: #f0883e;
            --text: #c9d1d9;
            --text-dim: #8b949e;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px 16px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 900px;
            width: 100%;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .title {{
            font-size: 24px;
            font-weight: 700;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .badge {{
            background: rgba(63, 185, 80, 0.15);
            color: var(--green);
            border: 1px solid rgba(63, 185, 80, 0.4);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .card h3 {{
            margin: 0;
            font-size: 13px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .card .value {{
            font-size: 17px;
            font-weight: 600;
            color: #fff;
            margin-top: 4px;
        }}
        .card .sub {{
            font-size: 12px;
            color: var(--text-dim);
            margin-top: 4px;
        }}
        .section-box {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: #fff;
            margin-top: 0;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        pre {{
            background: #090d13;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            color: #7ee787;
            font-family: "SFMono-Regular", Consolas, monospace;
            font-size: 13px;
            line-height: 1.5;
            overflow-x: auto;
            white-space: pre-wrap;
            margin-bottom: 0;
        }}
        .cmd-box {{
            background: #090d13;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px 14px;
            font-family: monospace;
            font-size: 13px;
            color: #58a6ff;
            margin-bottom: 8px;
        }}
        .links {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 24px;
        }}
        .btn {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--accent);
            text-decoration: none;
            padding: 10px 18px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            transition: 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-green {{
            background: #238636;
            color: #fff;
            border-color: rgba(240, 246, 252, 0.1);
        }}
        .btn-green:hover {{
            background: #2ea043;
        }}
        .btn-purple {{
            background: #6e40c9;
            color: #fff;
            border-color: rgba(240, 246, 252, 0.1);
        }}
        .btn-purple:hover {{
            background: #8957e5;
        }}
        .btn:hover {{
            background: #21262d;
            border-color: var(--accent);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 class="title">📡 Garrettopia Edge Base Station</h1>
                <div style="color: var(--text-dim); font-size: 13px; margin-top: 4px;">Bobcat Miner 300 (RK3566) • Armbian Bookworm • Uptime: {uptime}</div>
            </div>
            <div class="badge">ONLINE (eMMC)</div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>Hardware & Storage</h3>
                <div class="value">64 GB eMMC</div>
                <div class="sub">{df}</div>
            </div>
            <div class="card">
                <h3>LoRaWAN Concentrator</h3>
                <div class="value">Semtech SX1302</div>
                <div class="sub">TTN US915 • EUI: 7681F3FFFE439472</div>
            </div>
            <div class="card">
                <h3>Meshtastic Base Station</h3>
                <div class="value">Heltec V3 (GB3)</div>
                <div class="sub">TCP Bridge :4403 • US915</div>
            </div>
            <div class="card">
                <h3>Offline Knowledge Base</h3>
                <div class="value">Kiwix Reader</div>
                <div class="sub">Port 8088 • Wikipedia Simple ZIM</div>
            </div>
        </div>

        <!-- Kiwix Offline Knowledge Section -->
        <div class="section-box">
            <h2 class="section-title">📚 Kiwix Offline Knowledge & Survival Library</h2>
            <p style="color: var(--text-dim); font-size: 13px; margin-bottom: 14px;">
                Instant, zero-internet offline access to Wikipedia, medical references, repair guides, and survival manuals served locally from the Bobcat's high-speed eMMC storage.
            </p>
            <div>
                <a class="btn btn-purple" href="http://192.168.0.40:8088" target="_blank">📖 Open Kiwix Offline Library (:8088)</a>
            </div>
        </div>

        <!-- Meshtastic Section -->
        <div class="section-box">
            <h2 class="section-title">📻 Meshtastic LoRa Base Station & Relay Bridge</h2>
            <p style="color: var(--text-dim); font-size: 13px; margin-bottom: 14px;">
                Node: <strong>Garrettopia Bobcat300 Mesh (GB3)</strong> • Connected via USB <code>/dev/ttyUSB0</code>.
                The 24/7 TCP bridge on port <strong>4403</strong> connects mobile apps (iOS/Android) and automation bots to the radio.
            </p>
            <div style="display: flex; gap: 10px; margin-bottom: 14px;">
                <a class="btn btn-green" href="https://client.meshtastic.org" target="_blank">🌐 Open Meshtastic Web App</a>
            </div>
            <div class="cmd-box"># Query local node telemetry & channels<br><span style="color:#7ee787">meshtastic --host 127.0.0.1 --info</span></div>
            <div class="cmd-box"># Configure Discord Webhook or Telegram Bot<br><span style="color:#7ee787">nano /etc/meshtastic_bridge.json && systemctl restart meshtastic-bridge</span></div>
        </div>

        <!-- TTN LoRaWAN Section -->
        <div class="section-box">
            <h2 class="section-title">🌐 The Things Network (TTN) SX1302 8-Channel Gateway</h2>
            <p style="color: var(--text-dim); font-size: 13px; margin-bottom: 14px;">
                Onboard SX1302 mini-PCIe card running Semtech Packet Forwarder over SPI5 (<code>/dev/spidev5.0</code>).
                Forwarding 8 channels simultaneously to <code>nam1.cloud.thethings.network:1700</code>.
            </p>
            <div class="cmd-box"># Gateway EUI for TTN Console registration<br><span style="color:#7ee787">7681F3FFFE439472</span></div>
            <div class="cmd-box"># Monitor real-time LoRaWAN packets<br><span style="color:#7ee787">journalctl -u ttn-packet-forwarder.service -f</span></div>
        </div>

        <!-- NomadNet Section -->
        <div class="section-box">
            <h2 class="section-title">📜 Live NomadNet Page (index.mu)</h2>
            <pre>{nomad_page}</pre>
        </div>

        <div class="links">
            <a class="btn" href="http://192.168.0.40:8088" target="_blank">📖 Kiwix Reader</a>
            <a class="btn" href="https://github.com/garrettopia/bobcat-300-armbian-guide" target="_blank">📖 GitHub Blueprints</a>
            <a class="btn" href="http://192.168.0.19:80" target="_blank">🏠 Garrettopia Control Panel</a>
        </div>
    </div>
</body>
</html>
"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            uptime, df, rnstatus, _ = get_sys_info()
            data = {
                "status": "online",
                "device": "Bobcat Miner 300",
                "uptime": uptime,
                "storage": df,
                "concentrator": "SX1302 TTN Active",
                "mesh": "Heltec V3 (GB3) Active",
                "kiwix": "Online (Port 8088)"
            }
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif self.path == "/" or self.path == "/index.html":
            uptime, df, rnstatus, nomad_page = get_sys_info()
            for code in ["`C`2", "`c", "`F400`B", "`F040`B", "`f`b"]:
                nomad_page = nomad_page.replace(code, "")
            html = HTML_TEMPLATE.format(
                uptime=uptime,
                df=df,
                rnstatus=rnstatus,
                nomad_page=nomad_page
            )
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            super().do_GET()

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
