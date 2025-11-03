EvilPortalLab - Wi-Fi Captive Portal Tool

Disclaimer: This tool is intended for authorized security testing and educational purposes ONLY. Using this tool on networks without explicit permission is illegal and unethical. The developer assumes no liability for misuse.

EvilPortalLab is a Python-based tool for creating a "Fake" Wi-Fi Access Point (AP) and launching a captive portal. It is designed for penetration testing and red-teaming exercises to simulate Wi-Fi-based social engineering attacks.

When a target connects to the AP, this tool uses dnsmasq and iptables to redirect all web traffic (HTTP) to a local web server (the captive portal), which can be used to serve custom landing pages.

Features

Fake AP Creation: Broadcasts a custom SSID using hostapd.

WPA2 Support: Can create an open network or a WPA2-protected network.

Captive Portal: Redirects all HTTP traffic to a local portal.

DNS Catch-All: Intercepts and responds to all DNS queries, forcing clients to the portal.

Network Isolation: Uses iptables to prevent clients on the fake AP from accessing the upstream network or other clients.

Easy Configuration: Manages settings via a config.json file.

Interface Detection: Automatically scans for and helps configure wireless interfaces.

Dependencies

This tool is designed for Linux and relies on several external system utilities:

python3

hostapd

dnsmasq

iptables

nmcli (NetworkManager command-line)

iw

iproute2 (for ip command)

You can typically install these on a Debian-based system (like Kali or Ubuntu) with:

sudo apt update
sudo apt install hostapd dnsmasq python3-pip


(The other tools are usually pre-installed on modern distributions).

Configuration

The tool is configured via a central config.json file. The server will generate one on first run if it's missing.

{
  "wifi_interface": "wlxc01c30431f9b",
  "ssid": "Free_Airport_WiFi",
  "channel": 6,
  "wpa2": false,
  "wpa_passphrase": "password123",
  "portal_ip": "10.0.0.1",
  "portal_port": 8080,
  "dns_catch_all": true,
  "upstream_interface": "eth0"
}


wifi_interface: The wireless adapter to use (e.g., wlan0).

ssid: The name of the Wi-Fi network to broadcast.

channel: The Wi-Fi channel (1-11).

wpa2: true or false. Set to true to enable WPA2 encryption.

wpa_passphrase: The password if wpa2 is enabled (must be 8+ chars).

portal_ip: The gateway IP for the fake network (this machine's IP).

portal_port: The port where your captive portal web server is running.

dns_catch_all: true to redirect all DNS.

upstream_interface: The interface with internet access (e.g., eth0) for NAT.

Usage

1. Clone the Repository:

git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name


2. Select Interface (First-Time Setup):
If your config.json is empty, run the tool to select an adapter.

# Assuming your main script is main.py
sudo python3 main.py --select-interface


This will detect wireless adapters and save your choice to config.json.

3. Start the Access Point:
This must be run as root to manage network interfaces and iptables.

# Make sure your captive portal web server is running on port 8080
sudo python3 main.py --start-ap


This will:

Generate hostapd.conf and dnsmasq.conf.

Configure iptables rules.

Start the hostapd and dnsmasq services.

4. Stop the Access Point:

sudo python3 main.py --stop-ap


This will kill the AP processes and clean up all iptables rules.