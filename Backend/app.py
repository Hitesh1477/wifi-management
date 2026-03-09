from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
import os
import socket
import ipaddress

# ✅ Import DB collections (ONLY from db.py)
from db import users_collection, admins_collection, sessions_collection

# ✅ Import Blueprints
from admin_routes import admin_routes
from auth_routes import auth_routes
from filtering_routes import filtering_blueprint

# --------------------------------------------------
# ✅ APP CONFIG
# --------------------------------------------------
app = Flask(__name__)
CORS(app)

app.config["SECRET_KEY"] = "your-secret-key"

# --------------------------------------------------
# ✅ PATH CONFIG
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "Frontend")

# --------------------------------------------------
# ✅ REGISTER BLUEPRINTS
# --------------------------------------------------
app.register_blueprint(auth_routes, url_prefix="/api/auth")
app.register_blueprint(admin_routes, url_prefix="/api")  # Routes already have /admin prefix
app.register_blueprint(filtering_blueprint, url_prefix="/api/admin")

# --------------------------------------------------
# ✅ ALLOW ONLY LOCAL NETWORK (Wi-Fi)
# --------------------------------------------------
@app.before_request
def allow_lan_only():
    raw_ip = request.remote_addr or ""
    if not raw_ip:
        abort(403)

    try:
        client_ip = ipaddress.ip_address(raw_ip)
    except ValueError:
        abort(403)

    if client_ip.is_loopback:
        return

    if not client_ip.is_private:
        abort(403)

# --------------------------------------------------
# ✅ HELPER: GET REAL LAN IP
# --------------------------------------------------
def get_local_network_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# --------------------------------------------------
# ✅ FRONTEND ROUTES
# --------------------------------------------------

# 🔹 Login page
@app.route("/")
def login_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Login"),
        "index.html"
    )

# 🔹 Home page
@app.route("/home")
def home_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Login"),
        "home.html"
    )

# 🔹 Admin login page
@app.route("/admin/login")
def admin_login_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Final Admin"),
        "admin_login.html"
    )

# 🔹 Admin dashboard page
@app.route("/admin")
def admin_page():
    return send_from_directory(
        os.path.join(FRONTEND_DIR, "Final Admin"),
        "admin.html"
    )

# --------------------------------------------------
# ✅ STATIC FILES (CSS / JS / IMAGES)
# --------------------------------------------------

# 🔹 Serve Login folder files (style.css, script.js, images)
@app.route("/Login/<path:filename>")
def serve_login_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "Login"), filename)

# 🔹 Serve Final Admin folder files (admin.css, admin.js, images)
@app.route("/Final Admin/<path:filename>")
def serve_admin_files(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "Final Admin"), filename)

# 🔹 Serve admin panel page templates
@app.route("/pages/<path:filename>")
def serve_admin_pages(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "Final Admin", "pages"), filename)

# 🔹 Generic static route (backup)
@app.route("/static/<path:filename>")
def serve_static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

# --------------------------------------------------
# ✅ API STATUS CHECK
# --------------------------------------------------
@app.route("/api/status")
def api_status():
    return jsonify({
        "message": "Backend running on LAN ✅",
        "server_ip": get_local_network_ip()
    })

# --------------------------------------------------
# ✅ RUN SERVER (LAN HOSTING)
# --------------------------------------------------
# --------------------------------------------------
# ✅ RUN SERVER (LAN HOSTING)
# --------------------------------------------------
if __name__ == "__main__":
    try:
        from linux_firewall_manager import setup_hotspot_firewall, get_firewall_manager
        import subprocess
        
        print("🔥 Initializing Firewall Rules...")
        setup_hotspot_firewall()
        firewall_manager = get_firewall_manager()
        hotspot_iface = getattr(firewall_manager, "hotspot_interface", "wlx782051ac644f")
        internet_iface = getattr(firewall_manager, "internet_interface", "wlp0s20f3")
        print(f"📡 Firewall interfaces: hotspot={hotspot_iface}, internet={internet_iface}")
        
        # Disable IPv6 on hotspot interface to prevent bypass
        try:
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv6.conf.all.disable_ipv6=1'], check=False)
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv6.conf.default.disable_ipv6=1'], check=False)
            subprocess.run(['sudo', 'sysctl', '-w', f'net.ipv6.conf.{hotspot_iface}.disable_ipv6=1'], check=False)
            print("🔒 IPv6 Disabled (Prevents Bypass)")
        except Exception as e:
            print(f"⚠️ Failed to disable IPv6: {e}")
            
        # 🚨 EMERGENCY: Explicitly block known evasive IPs for slowroads.io
        try:
            slowroads_ips = [
                "104.26.7.92", "104.26.6.92", "172.67.70.173", # Cloudflare
                "76.76.21.21" # Vercel/common
            ]
            for ip in slowroads_ips:
                subprocess.run(['sudo', 'iptables', '-A', 'GLOBAL_BLOCKS', '-d', ip, '-j', 'DROP'], check=False)
                subprocess.run(['sudo', 'iptables', '-A', 'GLOBAL_BLOCKS', '-d', ip, '-p', 'udp', '--dport', '443', '-j', 'DROP'], check=False)
            
            # Block Public DNS here too
            public_dns = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"]
            for dns in public_dns:
                subprocess.run(['sudo', 'iptables', '-I', 'FORWARD', '1', '-d', dns, '-j', 'DROP'], check=False)
                
            print(f"🔒 Added emergency blocks for slowroads.io ({len(slowroads_ips)} IPs, TCP+UDP)")
        except Exception:
            pass
            
        print("✅ Firewall Rules Applied")
    except Exception as e:
        print(f"⚠️ Firewall Init Failed: {e}")

    try:
        from bandwidth_manager import apply_bandwidth_for_active_users, start_auto_bandwidth_daemon

        print("Initializing activity-based bandwidth management...")
        apply_bandwidth_for_active_users()
        start_auto_bandwidth_daemon(interval_seconds=300)
        print("Bandwidth management daemon started")
    except Exception as e:
        print(f"⚠️ Bandwidth management init failed: {e}")
        
    app.run(host="0.0.0.0", port=5000, debug=False) # Disable debug to prevent double-execution on reload
