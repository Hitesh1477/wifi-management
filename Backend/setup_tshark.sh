#!/bin/bash
# Install tshark for packet capture
# This script sets up tshark with proper permissions for non-root packet capture

set -e

echo "📦 Installing tshark (Wireshark CLI)..."
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)" 
   exit 1
fi

# Install packages
echo "Installing wireshark/tshark..."
DEBIAN_FRONTEND=noninteractive apt install -y tshark wireshark

echo ""
echo "Configuring non-root packet capture..."

# Configure wireshark to allow non-root users
echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections

# Reconfigure wireshark-common
DEBIAN_FRONTEND=noninteractive dpkg-reconfigure wireshark-common

# Add user to wireshark group
SUDO_USER_NAME="${SUDO_USER:-$USER}"
usermod -aG wireshark "$SUDO_USER_NAME"

echo ""
echo "✅ tshark installed successfully!"
echo ""
echo "⚠️  IMPORTANT: The user '$SUDO_USER_NAME' has been added to the 'wireshark' group."
echo "   You need to LOG OUT and LOG BACK IN for this to take effect."
echo ""
echo "After logging back in, verify with:"
echo "  groups | grep wireshark"
echo ""
