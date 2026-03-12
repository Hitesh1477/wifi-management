#!/bin/bash
# Start WiFi Hotspot - Quick Start Script
# Run this after setup_complete_system.sh has been executed once

set -e

echo "🚀 Starting WiFi Management System..."
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)" 
   exit 1
fi

HOTSPOT_INTERFACE="${HOTSPOT_INTERFACE:-wlx782051ac644f}"
HOTSPOT_IP="${HOTSPOT_GATEWAY_IP:-192.168.50.1}"

echo "==== Step 1: Configure Network Interface ===="
echo "🔧 Configuring $HOTSPOT_INTERFACE..."

# Bring interface down
ip link set $HOTSPOT_INTERFACE down 2>/dev/null || true
sleep 1

# Flush IP addresses
ip addr flush dev $HOTSPOT_INTERFACE

# Set static IP
ip addr add ${HOTSPOT_IP}/24 dev $HOTSPOT_INTERFACE

# Bring interface up
ip link set $HOTSPOT_INTERFACE up

echo "✅ Interface configured with IP $HOTSPOT_IP"
sleep 1

echo ""
echo "==== Step 2: Starting dnsmasq (DHCP/DNS) ===="
systemctl restart dnsmasq
sleep 2

if systemctl is-active --quiet dnsmasq; then
    echo "✅ dnsmasq is running"
else
    echo "❌ dnsmasq failed to start"
    journalctl -u dnsmasq -n 20 --no-pager
    exit 1
fi

echo ""
echo "==== Step 3: Starting hostapd (WiFi AP) ===="
systemctl restart hostapd
sleep 3

if systemctl is-active --quiet hostapd; then
    echo "✅ hostapd is running"
else
    echo "❌ hostapd failed to start"
    journalctl -u hostapd -n 20 --no-pager
    exit 1
fi

echo ""
echo "==== Step 4: Setting up Firewall (NAT + Captive Portal) ===="
cd "$(dirname "$0")"

echo ""
echo "==== Step 4a: Ensuring DNS Auto-Update Permissions ===="
AUTOUPDATE_USER="${SUDO_USER:-nikhil}"
if [[ -x "./setup_dnsmasq_autoupdate.sh" ]]; then
    if ./setup_dnsmasq_autoupdate.sh "$AUTOUPDATE_USER"; then
        echo "✅ DNS auto-update helper ready for user: $AUTOUPDATE_USER"
    else
        echo "⚠️  Could not configure DNS auto-update helper (continuing)"
    fi
else
    echo "⚠️  setup_dnsmasq_autoupdate.sh not found/executable (continuing)"
fi

# Run firewall setup with Python
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/nikhil/wifi-management/Backend')

from linux_firewall_manager import setup_captive_portal, update_firewall_rules
from dns_filtering_manager import update_dnsmasq_blocklist

print("  🔧 Setting up captive portal...")
if setup_captive_portal():
    print("  ✅ Captive portal configured")
else:
    print("  ❌ Captive portal setup failed")
    sys.exit(1)

print("  🔧 Updating web filtering rules...")
if update_firewall_rules():
    print("  ✅ Web filtering rules applied")
else:
    print("  ⚠️  No filtering rules found (will use defaults)")

print("  🔧 Syncing dnsmasq blocklist from database...")
if update_dnsmasq_blocklist():
    print("  ✅ DNS blocklist synchronized")
else:
    print("  ⚠️  DNS blocklist sync failed (check sudo/helper permissions if backend runs as non-root)")

print("  ✅ Firewall is ready")
PYEOF

if [ $? -ne 0 ]; then
    echo "❌ Firewall setup failed"
    exit 1
fi

# Captive portal blocking is handled via dedicated hotspot chains.
echo "  ✅ Captive portal chain enforcement enabled (global FORWARD policy unchanged)"

echo ""
echo "=================================="
echo "✅ WiFi Hotspot Started!"
echo "=================================="
echo ""
echo "Network Details:"
echo "  📶 SSID: CampusWiFi"
echo "  🔐 Password: campus123"
echo "  🌐 Gateway IP: $HOTSPOT_IP"
echo "  📡 DHCP Range: 192.168.50.100-250"
echo ""
echo "Next steps:"
echo "  1. Connect a device to the WiFi network"
echo "  2. Start Flask backend:"
echo "     cd /home/nikhil/wifi-management/Backend"
echo "     python3 app.py"
echo "  3. On connected device, navigate to: http://192.168.50.1:5000"
echo ""
echo "Note: Users must login to access the internet (captive portal active)"
echo ""
