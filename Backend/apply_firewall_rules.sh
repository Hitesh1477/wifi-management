#!/bin/bash
# Apply updated firewall rules with pre-authentication blacklist
# This blocks ALL apps and websites before login

echo "🔧 Applying updated firewall rules..."
echo ""

cd "$(dirname "$0")"

# Import and run the setup_captive_portal function
python3 <<'PYEOF'
import sys
sys.path.insert(0, '/home/nikhil/wifi-management/Backend')

from linux_firewall_manager import setup_captive_portal, get_firewall_manager

print("📋 Step 1: Flushing existing firewall rules...")
manager = get_firewall_manager()

# Clear FORWARD chain
import subprocess
subprocess.run(['sudo', 'iptables', '-F', 'FORWARD'], check=True)
print("✅ Cleared FORWARD chain")

print("")
print("📋 Step 2: Applying new captive portal rules...")
if setup_captive_portal():
    print("✅ Captive portal configured with pre-auth blacklist")
else:
    print("❌ Failed to setup captive portal")
    sys.exit(1)

print("")
print("📋 Step 3: Verifying firewall rules...")
result = subprocess.run(
    ['sudo', 'iptables', '-L', 'FORWARD', '-v', '-n'],
    capture_output=True,
    text=True
)
print(result.stdout)
PYEOF

if [ $? -eq 0 ]; then
    echo ""
    echo "==================================="
    echo "✅ Firewall Rules Applied!"
    echo "==================================="
    echo ""
    echo "🚫 All internet traffic is now BLOCKED before login:"
    echo "   - Instagram, Snapchat, WhatsApp ❌"
    echo "   - Websites, apps, games ❌"
    echo ""
    echo "✅ Only ALLOWED before login:"
    echo "   - Login page: http://192.168.50.1:5000"
    echo "   - Admin panel: http://192.168.50.1:5000/admin"
    echo ""
    echo "Note: Users will get full internet access AFTER successful login"
else
    echo ""
    echo "❌ Failed to apply firewall rules"
    exit 1
fi
