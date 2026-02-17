#!/bin/bash
# Fix dnsmasq Port Conflict
# Run with: sudo ./fix_dnsmasq.sh

set -e

echo "🔧 Fixing dnsmasq configuration..."
echo ""

# Update dnsmasq config to bind only to hotspot interface
cat > /etc/dnsmasq.conf << 'EOF'
# Interface to bind to
interface=wlx782051ac644f

# Bind only to this interface (avoid port 53 conflict with systemd-resolved)
bind-interfaces

# Don't use /etc/resolv.conf
no-resolv

# Upstream DNS servers
server=8.8.8.8
server=8.8.4.4

# DHCP configuration
dhcp-range=192.168.50.100,192.168.50.250,12h
dhcp-option=3,192.168.50.1
dhcp-option=6,192.168.50.1

# Logging
log-queries
log-dhcp
EOF

echo "✅ Updated /etc/dnsmasq.conf"
echo ""

# Restart dnsmasq
echo "🔄 Restarting dnsmasq..."
systemctl restart dnsmasq

if systemctl is-active --quiet dnsmasq; then
    echo "✅ dnsmasq is now running!"
else
    echo "❌ dnsmasq failed to start. Checking errors..."
    journalctl -u dnsmasq -n 20 --no-pager
    exit 1
fi

echo ""
echo "✅ Fix complete! Now run: sudo ./start_system.sh"
