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
        self.authenticated_ips = set()  # Track authenticated users
        self.hotspot_interface = "wlx782051ac644f"  # USB WiFi adapter
        self.internet_interface = "wlp0s20f3"  # Built-in WiFi
        self.hotspot_subnet = "192.168.50.0/24"
        self.flask_server_ip = "192.168.50.1"
        
    def setup_nat(self):
        """Enable IP forwarding and NAT for hotspot"""
        try:
            # Enable IP forwarding
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)
            
            # Flush existing NAT rules
            subprocess.run(['sudo', 'iptables', '-t', 'nat', '-F'], check=True)
            subprocess.run(['sudo', 'iptables', '-F'], check=True)

            # Create GLOBAL_BLOCKS chain if it doesn't exist
            try:
                subprocess.run(['sudo', 'iptables', '-N', 'GLOBAL_BLOCKS'], check=False)
            except:
                pass # Chain likely already exists
            
            # Flush GLOBAL_BLOCKS
            subprocess.run(['sudo', 'iptables', '-F', 'GLOBAL_BLOCKS'], check=True)

            # Insert GLOBAL_BLOCKS at the VERY TOP of FORWARD chain
            # This ensures that ANY blocked IP is dropped immediately,
            # BEFORE checking if the user is authenticated.
            subprocess.run(['sudo', 'iptables', '-I', 'FORWARD', '1', '-j', 'GLOBAL_BLOCKS'], check=True)
            
            # 🔒 FORCE LOCAL DNS: Block access to Google/Cloudflare DNS
            # This prevents users from bypassing dnsmasq by manually setting DNS to 8.8.8.8
            public_dns = ["8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"]
            for dns in public_dns:
                subprocess.run(['sudo', 'iptables', '-I', 'FORWARD', '1', '-d', dns, '-j', 'DROP'], check=False)
            logger.info("🔒 Blocking Public DNS (Forces Local Filtering)")

            # Set up NAT (masquerading)
            subprocess.run([
                'sudo', 'iptables', '-t', 'nat', '-A', 'POSTROUTING',
                '-o', self.internet_interface, '-j', 'MASQUERADE'
            ], check=True)
            
            # Allow established connections back (for authenticated users)
            subprocess.run([
                'sudo', 'iptables', '-A', 'FORWARD',
                '-i', self.internet_interface, '-o', self.hotspot_interface,
                '-m', 'state', '--state', 'RELATED,ESTABLISHED',
                '-j', 'ACCEPT'
            ], check=True)
            
            logger.info("NAT setup completed successfully (with GLOBAL_BLOCKS)")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to setup NAT: {e}")
            return False
    
    def resolve_domain_ips(self, domain: str) -> Set[str]:
        """Resolve all IP addresses for a domain using multiple methods"""
        ips = set()
        try:
            # Remove protocol if present
            domain = domain.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Method 1: socket.getaddrinfo (Standard)
            try:
                addr_info = socket.getaddrinfo(domain, None)
                for info in addr_info:
                    ip = info[4][0]
                    if ':' not in ip:  # IPv4 only for now
                        ips.add(ip)
            except Exception:
                pass

            # Method 2: System 'dig' command (More reliable for multiple A records)
            try:
                result = subprocess.run(['dig', '+short', domain], capture_output=True, text=True, timeout=2)
                for line in result.stdout.splitlines():
                    ip = line.strip()
                    if ip and ':' not in ip and ip[0].isdigit():
                        ips.add(ip)
            except Exception:
                pass
            
            # Method 3: 'nslookup' as backup
            if not ips:
                try:
                    result = subprocess.run(['nslookup', domain], capture_output=True, text=True, timeout=2)
                    for line in result.stdout.splitlines():
                        if 'Address: ' in line:
                            parts = line.split('Address: ')
                            if len(parts) > 1:
                                ip = parts[1].strip()
                                if ':' not in ip and not ip.startswith('127.'): # Ignore blocks/loopback
                                    ips.add(ip)
                except Exception:
                    pass

            logger.info(f"Resolved {domain} to IPs: {ips}")
        except Exception as e:
            logger.error(f"Error resolving {domain}: {e}")
        
        return ips
    
    def block_ip(self, ip: str):
        """Block a specific IP address using iptables"""
        try:
            # Add to GLOBAL_BLOCKS chain
            # We use -A (Append) because the chain itself is already at the top of FORWARD
            subprocess.run([
                'sudo', 'iptables', '-A', 'GLOBAL_BLOCKS',
                '-d', ip,
                '-j', 'DROP'
            ], check=True)
            
            # Also block HTTPS port specifically just in case (TCP)
            subprocess.run([
                'sudo', 'iptables', '-A', 'GLOBAL_BLOCKS',
                '-d', ip, '-p', 'tcp', '--dport', '443',
                '-j', 'DROP'
            ], check=True)

            # Block QUIC (UDP 443) - Critical for modern sites/apps
            subprocess.run([
                'sudo', 'iptables', '-A', 'GLOBAL_BLOCKS',
                '-d', ip, '-p', 'udp', '--dport', '443',
                '-j', 'DROP'
            ], check=True)
            
            self.blocked_ips.add(ip)
            logger.info(f"🚫 Blocked IP: {ip} (in GLOBAL_BLOCKS)")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to block IP {ip}: {e}")
            return False
    
    def unblock_ip(self, ip: str):
        """Unblock a specific IP address"""
        try:
            # Remove from GLOBAL_BLOCKS
            subprocess.run([
                'sudo', 'iptables', '-D', 'GLOBAL_BLOCKS',
                '-d', ip,
                '-j', 'DROP'
            ], check=False)
            
            subprocess.run([
                'sudo', 'iptables', '-D', 'GLOBAL_BLOCKS',
                '-d', ip, '-p', 'tcp', '--dport', '443',
                '-j', 'DROP'
            ], check=False)

            subprocess.run([
                'sudo', 'iptables', '-D', 'GLOBAL_BLOCKS',
                '-d', ip, '-p', 'udp', '--dport', '443',
                '-j', 'DROP'
            ], check=False)
            
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
            logger.info(f"✅ Unblocked IP: {ip}")
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
        """Clear all existing filter rules"""
        try:
            # Flush GLOBAL_BLOCKS chain
            subprocess.run(['sudo', 'iptables', '-F', 'GLOBAL_BLOCKS'], check=True)
            
            self.blocked_ips.clear()
            logger.info("Cleared all filter rules (flushed GLOBAL_BLOCKS)")
            return True
        except Exception as e:
            logger.error(f"Failed to clear filter rules: {e}")
            # If chain doesn't exist, try creating it
            try:
                subprocess.run(['sudo', 'iptables', '-N', 'GLOBAL_BLOCKS'], check=False)
                subprocess.run(['sudo', 'iptables', '-I', 'FORWARD', '1', '-j', 'GLOBAL_BLOCKS'], check=False)
            except:
                pass
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
    
    def reset_firewall(self):
        """Reset all firewall rules to default state (block everything)"""
        try:
            # Flus filter rules
            subprocess.run(['sudo', 'iptables', '-F'], check=True)
            subprocess.run(['sudo', 'iptables', '-X'], check=True)
            
            # Flush GLOBAL_BLOCKS if exists
            try:
                subprocess.run(['sudo', 'iptables', '-F', 'GLOBAL_BLOCKS'], check=False)
                subprocess.run(['sudo', 'iptables', '-X', 'GLOBAL_BLOCKS'], check=False)
            except:
                pass

            # Flush NAT rules
            subprocess.run(['sudo', 'iptables', '-t', 'nat', '-F'], check=True)
            subprocess.run(['sudo', 'iptables', '-t', 'nat', '-X'], check=True)
            
            # Default policies
            subprocess.run(['sudo', 'iptables', '-P', 'INPUT', 'ACCEPT'], check=True)
            subprocess.run(['sudo', 'iptables', '-P', 'FORWARD', 'DROP'], check=True)
            subprocess.run(['sudo', 'iptables', '-P', 'OUTPUT', 'ACCEPT'], check=True)
            
            self.blocked_ips.clear()
            self.authenticated_ips.clear()
            logger.info("✅ Firewall reset to default state")
            return True
        except Exception as e:
            logger.error(f"Failed to reset firewall: {e}")
            return False

    def setup_captive_portal_redirection(self):
        """Redirect unauthenticated HTTP traffic to Flask server"""
        try:
            # Allow DNS requests to local dnsmasq
            subprocess.run([
                'sudo', 'iptables', '-t', 'nat', '-A', 'PREROUTING',
                '-i', self.hotspot_interface,
                '-p', 'udp', '--dport', '53',
                '-j', 'ACCEPT'
            ], check=True)
            
            # Redirect HTTP (80) to Flask (5000)
            subprocess.run([
                'sudo', 'iptables', '-t', 'nat', '-A', 'PREROUTING',
                '-i', self.hotspot_interface,
                '-p', 'tcp', '--dport', '80',
                '-j', 'REDIRECT', '--to-port', '5000'
            ], check=True)
            
            # Note: We cannot easily redirect HTTPS (443) without SSL errors
            # Using DNS spoofing (dnsmasq) is preferred for blocking HTTPS domains
            
            logger.info("✅ Captive portal redirection configured")
            return True
        except Exception as e:
            logger.error(f"Failed to setup redirection: {e}")
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

