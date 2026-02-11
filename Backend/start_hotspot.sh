#!/bin/bash
# Quick start script for WiFi hotspot
# Use this after running setup_linux_hotspot.sh

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}WiFi Hotspot Quick Start${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Function to check if interface exists
check_interface() {
    if iwconfig 2>&1 | grep -q "wlan0"; then
        echo -e "${GREEN}✓${NC} WiFi adapter detected (wlan0)"
        return 0
    else
        echo -e "${RED}✗${NC} WiFi adapter not detected!"
        echo ""
        echo "Please check:"
        echo "1. TP-Link adapter is plugged in"
        echo "2. VMware USB passthrough is enabled"
        echo "3. Driver is installed"
        echo ""
        echo "To check USB devices: lsusb | grep -i realtek"
        return 1
    fi
}

# Function to find internet interface
find_internet_interface() {
    INET_IFACE=$(ip route | grep default | head -n1 | awk '{print $5}')
    if [ -z "$INET_IFACE" ]; then
        echo -e "${YELLOW}⚠${NC} Could not auto-detect internet interface"
        echo "Please edit linux_firewall_manager.py and set the correct interface"
        return 1
    else
        echo -e "${GREEN}✓${NC} Internet interface: $INET_IFACE"
        return 0
    fi
}

# Step 1: Check adapter
echo "Step 1: Checking WiFi adapter..."
if ! check_interface; then
    exit 1
fi
echo ""

# Step 2: Check internet interface
echo "Step 2: Detecting internet interface..."
find_internet_interface
echo ""

# Step 3: Get backend directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Step 3: Backend directory: $SCRIPT_DIR"
echo ""

# Step 4: Setup firewall and NAT
echo "Step 4: Setting up firewall and NAT..."
cd "$SCRIPT_DIR"
if python3 linux_firewall_manager.py; then
    echo -e "${GREEN}✓${NC} Firewall setup complete"
else
    echo -e "${RED}✗${NC} Firewall setup failed"
    echo "Check if MongoDB is running and accessible"
fi
echo ""

# Step 5: Start hotspot
echo "Step 5: Starting hotspot..."
if systemctl start dnsmasq && systemctl start hostapd; then
    echo -e "${GREEN}✓${NC} Hotspot started"
else
    echo -e "${RED}✗${NC} Failed to start hotspot"
    echo ""
    echo "Check logs:"
    echo "  sudo journalctl -u hostapd -n 50"
    echo "  sudo journalctl -u dnsmasq -n 50"
    exit 1
fi
echo ""

# Step 6: Check status
echo "Step 6: Checking status..."
sleep 2

if systemctl is-active --quiet hostapd && systemctl is-active --quiet dnsmasq; then
    echo -e "${GREEN}✓${NC} Hotspot is running"
    
    # Get WiFi info
    SSID=$(grep "^ssid=" /etc/hostapd/hostapd.conf | cut -d'=' -f2)
    PASSWORD=$(grep "^wpa_passphrase=" /etc/hostapd/hostapd.conf | cut -d'=' -f2)
    
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}✅ Hotspot Ready!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "WiFi Network Name (SSID): $SSID"
    echo "Password: $PASSWORD"
    echo "Gateway IP: 192.168.50.1"
    echo ""
    echo "To access admin panel:"
    echo "1. Connect to the WiFi hotspot"
    echo "2. Open browser and go to: http://192.168.50.1:5000/admin/login"
    echo ""
    echo "Useful commands:"
    echo "  sudo hotspot status   - Check hotspot status"
    echo "  sudo hotspot restart  - Restart hotspot"
    echo "  sudo hotspot stop     - Stop hotspot"
    echo ""
else
    echo -e "${RED}✗${NC} Hotspot failed to start properly"
    exit 1
fi

# Optional: Start Flask backend
echo "Would you like to start the Flask backend now? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Starting Flask backend..."
    systemctl start wifi-backend
    sleep 2
    if systemctl is-active --quiet wifi-backend; then
        echo -e "${GREEN}✓${NC} Flask backend running"
        echo "   Access at: http://192.168.50.1:5000"
    else
        echo -e "${YELLOW}⚠${NC} Flask backend failed to start"
        echo "   Try manually: cd $SCRIPT_DIR && python3 app.py"
    fi
fi

echo ""
echo "Done!"
