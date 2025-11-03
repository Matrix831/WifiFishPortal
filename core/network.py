#!/usr/bin/env python3
# wifitool/core/network.py
"""
Network helpers for EvilPortal:
- runtime hostapd/dnsmasq generation
- start/stop AP (real execution)
- captive-portal support via dnsmasq catch-all and iptables DNAT
"""

from pathlib import Path
import subprocess
from typing import List, Optional

from core.utils import load_config, save_config, log_event, ensure_dirs  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RUNTIME_DIR = DATA_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

HOSTAPD_PATH = RUNTIME_DIR / "hostapd.conf"
DNSMASQ_PATH = RUNTIME_DIR / "dnsmasq.conf"


def _run_cmd(cmd: List[str], capture: bool = True) -> Optional[str]:
    """Run a command (list form) and return stdout (or None on failure)."""
    try:
        res = subprocess.run(cmd, capture_output=capture, text=True, check=True)
        return res.stdout.strip() if capture else ""
    except Exception:
        return None


def list_wireless_interfaces() -> List[str]:
    """Attempt to list wireless interfaces using `iw` then fall back to `ip link`."""
    out = _run_cmd(["iw", "dev"])
    if out:
        names = []
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Interface"):
                parts = line.split()
                if len(parts) >= 2:
                    names.append(parts[1])
        if names:
            return names

    # Fallback to ip link
    out2 = _run_cmd(["ip", "-o", "link", "show"])
    if not out2:
        return []
    names = []
    for line in out2.splitlines():
        try:
            name = line.split(":")[1].strip().split("@")[0]
            if name != "lo":
                names.append(name)
        except Exception:
            continue
    return names


def iw_supports_ap() -> bool:
    """Check if device supports AP mode via `iw list`."""
    out = _run_cmd(["iw", "list"])
    if not out:
        return False
    return "Supported interface modes" in out and " AP" in out


def choose_adapter_interactive() -> Optional[str]:
    """Prompt user to choose interface and save to config.json."""
    ensure_dirs()
    ifaces = list_wireless_interfaces()
    if not ifaces:
        print("No network interfaces detected. Plug in an adapter and retry.")
        return None
    print("Detected interfaces:")
    for i, ifc in enumerate(ifaces, start=1):
        print(f"  [{i}] {ifc}")
    choice = input("Choose an interface number (q to cancel): ").strip()
    if choice.lower() == "q":
        return None
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(ifaces):
            print("Invalid selection.")
            return None
        selected = ifaces[idx]
        cfg = load_config()
        cfg["wifi_interface"] = selected
        save_config(cfg)
        log_event(f"[network] Selected interface: {selected}")
        print(f"Saved interface '{selected}' to config.json")
        return selected
    except ValueError:
        print("Invalid input.")
        return None


def generate_hostapd_conf(interface: str, ssid: str, channel: int = 6,
                          wpa2: bool = False, passphrase: str = "") -> Path:
    """Generate hostapd.conf template."""
    lines = [
        f"interface={interface}",
        "driver=nl80211",
        f"ssid={ssid}",
        "hw_mode=g",
        f"channel={channel}",
        "ieee80211n=1",
        "wmm_enabled=1",
        "auth_algs=1",
        "ignore_broadcast_ssid=0",
    ]
    if wpa2:
        if not passphrase or len(passphrase) < 8:
            raise ValueError("WPA2 passphrase must be at least 8 characters")
        lines += [
            "wpa=2",
            f"wpa_passphrase={passphrase}",
            "wpa_key_mgmt=WPA-PSK",
            "rsn_pairwise=CCMP",
        ]
    else:
        lines.append("wpa=0")

    HOSTAPD_PATH.write_text("\n".join(lines), encoding="utf-8")
    log_event(f"[network] Generated hostapd.conf at {HOSTAPD_PATH}")
    return HOSTAPD_PATH