def setup_captive_portal():
    """Setup captive portal - block all traffic except to Flask server for unauthenticated users"""
    manager = get_firewall_manager()
    
    try:
        # Setup NAT first
        manager.setup_nat()
        
        # Setup Redirection to Captive Portal
        manager.setup_captive_portal_redirection()
        
        # Allow DNS queries (FORWARD chain - required for captive portal detection)
        subprocess.run([
            'sudo', 'iptables', '-A', 'FORWARD',
            '-i', manager.hotspot_interface,
            '-p', 'udp', '--dport', '53',
            '-j', 'ACCEPT'
        ], check=True)
        
        # Allow DNS responses
        subprocess.run([
            'sudo', 'iptables', '-A', 'FORWARD',
            '-i', manager.hotspot_interface,
            '-p', 'udp', '--sport', '53',
            '-j', 'ACCEPT'
        ], check=True)
        
        # Allow DHCP
        subprocess.run([
            'sudo', 'iptables', '-A', 'FORWARD',
            '-i', manager.hotspot_interface,
            '-p', 'udp', '--dport', '67:68',
            '-j', 'ACCEPT'
        ], check=True)
        
        # Allow traffic to Flask server (port 5000) on hotspot IP - INPUT chain
        subprocess.run([
            'sudo', 'iptables', '-I', 'INPUT', '1',
            '-i', manager.hotspot_interface,
            '-p', 'tcp', '--dport', '5000',
            '-j', 'ACCEPT'
        ], check=True)
        
        # ⭐ CRITICAL: Block all internet traffic from unauthenticated users
        # This blocks ALL apps (Instagram, Snapchat, etc.) and websites before login
        # Authenticated users bypass this via rules inserted by allow_authenticated_user()
        subprocess.run([
            'sudo', 'iptables', '-A', 'FORWARD',
            '-i', manager.hotspot_interface,
            '-o', manager.internet_interface,
            '-j', 'DROP'
        ], check=True)
        
        manager.update_from_database()

        logger.info("✅ Captive portal firewall configured - all internet traffic blocked before auth")
        return True
    except Exception as e:
        logger.error(f"Failed to setup captive portal: {e}")
        return False

