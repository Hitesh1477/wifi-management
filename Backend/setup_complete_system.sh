#!/bin/bash
# Master Setup Script for WiFi Management System
# This script sets up the complete hotspot with captive portal and filtering

set -e  # Exit on error

echo "=================================="
echo "WiFi Management System Setup"
echo "=================================="
echo ""

# Configuration
HOTSPOT_INTERFACE="wlx782051ac644f"  # USB WiFi adapter
INTERNET_INTERFACE="wlp0s20f3"        # Built-in WiFi (connected to internet)
HOTSPOT_IP="192.168.50.1"
HOTSPOT_SSID="CampusWiFi"
HOTSPOT_PASSWORD="campus123"

echo "📡 Hotspot Interface: $HOTSPOT_INTERFACE"
echo "🌐 Internet Interface: $INTERNET_INTERFACE"
echo "📶 SSID: $HOTSPOT_SSID"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)" 
   exit 1
fi

echo "==== Step 1: Installing Required Packages ===="
apt update
apt install -y hostapd dnsmasq iptables wireless-tools net-tools tshark wireshark

echo ""
echo "==== Step 2: Stopping Services ===="
systemctl stop hostapd || true
systemctl stop dnsmasq || true

echo ""
echo "==== Step 3: Configuring hostapd ===="
cat > /etc/hostapd/hostapd.conf << EOF
# Interface configuration
interface=$HOTSPOT_INTERFACE
driver=nl80211

# WiFi configuration
ssid=$HOTSPOT_SSID
hw_mode=g
channel=6
country_code=IN

# Security
auth_algs=1
wpa=2
wpa_passphrase=$HOTSPOT_PASSWORD
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP CCMP
rsn_pairwise=CCMP

# Other settings
macaddr_acl=0
ignore_broadcast_ssid=0
EOF

echo "✅ hostapd.conf created"

# Tell hostapd where to find the config
echo "DAEMON_CONF=\"/etc/hostapd/hostapd.conf\"" > /etc/default/hostapd

echo ""
echo "==== Step 4: Configuring dnsmasq ===="
# Backup original config
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup || true

cat > /etc/dnsmasq.conf << EOF
# Interface to bind to
interface=$HOTSPOT_INTERFACE

# Don't use /etc/resolv.conf
no-resolv

# Upstream DNS servers
server=8.8.8.8
server=8.8.4.4

# DHCP configuration
dhcp-range=192.168.50.100,192.168.50.250,12h
dhcp-option=3,$HOTSPOT_IP
dhcp-option=6,$HOTSPOT_IP

# Logging
log-queries
log-dhcp
EOF

echo "✅ dnsmasq.conf created"

echo ""
echo "==== Step 5: Configuring Network Interfaces ===="
# Stop NetworkManager from managing the hotspot interface
cat > /etc/NetworkManager/conf.d/unmanaged-hotspot.conf << EOF
[keyfile]
unmanaged-devices=interface-name:$HOTSPOT_INTERFACE
EOF

echo "✅ NetworkManager configured to ignore hotspot interface"

echo ""
echo "==== Step 6: Enabling IP Forwarding ===="
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=1

echo "✅ IP forwarding enabled"

echo ""
echo "==== Step 7: Setting up tshark permissions ===="
# Allow non-root packet capture
dpkg-reconfigure -p critical wireshark-common << EOF
yes
EOF

# Add current user to wireshark group
SUDO_USER_NAME="${SUDO_USER:-$USER}"
usermod -aG wireshark "$SUDO_USER_NAME"

echo "✅ tshark permissions configured for user: $SUDO_USER_NAME"

echo ""
echo "==== Step 8: Creating Startup Script ===="
cat > /usr/local/bin/start-wifi-hotspot.sh << 'SCRIPTEOF'
#!/bin/bash
HOTSPOT_INTERFACE="wlx782051ac644f"
HOTSPOT_IP="192.168.50.1"

echo "🔧 Configuring $HOTSPOT_INTERFACE..."

# Bring interface down
ip link set $HOTSPOT_INTERFACE down
sleep 1

# Flush IP addresses
ip addr flush dev $HOTSPOT_INTERFACE

# Set static IP
ip addr add ${HOTSPOT_IP}/24 dev $HOTSPOT_INTERFACE

# Bring interface up
ip link set $HOTSPOT_INTERFACE up

echo "✅ Interface configured"
SCRIPTEOF

chmod +x /usr/local/bin/start-wifi-hotspot.sh

echo "✅ Startup script created"

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Run: sudo /usr/local/bin/start-wifi-hotspot.sh"
echo "2. Run: sudo systemctl start dnsmasq"
echo "3. Run: sudo systemctl start hostapd"
echo "4. Run: cd $(pwd) && sudo python3 linux_firewall_manager.py"
echo "5. Run: python3 app.py"
echo ""
echo "To auto-start on boot:"
echo "  sudo systemctl enable hostapd"
echo "  sudo systemctl enable dnsmasq"
echo ""
