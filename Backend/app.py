from flask import Flask, request, jsonify, abort, send_from_directory
from flask_cors import CORS
import os
import socket

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
    ip = request.remote_addr

    # Allow localhost for testing
    if ip in ("127.0.0.1", "::1"):
        return

    # Allow private IP ranges only
    if not (
        ip.startswith("192.168.") or
        ip.startswith("10.") or
        ip.startswith("172.")
    ):
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
        from linux_firewall_manager import setup_hotspot_firewall
        import subprocess
        
        print("🔥 Initializing Firewall Rules...")
        setup_hotspot_firewall()
        
        # Disable IPv6 on hotspot interface to prevent bypass
        try:
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv6.conf.all.disable_ipv6=1'], check=False)
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv6.conf.default.disable_ipv6=1'], check=False)
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv6.conf.wlx782051ac644f.disable_ipv6=1'], check=False)
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
        
    app.run(host="0.0.0.0", port=5000, debug=False) # Disable debug to prevent double-execution on reload
