#!/usr/bin/env python3

import sys
import signal 
from core.utils import load_config, ensure_dirs, log_event  # type: ignore
import core.network as network  # type: ignore

_cleanup_has_run = False

def cmd_prepare():
    cfg = load_config()
    if not cfg.get("wifi_interface"):
        print("No wifi_interface set in config.json; use 'choose-iface' to set one.")
    print("Generating runtime network configuration files (templates only)...")
    network.prepare_runtime_files()
    print("Files generated under data/runtime/ — inspect before applying any commands.")


def cmd_choose_iface():
    print("Interactive adapter selection:")
    sel = network.choose_adapter_interactive()
    if sel:
        print("Selected interface:", sel)
    else:
        print("No selection made.")


def cmd_status():
    cfg = load_config()
    print("EvilPortal status")
    print("Config (merged):")
    for k, v in cfg.items():
        print(f"  {k}: {v}")
    print("Detected wireless interfaces:", network.list_wireless_interfaces())
    print("AP support heuristic:", network.iw_supports_ap())


def run_cleanup_and_exit(sig=None, frame=None):
    """
    This function is called by the signal handler or at exit.
    It runs the network.stop_ap() cleanup.
    """
    global _cleanup_has_run
    if _cleanup_has_run:
        return
    _cleanup_has_run = True
    
    print("\nInterrupted. Running network cleanup...")
    log_event("[main] Signal received. Running stop_ap() cleanup.")
    try:
        network.stop_ap()
    except Exception as e:
        log_event(f"[main] Error during cleanup: {e}")
        print(f"Error during cleanup: {e}")
    print("Cleanup complete. Exiting.")
    sys.exit(0)


def cmd_start():
    cfg = load_config()
    print("Starting EvilPortal. Config:")
    for k, v in cfg.items():
        print(f"  {k}: {v}")

    if cfg.get("wifi_interface"):
        print("Generating/refreshing runtime network files...")
        network.prepare_runtime_files()
        print("Runtime files ready under data/runtime/")

    signal.signal(signal.SIGINT, run_cleanup_and_exit)
    signal.signal(signal.SIGTERM, run_cleanup_and_exit)

    try:
        print("\nLaunching local admin and portal web server...")

        import importlib
        portal = importlib.import_module("core.portal")
        importlib.reload(portal) 

        app = getattr(portal, "app", None)
        if app is None:
            raise RuntimeError("core.portal does not expose 'app'; cannot start server")

        port = int(cfg.get("portal_port", 8080))
        log_event(f"[main] Starting Flask portal on 0.0.0.0:{port}")
        
        app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)

    except Exception as e:
        # --- MODIFIED: Specific error for port-in-use ---
        if "Address already in use" in str(e):
            port = cfg.get("portal_port", 8080)
            print(f"\n[ERROR] Port {port} is already in use.")
            print("Another program (or a leftover wifitool) is running on that port.")
            print("Please stop the other program or change 'portal_port' in your config.json file.")
            log_event(f"[main] CRITICAL: Address already in use (Port {port})")
        else:
            log_event(f"[main] Portal error: {e}")
            print("Portal stopped with error:", e)
        # --- END OF MODIFICATION ---
    
    finally:
        print("Server is shutting down. Running cleanup...")
        run_cleanup_and_exit()


def print_help():
    print("""
Available commands:
  prepare        Generate runtime config templates
  choose-iface   Interactively select wireless interface
  status         Show current config and interfaces
  start          Run the EvilPortal server (includes admin panel)
  help           Show this message
""")


def main():
    ensure_dirs()
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <command>  (help for options)")
        return
    cmd = sys.argv[1].lower()
    if cmd in ("help", "-h", "--help"):
        print_help()
    elif cmd == "prepare":
        cmd_prepare()
    elif cmd == "choose-iface":
        cmd_choose_iface()
    elif cmd == "status":
        cmd_status()
    elif cmd == "start":
        cmd_start()
    else:
        print("Unknown command:", cmd)
        print("Run: python3 main.py help")

if __name__ == "__main__":
    main()