#!/usr/bin/env python3
"""
Linux Hotspot Manager - Control WiFi hotspot
Manages hostapd, dnsmasq, and network interfaces
"""

import subprocess
import logging
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HotspotManager:
    def __init__(self):
        self.hotspot_interface = "wlan0"
        self.hotspot_ip = "192.168.50.1"
        self.hotspot_subnet = "192.168.50.0/24"
        
    def check_interface_exists(self) -> bool:
        """Check if wireless interface exists"""
        try:
            result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            return self.hotspot_interface in result.stdout
        except Exception as e:
            logger.error(f"Failed to check interface: {e}")
            return False
    
    def configure_interface(self) -> bool:
        """Configure the wireless interface with static IP"""
        try:
            # Bring interface down
            subprocess.run(['sudo', 'ip', 'link', 'set', self.hotspot_interface, 'down'], 
                         check=True)
            time.sleep(1)
            
            # Set static IP
            subprocess.run(['sudo', 'ip', 'addr', 'flush', 'dev', self.hotspot_interface], 
                         check=True)
            subprocess.run([
                'sudo', 'ip', 'addr', 'add', 
                f'{self.hotspot_ip}/24', 
                'dev', self.hotspot_interface
            ], check=True)
            
            # Bring interface up
            subprocess.run(['sudo', 'ip', 'link', 'set', self.hotspot_interface, 'up'], 
                         check=True)
            
            logger.info(f"Interface {self.hotspot_interface} configured with IP {self.hotspot_ip}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to configure interface: {e}")
            return False
    
    def start_hostapd(self) -> bool:
        """Start hostapd service"""
        try:
            subprocess.run(['sudo', 'systemctl', 'start', 'hostapd'], check=True)
            time.sleep(2)
            
            # Check if running
            result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', 'hostapd'],
                capture_output=True, text=True
            )
            
            if result.stdout.strip() == 'active':
                logger.info("hostapd started successfully")
                return True
            else:
                logger.error("hostapd failed to start")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start hostapd: {e}")
            return False
    
    def stop_hostapd(self) -> bool:
        """Stop hostapd service"""
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', 'hostapd'], check=True)
            logger.info("hostapd stopped")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop hostapd: {e}")
            return False
    
    def start_dnsmasq(self) -> bool:
        """Start dnsmasq service"""
        try:
            subprocess.run(['sudo', 'systemctl', 'start', 'dnsmasq'], check=True)
            time.sleep(1)
            
            # Check if running
            result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', 'dnsmasq'],
                capture_output=True, text=True
            )
            
            if result.stdout.strip() == 'active':
                logger.info("dnsmasq started successfully")
                return True
            else:
                logger.error("dnsmasq failed to start")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start dnsmasq: {e}")
            return False
    
    def stop_dnsmasq(self) -> bool:
        """Stop dnsmasq service"""
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', 'dnsmasq'], check=True)
            logger.info("dnsmasq stopped")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stop dnsmasq: {e}")
            return False
    
    def start_hotspot(self) -> bool:
        """Start the complete hotspot (interface + hostapd + dnsmasq)"""
        logger.info("Starting hotspot...")
        
        # Check interface exists
        if not self.check_interface_exists():
            logger.error(f"Interface {self.hotspot_interface} not found!")
            logger.info("Please check if TP-Link adapter is connected")
            return False
        
        # Configure interface
        if not self.configure_interface():
            return False
        
        # Start dnsmasq (DHCP/DNS)
        if not self.start_dnsmasq():
            return False
        
        # Start hostapd (Access Point)
        if not self.start_hostapd():
            self.stop_dnsmasq()
            return False
        
        logger.info("✅ Hotspot started successfully!")
        return True
    
    def stop_hotspot(self) -> bool:
        """Stop the complete hotspot"""
        logger.info("Stopping hotspot...")
        
        success = True
        if not self.stop_hostapd():
            success = False
        if not self.stop_dnsmasq():
            success = False
        
        if success:
            logger.info("✅ Hotspot stopped successfully!")
        return success
    
    def restart_hotspot(self) -> bool:
        """Restart the hotspot"""
        logger.info("Restarting hotspot...")
        self.stop_hotspot()
        time.sleep(2)
        return self.start_hotspot()
    
    def get_status(self) -> dict:
        """Get current hotspot status"""
        try:
            # Check hostapd
            hostapd_result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', 'hostapd'],
                capture_output=True, text=True
            )
            hostapd_active = hostapd_result.stdout.strip() == 'active'
            
            # Check dnsmasq
            dnsmasq_result = subprocess.run(
                ['sudo', 'systemctl', 'is-active', 'dnsmasq'],
                capture_output=True, text=True
            )
            dnsmasq_active = dnsmasq_result.stdout.strip() == 'active'
            
            # Check interface
            interface_exists = self.check_interface_exists()
            
            # Get connected clients
            connected_clients = 0
            if interface_exists:
                try:
                    result = subprocess.run(
                        ['iw', 'dev', self.hotspot_interface, 'station', 'dump'],
                        capture_output=True, text=True
                    )
                    # Count "Station" entries
                    connected_clients = result.stdout.count('Station')
                except:
                    pass
            
            return {
                "hotspot_active": hostapd_active and dnsmasq_active,
                "hostapd_running": hostapd_active,
                "dnsmasq_running": dnsmasq_active,
                "interface_exists": interface_exists,
                "interface_name": self.hotspot_interface,
                "hotspot_ip": self.hotspot_ip,
                "connected_clients": connected_clients
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                "hotspot_active": False,
                "error": str(e)
            }
    
    def enable_on_boot(self) -> bool:
        """Enable hotspot to start on boot"""
        try:
            subprocess.run(['sudo', 'systemctl', 'enable', 'hostapd'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'dnsmasq'], check=True)
            logger.info("Hotspot enabled on boot")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to enable on boot: {e}")
            return False
    
    def disable_on_boot(self) -> bool:
        """Disable hotspot from starting on boot"""
        try:
            subprocess.run(['sudo', 'systemctl', 'disable', 'hostapd'], check=True)
            subprocess.run(['sudo', 'systemctl', 'disable', 'dnsmasq'], check=True)
            logger.info("Hotspot disabled on boot")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to disable on boot: {e}")
            return False


if __name__ == "__main__":
    import sys
    
    manager = HotspotManager()
    
    if len(sys.argv) < 2:
        print("Usage: python3 linux_hotspot_manager.py [start|stop|restart|status|enable|disable]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        success = manager.start_hotspot()
        sys.exit(0 if success else 1)
    
    elif command == "stop":
        success = manager.stop_hotspot()
        sys.exit(0 if success else 1)
    
    elif command == "restart":
        success = manager.restart_hotspot()
        sys.exit(0 if success else 1)
    
    elif command == "status":
        status = manager.get_status()
        print("\n=== Hotspot Status ===")
        for key, value in status.items():
            print(f"{key}: {value}")
        sys.exit(0 if status.get("hotspot_active") else 1)
    
    elif command == "enable":
        success = manager.enable_on_boot()
        sys.exit(0 if success else 1)
    
    elif command == "disable":
        success = manager.disable_on_boot()
        sys.exit(0 if success else 1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
