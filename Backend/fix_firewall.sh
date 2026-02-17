#!/bin/bash
# Quick fix script to remove the problematic ACCEPT rule
# This rule was allowing all traffic to bypass the captive portal

echo "🔧 Fixing firewall rules..."
echo ""

# Remove the broad ACCEPT rule if it exists
sudo iptables -D FORWARD -i wlx782051ac644f -o wlp0s20f3 -j ACCEPT 2>/dev/null

echo "✅ Removed broad ACCEPT rule"
echo ""
echo "📋 Current FORWARD chain rules:"
sudo iptables -L FORWARD -v -n --line-numbers
echo ""
echo "==================================="
echo "✅ Firewall Fixed!"
echo "==================================="
echo ""
echo "🎮 **IMPORTANT for testing:**"
echo "   - Close any running games/apps completely"
echo "   - OR disconnect and reconnect to WiFi"
echo "   - This clears existing connections"
echo ""
echo "Established connections are allowed (rule #1 above)"
echo "New connections will be blocked by the DROP rule!"
echo ""
echo "Try opening a game now - it should fail to connect."