def generate_dnsmasq_conf(iface: str, gateway_ip: str = "10.0.0.1",
                          dhcp_start: str = "10.0.0.10", dhcp_end: str = "10.0.0.200",
                          dns_catch_all: bool = True) -> Path:
    """Generate dnsmasq.conf template. If dns_catch_all is True, add address=/#/gateway_ip."""
    lines = [
        f"interface={iface}",
        "bind-interfaces",
        "domain-needed",
        "bogus-priv",
        "server=8.8.8.8",
        f"dhcp-range={dhcp_start},{dhcp_end},12h",
        f"dhcp-option=3,{gateway_ip}",
        f"dhcp-option=6,{gateway_ip}",
        "log-queries",
        "log-dhcp",
    ]
    if dns_catch_all:
        lines.append(f"address=/#/{gateway_ip}")
    DNSMASQ_PATH.write_text("\n".join(lines), encoding="utf-8")
    log_event(f"[network] Generated dnsmasq.conf at {DNSMASQ_PATH}")
    return DNSMASQ_PATH


def prepare_runtime_files():
    """Generate hostapd + dnsmasq configs using config.json (respects dns_catch_all)."""
    cfg = load_config()
    iface = cfg.get("wifi_interface")
    if not iface:
        log_event("[network] No wifi_interface set in config; skipping runtime generation.")
        return
    ssid = cfg.get("ssid") or "EvilPortalLab"
    channel = int(cfg.get("channel", 6))
    wpa2 = bool(cfg.get("wpa2", False))
    passphrase = cfg.get("wpa_passphrase", "")
    dns_catch = bool(cfg.get("dns_catch_all", True))
    generate_hostapd_conf(iface, ssid, channel=channel, wpa2=wpa2, passphrase=passphrase)
    generate_dnsmasq_conf(iface, gateway_ip=cfg.get("portal_ip", "10.0.0.1"), dns_catch_all=dns_catch)
    log_event("[network] Runtime files generated.")


