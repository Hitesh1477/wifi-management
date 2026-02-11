#!/usr/bin/env python3
"""
Linux Firewall Manager - iptables-based web filtering
Integrates with Flask backend for dynamic filtering
"""

import subprocess
import socket
import logging
from typing import List, Dict, Set
from db import web_filter_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinuxFirewallManager:
    def __init__(self):
        self.blocked_ips = set()
        self.hotspot_interface = "wlan0"
        self.internet_interface = "eth0"  # Change to your internet interface
        
    def setup_nat(self):
        """Enable IP forwarding and NAT for hotspot"""
        try:
            # Enable IP forwarding
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)
            
            # Flush existing NAT rules
            subprocess.run(['sudo', 'iptables', '-t', 'nat', '-F'], check=True)
            subprocess.run(['sudo', 'iptables', '-F'], check=True)
            
            # Set up NAT (masquerading)
            subprocess.run([
                'sudo', 'iptables', '-t', 'nat', '-A', 'POSTROUTING',
                '-o', self.internet_interface, '-j', 'MASQUERADE'
            ], check=True)
            
            # Allow forwarding from hotspot to internet
            subprocess.run([
                'sudo', 'iptables', '-A', 'FORWARD',
                '-i', self.hotspot_interface, '-o', self.internet_interface,
                '-j', 'ACCEPT'
            ], check=True)
            
            # Allow established connections back
            subprocess.run([
                'sudo', 'iptables', '-A', 'FORWARD',
                '-i', self.internet_interface, '-o', self.hotspot_interface,
                '-m', 'state', '--state', 'RELATED,ESTABLISHED',
                '-j', 'ACCEPT'
            ], check=True)
            
            logger.info("NAT setup completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup NAT: {e}")
            return False
    
    def resolve_domain_ips(self, domain: str) -> Set[str]:
        """Resolve all IP addresses for a domain"""
        ips = set()
        try:
            # Remove protocol if present
            domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Get IP addresses
            addr_info = socket.getaddrinfo(domain, None)
            for info in addr_info:
                ip = info[4][0]
                if ':' not in ip:  # IPv4 only for now
                    ips.add(ip)
            
            logger.info(f"Resolved {domain} to IPs: {ips}")
        except socket.gaierror as e:
            logger.warning(f"Could not resolve {domain}: {e}")
        except Exception as e:
            logger.error(f"Error resolving {domain}: {e}")
        
        return ips
    
    def block_ip(self, ip: str):
        """Block a specific IP address using iptables"""
        try:
            # Block outgoing traffic to this IP
            subprocess.run([
                'sudo', 'iptables', '-A', 'FORWARD',
                '-s', '192.168.50.0/24',  # Hotspot subnet
                '-d', ip,
                '-j', 'DROP'
            ], check=True)
            
            self.blocked_ips.add(ip)
            logger.info(f"Blocked IP: {ip}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to block IP {ip}: {e}")
            return False
    
    def unblock_ip(self, ip: str):
        """Unblock a specific IP address"""
        try:
            # Remove the DROP rule
            subprocess.run([
                'sudo', 'iptables', '-D', 'FORWARD',
                '-s', '192.168.50.0/24',
                '-d', ip,
                '-j', 'DROP'
            ], check=False)  # Don't fail if rule doesn't exist
            
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
            logger.info(f"Unblocked IP: {ip}")
            return True
        except Exception as e:
            logger.error(f"Failed to unblock IP {ip}: {e}")
            return False
    
    def block_domain(self, domain: str):
        """Block all IPs for a domain"""
        ips = self.resolve_domain_ips(domain)
        for ip in ips:
            self.block_ip(ip)
    
    def unblock_domain(self, domain: str):
        """Unblock all IPs for a domain"""
        ips = self.resolve_domain_ips(domain)
        for ip in ips:
            self.unblock_ip(ip)
    
    def clear_filter_rules(self):
        """Clear all existing filter rules (but keep NAT)"""
        try:
            # Get all FORWARD rules with DROP action
            result = subprocess.run(
                ['sudo', 'iptables', '-L', 'FORWARD', '--line-numbers', '-n'],
                capture_output=True, text=True
            )
            
            # Delete DROP rules (in reverse order to maintain line numbers)
            lines = result.stdout.split('\n')
            drop_lines = []
            for line in lines:
                if 'DROP' in line and line.strip():
                    parts = line.split()
                    if parts and parts[0].isdigit():
                        drop_lines.append(int(parts[0]))
            
            for line_num in sorted(drop_lines, reverse=True):
                subprocess.run(
                    ['sudo', 'iptables', '-D', 'FORWARD', str(line_num)],
                    check=False
                )
            
            self.blocked_ips.clear()
            logger.info("Cleared all filter rules")
            return True
        except Exception as e:
            logger.error(f"Failed to clear filter rules: {e}")
            return False
    
    def update_from_database(self):
        """Update firewall rules based on MongoDB configuration"""
        try:
            config = web_filter_collection.find_one({"type": "config"})
            if not config:
                logger.warning("No filter configuration found in database")
                return False
            
            # Clear existing rules
            self.clear_filter_rules()
            
            # Get all domains to block
            domains_to_block = set()
            
            # Add manually blocked sites
            if "manual_blocks" in config:
                domains_to_block.update(config["manual_blocks"])
            
            # Add active category sites
            if "categories" in config:
                for category, details in config["categories"].items():
                    if details.get("active", False):
                        domains_to_block.update(details.get("sites", []))
            
            # Block all domains
            logger.info(f"Blocking {len(domains_to_block)} domains")
            for domain in domains_to_block:
                self.block_domain(domain)
            
            logger.info("Firewall rules updated from database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update from database: {e}")
            return False
    
    def save_rules(self):
        """Save iptables rules to persist across reboots"""
        try:
            subprocess.run(['sudo', 'netfilter-persistent', 'save'], check=True)
            logger.info("Firewall rules saved")
            return True
        except subprocess.CalledProcessError:
            # Try alternative method
            try:
                subprocess.run(['sudo', 'iptables-save', '>', '/etc/iptables/rules.v4'], 
                             shell=True, check=True)
                logger.info("Firewall rules saved (alternative method)")
                return True
            except Exception as e:
                logger.error(f"Failed to save rules: {e}")
                return False
    
    def get_blocked_ips_count(self) -> Dict:
        """Get statistics about blocked IPs"""
        return {
            "total_blocked_ips": len(self.blocked_ips),
            "blocked_ips": list(self.blocked_ips)
        }


