#!/bin/bash
# Setup script for Linux WiFi Hotspot with Web Filtering
# Run this on your Linux VM after installing the system

set -e  # Exit on error

echo "========================================="
echo "WiFi Hotspot Setup Script"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# 1. Install required packages
echo "Step 1: Installing required packages..."
apt update
apt install -y hostapd dnsmasq iptables iptables-persistent \
    python3-pip python3-venv net-tools wireless-tools \
    bridge-utils iw git dkms build-essential

# 2. Stop services during configuration
echo ""
echo "Step 2: Stopping services for configuration..."
systemctl stop hostapd || true
systemctl stop dnsmasq || true

# 3. Backup existing configs
echo ""
echo "Step 3: Backing up existing configurations..."
[ -f /etc/hostapd/hostapd.conf ] && cp /etc/hostapd/hostapd.conf /etc/hostapd/hostapd.conf.backup
[ -f /etc/dnsmasq.conf ] && cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup

# 4. Create hostapd configuration
echo ""
echo "Step 4: Creating hostapd configuration..."
cat > /etc/hostapd/hostapd.conf << 'EOF'
# WiFi Interface
interface=wlan0
driver=nl80211

# Network Settings
ssid=MyWiFiHotspot
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1

# Security Settings
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=Password@123
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Point hostapd to config file
echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' > /etc/default/hostapd

# 5. Create dnsmasq configuration
echo ""
echo "Step 5: Creating dnsmasq configuration..."
cat > /etc/dnsmasq.conf << 'EOF'
# Interface to listen on
interface=wlan0

# Never forward plain names (without a dot or domain part)
domain-needed

# Never forward addresses in the non-routed address spaces
bogus-priv

# DHCP range
dhcp-range=192.168.50.10,192.168.50.100,255.255.255.0,24h

# Router (gateway)
dhcp-option=3,192.168.50.1

# DNS servers
dhcp-option=6,192.168.50.1

# Upstream DNS
no-resolv
server=8.8.8.8
server=8.8.4.4

# Log queries for debugging
log-queries
log-dhcp
log-facility=/var/log/dnsmasq.log

# Cache size
cache-size=500
EOF

# 6. Enable IP forwarding
echo ""
echo "Step 6: Enabling IP forwarding..."
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# 7. Set up network interface
echo ""
echo "Step 7: Configuring network interface..."
cat > /etc/network/interfaces.d/wlan0 << 'EOF'
auto wlan0
iface wlan0 inet static
    address 192.168.50.1
    netmask 255.255.255.0
EOF

# 8. Create systemd service for Flask backend
echo ""
echo "Step 8: Creating Flask backend service..."

# Get the current directory (where the script is run from)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR"

cat > /etc/systemd/system/wifi-backend.service << EOF
[Unit]
Description=WiFi Management Flask Backend
After=network.target mongodb.service

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$BACKEND_DIR
ExecStart=/usr/bin/python3 $BACKEND_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 9. Create systemd service for domain resolver
echo ""
echo "Step 9: Creating domain resolver service..."
cat > /etc/systemd/system/domain-resolver.service << EOF
[Unit]
Description=Domain IP Resolver Service
After=network.target wifi-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=$BACKEND_DIR
ExecStart=/usr/bin/python3 $BACKEND_DIR/domain_resolver_service.py --interval 3600
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 10. Create hotspot control script
echo ""
echo "Step 10: Creating hotspot control script..."
cat > /usr/local/bin/hotspot << 'EOF'
#!/bin/bash
# Hotspot control script

case "$1" in
    start)
        echo "Starting hotspot..."
        systemctl start dnsmasq
        systemctl start hostapd
        echo "Hotspot started!"
        ;;
    stop)
        echo "Stopping hotspot..."
        systemctl stop hostapd
        systemctl stop dnsmasq
        echo "Hotspot stopped!"
        ;;
    restart)
        echo "Restarting hotspot..."
        systemctl restart dnsmasq
        systemctl restart hostapd
        echo "Hotspot restarted!"
        ;;
    status)
        echo "=== Hotspot Status ==="
        echo ""
        echo "hostapd:"
        systemctl status hostapd --no-pager | grep Active
        echo ""
        echo "dnsmasq:"
        systemctl status dnsmasq --no-pager | grep Active
        echo ""
        echo "Connected clients:"
        iw dev wlan0 station dump | grep Station | wc -l
        ;;
    enable)
        systemctl enable hostapd
        systemctl enable dnsmasq
        echo "Hotspot enabled on boot"
        ;;
    disable)
        systemctl disable hostapd
        systemctl disable dnsmasq
        echo "Hotspot disabled on boot"
        ;;
    *)
        echo "Usage: hotspot {start|stop|restart|status|enable|disable}"
        exit 1
        ;;
esac
EOF

chmod +x /usr/local/bin/hotspot

# 11. Install Python dependencies
echo ""
echo "Step 11: Installing Python dependencies..."
if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    pip3 install -r "$BACKEND_DIR/requirements.txt"
else
    pip3 install flask flask-cors pymongo
fi

# 12. Reload systemd
echo ""
echo "Step 12: Reloading systemd..."
systemctl daemon-reload

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Check if TP-Link adapter is detected:"
echo "   lsusb | grep -i realtek"
echo "   iwconfig"
echo ""
echo "2. If adapter not detected, install driver:"
echo "   cd ~"
echo "   git clone https://github.com/Mange/rtl8192eu-linux-driver"
echo "   cd rtl8192eu-linux-driver"
echo "   sudo dkms add ."
echo "   sudo dkms install rtl8192eu/1.0"
echo ""
echo "3. Configure hostapd with your SSID and password:"
echo "   sudo nano /etc/hostapd/hostapd.conf"
echo ""
echo "4. Find your internet interface (usually eth0 or enp0s3):"
echo "   ip link"
echo ""
echo "5. Update internet interface in:"
echo "   nano $BACKEND_DIR/linux_firewall_manager.py"
echo "   (Change 'eth0' to your interface)"
echo ""
echo "6. Setup initial firewall and NAT:"
echo "   sudo python3 $BACKEND_DIR/linux_firewall_manager.py"
echo ""
echo "7. Start the hotspot:"
echo "   sudo hotspot start"
echo ""
echo "8. Enable services on boot (optional):"
echo "   sudo hotspot enable"
echo "   sudo systemctl enable wifi-backend"
echo "   sudo systemctl enable domain-resolver"
echo ""
echo "9. Start Flask backend:"
echo "   sudo systemctl start wifi-backend"
echo ""
echo "10. Check status:"
echo "    sudo hotspot status"
echo ""