def _exec(cmd: str, strict: bool = False):
    """
    Run a shell command and log it.
    If strict=True, it will raise an exception on failure (used by start_ap).
    If strict=False, it will ignore failures (used by stop_ap for cleanup).
    """
    print(f"[exec] {cmd}")
    log_event(f"[exec] {cmd}")
    try:
        # Use check=strict to enable/disable raising exceptions
        # Capture output to provide better error messages
        subprocess.run(cmd, shell=True, check=strict, text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        # --- This is the new error reporting ---
        # Log the specific error message from the failed command
        error_message = e.stderr or e.stdout
        log_event(f"[error] Command failed: {cmd} (Error: {error_message.strip()})")
        # Re-raise the exception so the calling function (start_ap) fails
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        log_event(f"[error] Command failed: {cmd} ({e})")
        raise e


def start_ap():
    """Start a real AP and configure captive-portal redirection (iptables + dnsmasq)."""
    cfg = load_config()
    iface = cfg.get("wifi_interface")
    if not iface:
        detected = list_wireless_interfaces()
        if not detected:
            log_event("[network] start_ap aborted: no interface configured or detected.")
            return False
        iface = detected[0]
        cfg["wifi_interface"] = iface
        try:
            save_config(cfg)
            log_event(f"[network] Auto-selected interface '{iface}' and saved to config.json")
        except Exception:
            log_event(f"[network] Auto-selected interface '{iface}' (failed to save to config)")

    ssid = cfg.get("ssid", "EvilPortal")
    channel = int(cfg.get("channel", 6))
    passphrase = cfg.get("wpa_passphrase", "password123")
    wpa2 = bool(cfg.get("wpa2", True))

    portal_ip = cfg.get("portal_ip", "10.0.0.1")
    if not cfg.get("portal_ip"):
        cfg["portal_ip"] = portal_ip
        try:
            save_config(cfg)
            log_event(f"[network] Set portal_ip to {portal_ip} in config.json")
        except Exception as e:
            log_event(f"[network] Failed to save portal_ip: {e}")

    portal_port = int(cfg.get("portal_port", 8080))

    dns_catch = bool(cfg.get("dns_catch_all", True))
    generate_hostapd_conf(iface, ssid, channel=channel, wpa2=wpa2, passphrase=passphrase)
    generate_dnsmasq_conf(iface, gateway_ip=portal_ip, dns_catch_all=dns_catch)

    print(f"\n=== Starting Real AP on {iface} ({portal_ip}) ===")
    log_event(f"[network] Starting real AP on {iface}")

    # --- MODIFIED: All start_ap commands now use strict=True ---
    # We allow nmcli to fail gracefully if it's not present
    _exec(f"nmcli dev set {iface} managed no || true", strict=False)
    _exec(f"ip link set {iface} down", strict=True)
    _exec(f"ip addr flush dev {iface}", strict=True)
    _exec(f"ip addr add {portal_ip}/24 dev {iface}", strict=True)
    _exec(f"ip link set {iface} up", strict=True)
    _exec("sysctl -w net.ipv4.ip_forward=1", strict=True)

    upstream = cfg.get("upstream_interface") or "eth0"
    
    _exec(f"iptables -t nat -A POSTROUTING -o {upstream} -j MASQUERADE", strict=True)
    _exec(f"iptables -A FORWARD -i {upstream} -o {iface} -m state --state RELATED,ESTABLISHED -j ACCEPT", strict=True)

    # --- FIX 1 (LOGIC): Moved REJECT rule BEFORE the general DROP rule ---
    # --- FIX 2 (CRASH): Changed from '-t nat -A PREROUTING' to '-A FORWARD' ---
    _exec(f"iptables -A FORWARD -i {iface} -p tcp --dport 443 -j REJECT", strict=True)
    
    # This general DROP rule must come AFTER specific rules (like the REJECT above)
    _exec(f"iptables -A FORWARD -i {iface} -o {upstream} -j DROP", strict=True)

    # NAT rules for DNS and HTTP redirection (Captive Portal)
    _exec(f"iptables -t nat -A PREROUTING -i {iface} -p tcp --dport 53 -j DNAT --to-destination {portal_ip}:53", strict=True)
    _exec(f"iptables -t nat -A PREROUTING -i {iface} -p udp --dport 53 -j DNAT --to-destination {portal_ip}:53", strict=True)
    _exec(f"iptables -t nat -A PREROUTING -i {iface} -p tcp --dport 80 -j DNAT --to-destination {portal_ip}:{portal_port}", strict=True)
    
    # --- REMOVED failing line: ---
    # _exec(f"iptables -t nat -A PREROUTING -i {iface} -p tcp --dport 443 -j REJECT", strict=True)

    _exec("pkill hostapd || true", strict=False) # Keep pkill non-strict
    _exec("pkill dnsmasq || true", strict=False) # Keep pkill non-strict
    _exec(f'hostapd "{HOSTAPD_PATH}" -B', strict=True)
    _exec(f'dnsmasq -C "{DNSMASQ_PATH}" -k &', strict=True)

    log_event("[network] AP started with captive portal redirection.")
    print("AP started successfully.")
    return True


def stop_ap():
    """Stop AP and clean up iptables and processes."""
    cfg = load_config()
    iface = cfg.get("wifi_interface", "wlan0")
    upstream = cfg.get("upstream_interface") or "eth0"
    portal_ip = cfg.get("portal_ip", "10.0.0.1") 
    portal_port = int(cfg.get("portal_port", 8080))

    print(f"\n=== Stopping AP on {iface} ===")
    log_event(f"[network] Stopping AP on {iface}")

    # --- MODIFIED: All stop_ap commands use strict=False (default) ---
    _exec("pkill hostapd || true")
    _exec("pkill dnsmasq || true")

    _exec(f"iptables -t nat -D POSTROUTING -o {upstream} -j MASQUERADE || true")
    _exec(f"iptables -D FORWARD -i {upstream} -o {iface} -m state --state RELATED,ESTABLISHED -j ACCEPT || true")
    
    # --- FIX 3: Update cleanup to remove the correct rule ---
    _exec(f"iptables -D FORWARD -i {iface} -p tcp --dport 443 -j REJECT || true")
    
    _exec(f"iptables -D FORWARD -i {iface} -o {upstream} -j DROP || true")

    _exec(f"iptables -t nat -D PREROUTING -i {iface} -p tcp --dport 53 -j DNAT --to-destination {portal_ip}:53 || true")
    _exec(f"iptables -t nat -D PREROUTING -i {iface} -p udp --dport 53 -j DNAT --to-destination {portal_ip}:53 || true")

    _exec(f"iptables -t nat -D PREROUTING -i {iface} -p tcp --dport 80 -j DNAT --to-destination {portal_ip}:{portal_port} || true")
    
    # --- REMOVED matching failing line: ---
    # _exec(f"iptables -t nat -D PREROUTING -i {iface} -p tcp --dport 443 -j REJECT || true")

    _exec("sysctl -w net.ipv4.ip_forward=0")
    _exec(f"ip link set {iface} down")

    _exec(f"nmcli dev set {iface} managed yes || true")

    log_event("[network] AP stopped and cleaned up.")
    print("AP stopped and cleaned up.")
    return True
