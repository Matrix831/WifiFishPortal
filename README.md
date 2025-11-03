EvilPortalLab

A Python toolkit for launching Wi-Fi Captive Portal attacks.

   ⚠️ ETHICAL USE ONLY ⚠️
This tool is intended for authorized security testing and educational purposes. Using this tool on networks without explicit permission is illegal and unethical. The developer assumes no liability for misuse.

WifiFishPortal is a powerful toolkit for penetration testers and red teams to simulate Wi-Fi social engineering attacks. It automates the creation of a "Fake" Access Point (AP) and a captive portal.

When a target connects, the tool hijacks their web traffic using dnsmasq and iptables, redirecting all HTTP requests to your custom-built landing page.

✨ Features

- Fake AP Creation: Broadcasts any custom SSID (e.g., "Free_Airport_WiFi") using hostapd.
- WPA2 Support: Creates either an Open network or a secure WPA2-protected one.
- Full Captive Portal: Intelligently redirects all HTTP traffic to your local portal.
- DNS Catch-All: Intercepts and responds to all DNS queries, forcing clients to your page even if they type a domain name.
- Client Isolation: iptables rules prevent clients from accessing the real network or other devices on the AP.
- Easy Configuration: Manage all settings from a simple config.json file.
- Auto-Interface Scan: Detects and helps you select the right wireless adapter.

🛠️ Dependencies

This tool is built for Linux and requires several key utilities:
  python3
  hostapd
  dnsmasq
  iptables
  nmcli (NetworkManager command-line)
  iw
  iproute2 (for the ip command)

🚀 Installation

On a Debian-based system (like Kali, Ubuntu, or Raspberry Pi OS), you can install the main dependencies with:

    sudo apt update
    sudo apt install hostapd dnsmasq python3-pip

(The other tools are typically pre-installed on modern distributions.)

⚙️ Configuration

All settings are managed via the config.json file. The server will create a default one on its first run.
  wifi_interface: The wireless adapter to use (e.g., wlan0).
  ssid: The name of the Wi-Fi network to broadcast.
  channel: The Wi-Fi channel (1-11).
  wpa2: true or false. Set to true to enable WPA2 encryption.
  wpa_passphrase: The password if wpa2 is enabled (must be 8+ chars).
  portal_ip: The gateway IP for the fake network (this machine's IP).
  portal_port: The port where your captive portal web server is running.
  dns_catch_all: true to redirect all DNS.
  upstream_interface: The interface with internet access (e.g., eth0) for NAT.

⚡ How to Use

1. Clone the Repository:
  git clone [https://github.com/Matrix831/WifiFishPortal.git]
  cd WifiFishPortal

2. Select Interface (First-Time Setup):
If your config.json is empty, run the tool to select an adapter.

  sudo python3 main.py --select-interface

This will detect wireless adapters and save your choice.

3. Start the Access Point:
This must be run as root. Make sure your own captive portal web server is running on the configured port!

  sudo python3 main.py --start-ap

This will:

Generate hostapd.conf and dnsmasq.conf
Configure all the iptables rules
Start the hostapd and dnsmasq services

4. Stop the Access Point:

  sudo python3 main.py --stop-ap

This kills all processes and cleans up the iptables rules.

You can also do this steps at the admin panel UI, just open http://[YOU_IP]/admin
You can also access the admin panel by using the USERNAME:matrix and PASSWORD:matrix(you can modify the password at portal.py), at the main interface.

This tool is not yet in its final stage, so bugs and errors might occur.

  !!NOTE!!
  MAKE YOUR WIFI MODULE OR WIFI ADAPTER SUPPORTS MONITOR MODE AND PACKET INJECTION