def allow_authenticated_user(client_ip: str):
    """Allow internet access for authenticated user"""
    manager = get_firewall_manager()
    
    try:
        # ⭐ INSERT at position 2 (After GLOBAL_BLOCKS but before DROP rules)
        # Position 1 is strictly for GLOBAL_BLOCKS
        subprocess.run([
            'sudo', 'iptables', '-I', 'FORWARD', '2',
            '-s', client_ip,
            '-i', manager.hotspot_interface,
            '-o', manager.internet_interface,
            '-j', 'ACCEPT'
        ], check=True)
        
        manager.authenticated_ips.add(client_ip)
        logger.info(f"✅ Allowed internet access for {client_ip}")
        return True
    except Exception as e:
        logger.error(f"Failed to allow user {client_ip}: {e}")
        return False

def block_authenticated_user(client_ip: str):
    """Remove internet access for user (on logout)"""
    manager = get_firewall_manager()
    
    try:
        # Remove the ACCEPT rule for this IP
        subprocess.run([
            'sudo', 'iptables', '-D', 'FORWARD',
            '-s', client_ip,
            '-i', manager.hotspot_interface,
            '-o', manager.internet_interface,
            '-j', 'ACCEPT'
        ], check=False)  # Don't fail if rule doesn't exist
        
        if client_ip in manager.authenticated_ips:
            manager.authenticated_ips.remove(client_ip)
        logger.info(f"✅ Blocked internet access for {client_ip}")
        return True
    except Exception as e:
        logger.error(f"Failed to block user {client_ip}: {e}")
        return False

def setup_hotspot_firewall():
    """Initial setup for hotspot firewall with captive portal"""
    # This MUST call setup_captive_portal() to ensure the DROP rules are applied!
    setup_captive_portal()
    
    manager = get_firewall_manager()
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