# Singleton instance
_firewall_manager = None

def get_firewall_manager() -> LinuxFirewallManager:
    """Get or create firewall manager instance"""
    global _firewall_manager
    if _firewall_manager is None:
        _firewall_manager = LinuxFirewallManager()
    return _firewall_manager

def update_firewall_rules():
    """Update firewall rules from database (called by Flask routes)"""
    manager = get_firewall_manager()
    success = manager.update_from_database()
    if success:
        manager.save_rules()
    return success

def setup_hotspot_firewall():
    """Initial setup for hotspot firewall"""
    manager = get_firewall_manager()
    manager.setup_nat()
    manager.update_from_database()
    manager.save_rules()


if __name__ == "__main__":
    # Test the firewall manager
    print("Testing Linux Firewall Manager...")
    manager = LinuxFirewallManager()
    
    # Setup NAT
    print("\n1. Setting up NAT...")
    manager.setup_nat()
    
    # Update from database
    print("\n2. Updating rules from database...")
    manager.update_from_database()
    
    # Show stats
    print("\n3. Statistics:")
    stats = manager.get_blocked_ips_count()
    print(f"   Total blocked IPs: {stats['total_blocked_ips']}")
    
    # Save rules
    print("\n4. Saving rules...")
    manager.save_rules()
    
    print("\nDone!")
