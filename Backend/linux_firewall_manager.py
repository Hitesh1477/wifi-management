#!/usr/bin/env python3
"""
Linux Firewall Manager - iptables-based web filtering
Integrates with Flask backend for dynamic filtering
"""

import subprocess
import socket
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Optional
from db import web_filter_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_DNS_SERVERS = ("8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1")
GLOBAL_BLOCKS_CHAIN = "GLOBAL_BLOCKS"
HOTSPOT_FORWARD_CHAIN = "WIFI_MGMT_FORWARD"
HOTSPOT_AUTH_CHAIN = "WIFI_MGMT_AUTH"
HOTSPOT_PREROUTING_CHAIN = "WIFI_MGMT_PREROUTING"
HOTSPOT_USAGE_CHAIN = "WIFI_MGMT_USAGE"

USAGE_COMMENT_UPLOAD_PREFIX = "wifi_usage_up:"
USAGE_COMMENT_DOWNLOAD_PREFIX = "wifi_usage_down:"


def _iptables_run(args: List[str], table: str = "filter", check: bool = False) -> subprocess.CompletedProcess:
    command = ["sudo", "iptables"]
    if table != "filter":
        command.extend(["-t", table])
    command.extend(args)
    return subprocess.run(command, capture_output=True, text=True, check=check)


def _iptables_rule_exists(chain: str, rule_args: List[str], table: str = "filter") -> bool:
    result = _iptables_run(["-C", chain] + rule_args, table=table, check=False)
    return result.returncode == 0


def _ensure_chain(chain: str, table: str = "filter") -> None:
    _iptables_run(["-N", chain], table=table, check=False)


def _flush_chain(chain: str, table: str = "filter") -> None:
    _iptables_run(["-F", chain], table=table, check=False)


def _ensure_rule(chain: str, rule_args: List[str], table: str = "filter", insert_position: Optional[int] = None) -> None:
    if _iptables_rule_exists(chain, rule_args, table=table):
        return

    if insert_position is None:
        _iptables_run(["-A", chain] + rule_args, table=table, check=True)
        return

    _iptables_run(["-I", chain, str(insert_position)] + rule_args, table=table, check=True)


def _delete_rule_all(chain: str, rule_args: List[str], table: str = "filter") -> None:
    while True:
        result = _iptables_run(["-D", chain] + rule_args, table=table, check=False)
        if result.returncode != 0:
            break


def _usage_upload_comment(client_ip: str) -> str:
    return f"{USAGE_COMMENT_UPLOAD_PREFIX}{client_ip}"


def _usage_download_comment(client_ip: str) -> str:
    return f"{USAGE_COMMENT_DOWNLOAD_PREFIX}{client_ip}"


def _usage_upload_rule_args(client_ip: str, hotspot_interface: str, internet_interface: str) -> List[str]:
    return [
        "-s",
        client_ip,
        "-i",
        hotspot_interface,
        "-o",
        internet_interface,
        "-m",
        "comment",
        "--comment",
        _usage_upload_comment(client_ip),
        "-j",
        "RETURN",
    ]


def _usage_download_rule_args(client_ip: str, hotspot_interface: str, internet_interface: str) -> List[str]:
    return [
        "-d",
        client_ip,
        "-i",
        internet_interface,
        "-o",
        hotspot_interface,
        "-m",
        "conntrack",
        "--ctstate",
        "RELATED,ESTABLISHED",
        "-m",
        "comment",
        "--comment",
        _usage_download_comment(client_ip),
        "-j",
        "RETURN",
    ]


def _run_ip_command(args: List[str]) -> str:
    try:
        result = subprocess.run(
            ["ip"] + args,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return ""
        return (result.stdout or "").strip()
    except Exception:
        return ""


def _extract_route_device(route_output: str) -> Optional[str]:
    for line in route_output.splitlines():
        parts = line.split()
        if "dev" not in parts:
            continue
        dev_index = parts.index("dev")
        if dev_index + 1 < len(parts):
            return parts[dev_index + 1].strip()
    return None


def _detect_default_route_interface() -> Optional[str]:
    return _extract_route_device(_run_ip_command(["-4", "route", "show", "default"]))


def _detect_interface_for_subnet(subnet: str) -> Optional[str]:
    if not subnet:
        return None
    return _extract_route_device(_run_ip_command(["-4", "route", "show", subnet]))


def _detect_interface_by_ipv4_prefix(prefix: str) -> Optional[str]:
    if not prefix:
        return None

    output = _run_ip_command(["-o", "-4", "addr", "show"])
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 4 or parts[2] != "inet":
            continue
        iface = parts[1].strip()
        ip_addr = parts[3].split("/", 1)[0].strip()
        if ip_addr.startswith(prefix):
            return iface
    return None


def _prefix_from_gateway_ip(gateway_ip: str) -> str:
    octets = str(gateway_ip or "").strip().split(".")
    if len(octets) == 4:
        return ".".join(octets[:3]) + "."
    return "192.168.50."

class LinuxFirewallManager:
    def __init__(self):
        self.blocked_ips = set()
        self.authenticated_ips = set()  # Track authenticated users
        self.hotspot_subnet = os.environ.get("HOTSPOT_SUBNET", "192.168.50.0/24")
        self.flask_server_ip = os.environ.get("HOTSPOT_GATEWAY_IP", "192.168.50.1")

        hotspot_prefix = _prefix_from_gateway_ip(self.flask_server_ip)
        configured_hotspot = (os.environ.get("HOTSPOT_INTERFACE") or "").strip()
        detected_hotspot = (
            configured_hotspot
            or _detect_interface_for_subnet(self.hotspot_subnet)
            or _detect_interface_by_ipv4_prefix(hotspot_prefix)
        )
        self.hotspot_interface = detected_hotspot or "wlx782051ac644f"

        configured_internet = (os.environ.get("INTERNET_INTERFACE") or "").strip()
        detected_internet = configured_internet or _detect_default_route_interface()
        if detected_internet == self.hotspot_interface:
            detected_internet = None
        self.internet_interface = detected_internet or "wlp0s20f3"

        logger.info(
            "Firewall interfaces: hotspot=%s internet=%s subnet=%s",
            self.hotspot_interface,
            self.internet_interface,
            self.hotspot_subnet,
        )

    def _cleanup_legacy_rules(self):
        """Remove broad legacy rules that could impact host networking."""
        _delete_rule_all("FORWARD", ["-j", GLOBAL_BLOCKS_CHAIN])
        _delete_rule_all("FORWARD", ["-i", self.hotspot_interface, "-j", "DROP"])
        _delete_rule_all(
            "FORWARD",
            ["-o", self.hotspot_interface, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
        )

        _delete_rule_all(
            "PREROUTING",
            ["-i", self.hotspot_interface, "-p", "udp", "--dport", "53", "-j", "ACCEPT"],
            table="nat",
        )
        _delete_rule_all(
            "PREROUTING",
            ["-i", self.hotspot_interface, "-p", "tcp", "--dport", "80", "-j", "REDIRECT", "--to-port", "5000"],
            table="nat",
        )
        _delete_rule_all(
            "POSTROUTING",
            ["-o", self.internet_interface, "-j", "MASQUERADE"],
            table="nat",
        )

        _delete_rule_all("FORWARD", ["-i", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN])
        _delete_rule_all("FORWARD", ["-o", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN])

        for dns in PUBLIC_DNS_SERVERS:
            _delete_rule_all("FORWARD", ["-d", dns, "-j", "DROP"])
            _delete_rule_all("FORWARD", ["-d", dns, "-p", "udp", "--dport", "443", "-j", "DROP"])

    def _ensure_forward_usage_order(self):
        """Ensure usage-accounting hooks run before ACCEPT rules in FORWARD."""
        _ensure_chain(GLOBAL_BLOCKS_CHAIN)
        _ensure_chain(HOTSPOT_FORWARD_CHAIN)
        _ensure_chain(HOTSPOT_AUTH_CHAIN)
        _ensure_chain(HOTSPOT_USAGE_CHAIN)

        _ensure_rule(HOTSPOT_USAGE_CHAIN, ["-j", "RETURN"])

        _delete_rule_all("FORWARD", ["-i", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN])
        _delete_rule_all("FORWARD", ["-o", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN])
        _delete_rule_all("FORWARD", ["-i", self.hotspot_interface, "-j", HOTSPOT_FORWARD_CHAIN])
        _delete_rule_all(
            "FORWARD",
            [
                "-i",
                self.internet_interface,
                "-o",
                self.hotspot_interface,
                "-m",
                "conntrack",
                "--ctstate",
                "RELATED,ESTABLISHED",
                "-j",
                "ACCEPT",
            ],
        )

        # Insert in reverse order so final chain order is:
        # 1) usage -o hotspot, 2) usage -i hotspot,
        # 3) established return ACCEPT, 4) hotspot forward chain.
        _ensure_rule(
            "FORWARD",
            ["-i", self.hotspot_interface, "-j", HOTSPOT_FORWARD_CHAIN],
            insert_position=1,
        )
        _ensure_rule(
            "FORWARD",
            [
                "-i",
                self.internet_interface,
                "-o",
                self.hotspot_interface,
                "-m",
                "conntrack",
                "--ctstate",
                "RELATED,ESTABLISHED",
                "-j",
                "ACCEPT",
            ],
            insert_position=1,
        )
        _ensure_rule(
            "FORWARD",
            ["-i", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN],
            insert_position=1,
        )
        _ensure_rule(
            "FORWARD",
            ["-o", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN],
            insert_position=1,
        )
        
    def setup_nat(self):
        """Enable IP forwarding and NAT for hotspot"""
        try:
            configured_hotspot = (os.environ.get("HOTSPOT_INTERFACE") or "").strip()
            configured_internet = (os.environ.get("INTERNET_INTERFACE") or "").strip()
            hotspot_prefix = _prefix_from_gateway_ip(self.flask_server_ip)

            detected_hotspot = (
                configured_hotspot
                or _detect_interface_for_subnet(self.hotspot_subnet)
                or _detect_interface_by_ipv4_prefix(hotspot_prefix)
            )
            if detected_hotspot:
                self.hotspot_interface = detected_hotspot

            detected_internet = configured_internet or _detect_default_route_interface()
            if detected_internet and detected_internet != self.hotspot_interface:
                self.internet_interface = detected_internet

            logger.info(
                "Applying NAT on hotspot=%s internet=%s",
                self.hotspot_interface,
                self.internet_interface,
            )

            # Enable IP forwarding
            subprocess.run(['sudo', 'sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)

            # Remove broad legacy rules left by older versions.
            self._cleanup_legacy_rules()

            # Create/refresh dedicated chains used by this project only.
            _ensure_chain(GLOBAL_BLOCKS_CHAIN)
            _ensure_chain(HOTSPOT_FORWARD_CHAIN)
            _ensure_chain(HOTSPOT_AUTH_CHAIN)
            _ensure_chain(HOTSPOT_USAGE_CHAIN)

            _flush_chain(GLOBAL_BLOCKS_CHAIN)
            _flush_chain(HOTSPOT_FORWARD_CHAIN)
            _flush_chain(HOTSPOT_AUTH_CHAIN)
            _flush_chain(HOTSPOT_USAGE_CHAIN)

            # Default behavior for usage chain is pass-through.
            _ensure_rule(HOTSPOT_USAGE_CHAIN, ["-j", "RETURN"])

            # Reset hooks so usage accounting runs before ACCEPT decisions.
            self._ensure_forward_usage_order()

            # NAT only hotspot subnet traffic.
            _ensure_rule(
                "POSTROUTING",
                ["-s", self.hotspot_subnet, "-o", self.internet_interface, "-j", "MASQUERADE"],
                table="nat",
            )

            # Chain order: blocklist -> DNS bypass protection -> authenticated users -> drop.
            _ensure_rule(HOTSPOT_FORWARD_CHAIN, ["-j", GLOBAL_BLOCKS_CHAIN])

            for dns in PUBLIC_DNS_SERVERS:
                _ensure_rule(
                    HOTSPOT_FORWARD_CHAIN,
                    ["-d", dns, "-p", "udp", "--dport", "53", "-j", "DROP"],
                )
                _ensure_rule(
                    HOTSPOT_FORWARD_CHAIN,
                    ["-d", dns, "-p", "tcp", "--dport", "53", "-j", "DROP"],
                )

            _ensure_rule(HOTSPOT_FORWARD_CHAIN, ["-j", HOTSPOT_AUTH_CHAIN])
            _ensure_rule(HOTSPOT_FORWARD_CHAIN, ["-j", "DROP"])

            logger.info("NAT, captive filtering, and usage accounting chains configured")
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
                    ip_text = str(info[4][0])
                    if ':' not in ip_text:  # IPv4 only for now
                        ips.add(ip_text)
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
        ip = str(ip or "").strip()
        if not ip:
            return False

        try:
            # Ensure idempotent rules (avoid duplicates in GLOBAL_BLOCKS).
            _ensure_rule(GLOBAL_BLOCKS_CHAIN, ['-d', ip, '-j', 'DROP'])
            _ensure_rule(GLOBAL_BLOCKS_CHAIN, ['-d', ip, '-p', 'tcp', '--dport', '443', '-j', 'DROP'])
            _ensure_rule(GLOBAL_BLOCKS_CHAIN, ['-d', ip, '-p', 'udp', '--dport', '443', '-j', 'DROP'])
            
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
                'sudo', 'iptables', '-D', GLOBAL_BLOCKS_CHAIN,
                '-d', ip,
                '-j', 'DROP'
            ], check=False)
            
            subprocess.run([
                'sudo', 'iptables', '-D', GLOBAL_BLOCKS_CHAIN,
                '-d', ip, '-p', 'tcp', '--dport', '443',
                '-j', 'DROP'
            ], check=False)

            subprocess.run([
                'sudo', 'iptables', '-D', GLOBAL_BLOCKS_CHAIN,
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
            subprocess.run(['sudo', 'iptables', '-F', GLOBAL_BLOCKS_CHAIN], check=True)
            
            self.blocked_ips.clear()
            logger.info("Cleared all filter rules (flushed GLOBAL_BLOCKS)")
            return True
        except Exception as e:
            logger.error(f"Failed to clear filter rules: {e}")
            # If chain doesn't exist, try creating it
            try:
                _ensure_chain(GLOBAL_BLOCKS_CHAIN)
                _ensure_chain(HOTSPOT_FORWARD_CHAIN)
                _ensure_rule(HOTSPOT_FORWARD_CHAIN, ['-j', GLOBAL_BLOCKS_CHAIN])
            except:
                pass
            return False
    
    def update_from_database(self):
        """Update firewall rules based on MongoDB configuration"""
        try:
            # Keep FORWARD hooks in the correct order for usage accounting.
            self._ensure_forward_usage_order()

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
            
            # Resolve all domains in parallel to reduce apply latency.
            domain_to_ips: Dict[str, Set[str]] = {}
            logger.info(f"Blocking {len(domains_to_block)} domains")

            if domains_to_block:
                max_workers = min(16, max(4, len(domains_to_block)))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_domain = {
                        executor.submit(self.resolve_domain_ips, domain): domain
                        for domain in domains_to_block
                    }

                    for future in as_completed(future_to_domain):
                        domain = future_to_domain[future]
                        try:
                            domain_to_ips[domain] = future.result() or set()
                        except Exception as e:
                            logger.error(f"Error resolving {domain}: {e}")
                            domain_to_ips[domain] = set()

            # Add each IP once even if multiple domains resolve to it.
            unique_ips = set()
            for ips in domain_to_ips.values():
                unique_ips.update(ips)

            logger.info(f"Applying blocks for {len(unique_ips)} unique IPs")
            for ip in sorted(unique_ips):
                self.block_ip(ip)
            
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
                subprocess.run(['sudo', 'mkdir', '-p', '/etc/iptables'], check=True)
                subprocess.run(
                    ['sudo', 'sh', '-c', 'iptables-save > /etc/iptables/rules.v4'],
                    check=True,
                )
                logger.info("Firewall rules saved (alternative method)")
                return True
            except Exception as e:
                logger.error(f"Failed to save rules: {e}")
                return False
    
    def reset_firewall(self):
        """Remove WiFi-management rules without flushing global firewall state."""
        try:
            # Remove hook rules from built-in chains.
            _delete_rule_all("FORWARD", ["-i", self.hotspot_interface, "-j", HOTSPOT_FORWARD_CHAIN])
            _delete_rule_all("FORWARD", ["-i", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN])
            _delete_rule_all("FORWARD", ["-o", self.hotspot_interface, "-j", HOTSPOT_USAGE_CHAIN])
            _delete_rule_all(
                "FORWARD",
                [
                    "-i",
                    self.internet_interface,
                    "-o",
                    self.hotspot_interface,
                    "-m",
                    "conntrack",
                    "--ctstate",
                    "RELATED,ESTABLISHED",
                    "-j",
                    "ACCEPT",
                ],
            )

            _delete_rule_all(
                "PREROUTING",
                [
                    "-i",
                    self.hotspot_interface,
                    "-p",
                    "tcp",
                    "--dport",
                    "80",
                    "-j",
                    HOTSPOT_PREROUTING_CHAIN,
                ],
                table="nat",
            )
            _delete_rule_all(
                "POSTROUTING",
                ["-s", self.hotspot_subnet, "-o", self.internet_interface, "-j", "MASQUERADE"],
                table="nat",
            )

            # Remove helper INPUT allowances added for hotspot services.
            _delete_rule_all("INPUT", ["-i", self.hotspot_interface, "-p", "tcp", "--dport", "5000", "-j", "ACCEPT"])
            _delete_rule_all("INPUT", ["-i", self.hotspot_interface, "-p", "udp", "--dport", "67", "-j", "ACCEPT"])
            _delete_rule_all("INPUT", ["-i", self.hotspot_interface, "-p", "udp", "--dport", "53", "-j", "ACCEPT"])
            _delete_rule_all("INPUT", ["-i", self.hotspot_interface, "-p", "tcp", "--dport", "53", "-j", "ACCEPT"])

            # Remove old broad rules from legacy versions.
            self._cleanup_legacy_rules()

            # Flush and delete project chains.
            for chain in (HOTSPOT_AUTH_CHAIN, HOTSPOT_FORWARD_CHAIN, HOTSPOT_USAGE_CHAIN, GLOBAL_BLOCKS_CHAIN):
                _flush_chain(chain)
                _iptables_run(["-X", chain], check=False)

            _flush_chain(HOTSPOT_PREROUTING_CHAIN, table="nat")
            _iptables_run(["-X", HOTSPOT_PREROUTING_CHAIN], table="nat", check=False)

            self.blocked_ips.clear()
            self.authenticated_ips.clear()
            logger.info("✅ WiFi-management firewall rules removed safely")
            return True
        except Exception as e:
            logger.error(f"Failed to reset firewall: {e}")
            return False

    def setup_captive_portal_redirection(self):
        """Redirect unauthenticated HTTP traffic to Flask server"""
        try:
            _ensure_chain(HOTSPOT_PREROUTING_CHAIN, table="nat")
            _flush_chain(HOTSPOT_PREROUTING_CHAIN, table="nat")

            # Authenticated users bypass the redirect chain.
            for client_ip in sorted(self.authenticated_ips):
                _ensure_rule(
                    HOTSPOT_PREROUTING_CHAIN,
                    ["-s", client_ip, "-j", "RETURN"],
                    table="nat",
                )

            # Requests explicitly targeting the gateway should not be redirected.
            _ensure_rule(
                HOTSPOT_PREROUTING_CHAIN,
                ["-d", self.flask_server_ip, "-j", "RETURN"],
                table="nat",
            )

            # Redirect unauthenticated HTTP traffic to Flask login.
            _ensure_rule(
                HOTSPOT_PREROUTING_CHAIN,
                ["-j", "REDIRECT", "--to-port", "5000"],
                table="nat",
            )

            _delete_rule_all(
                "PREROUTING",
                [
                    "-i",
                    self.hotspot_interface,
                    "-p",
                    "tcp",
                    "--dport",
                    "80",
                    "-j",
                    HOTSPOT_PREROUTING_CHAIN,
                ],
                table="nat",
            )
            _ensure_rule(
                "PREROUTING",
                [
                    "-i",
                    self.hotspot_interface,
                    "-p",
                    "tcp",
                    "--dport",
                    "80",
                    "-j",
                    HOTSPOT_PREROUTING_CHAIN,
                ],
                table="nat",
                insert_position=1,
            )

            # Note: HTTPS interception is intentionally not attempted.
            logger.info("✅ Captive portal redirection configured (HTTP only)")
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

    def get_usage_counters_by_ip(self) -> Dict[str, Dict[str, int]]:
        """Read per-client upload/download byte counters from usage chain."""
        usage: Dict[str, Dict[str, int]] = {}

        def _set_usage(client_ip: str, direction: str, byte_count: int) -> None:
            ip_text = str(client_ip or "").strip()
            if not ip_text:
                return
            entry = usage.setdefault(ip_text, {"upload_bytes": 0, "download_bytes": 0, "total_bytes": 0})
            entry[direction] = max(0, int(byte_count))

        def _parse_iptables_save(output: str) -> bool:
            parsed = False
            chain_pattern = re.compile(
                rf"^\[(\d+):(\d+)\]\s+-A\s+{re.escape(HOTSPOT_USAGE_CHAIN)}\s+(.*)$"
            )

            for line in (output or "").splitlines():
                match = chain_pattern.match(line.strip())
                if not match:
                    continue

                byte_count = int(match.group(2))
                rule = match.group(3)

                if USAGE_COMMENT_UPLOAD_PREFIX in rule:
                    ip_match = re.search(r"-s\s+((?:\d{1,3}\.){3}\d{1,3})(?:/\d+)?", rule)
                    if not ip_match:
                        continue
                    _set_usage(ip_match.group(1), "upload_bytes", byte_count)
                    parsed = True
                    continue

                if USAGE_COMMENT_DOWNLOAD_PREFIX in rule:
                    ip_match = re.search(r"-d\s+((?:\d{1,3}\.){3}\d{1,3})(?:/\d+)?", rule)
                    if not ip_match:
                        continue
                    _set_usage(ip_match.group(1), "download_bytes", byte_count)
                    parsed = True

            return parsed

        def _parse_iptables_list(output: str) -> bool:
            parsed = False
            for line in (output or "").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("Chain ") or stripped.startswith("pkts "):
                    continue

                parts = stripped.split()
                if len(parts) < 9:
                    continue

                byte_text = parts[1]
                target = parts[2]
                source = parts[7]
                destination = parts[8]

                if target != "RETURN":
                    continue

                try:
                    byte_count = int(byte_text)
                except ValueError:
                    continue

                source_ip = source.split("/", 1)[0]
                destination_ip = destination.split("/", 1)[0]

                if source_ip != "0.0.0.0" and source_ip != "0.0.0.0/0":
                    _set_usage(source_ip, "upload_bytes", byte_count)
                    parsed = True
                    continue

                if destination_ip != "0.0.0.0" and destination_ip != "0.0.0.0/0":
                    _set_usage(destination_ip, "download_bytes", byte_count)
                    parsed = True

            return parsed

        command_candidates = [
            ["iptables-save", "-c"],
            ["sudo", "-n", "iptables-save", "-c"],
        ]

        parsed_any = False

        for command in command_candidates:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except Exception:
                continue

            if result.returncode != 0:
                continue

            if _parse_iptables_save(result.stdout):
                parsed_any = True
                break

        if not parsed_any:
            list_command_candidates = [
                ["iptables", "-L", HOTSPOT_USAGE_CHAIN, "-v", "-n", "-x"],
                ["sudo", "-n", "iptables", "-L", HOTSPOT_USAGE_CHAIN, "-v", "-n", "-x"],
            ]

            for command in list_command_candidates:
                try:
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                except Exception:
                    continue

                if result.returncode != 0:
                    continue

                if _parse_iptables_list(result.stdout):
                    parsed_any = True
                    break

        if not parsed_any:
            return usage

        for entry in usage.values():
            upload_bytes = max(0, int(entry.get("upload_bytes", 0)))
            download_bytes = max(0, int(entry.get("download_bytes", 0)))
            entry["total_bytes"] = upload_bytes + download_bytes

        return usage

    def get_usage_for_client_ip(self, client_ip: str) -> Dict[str, int]:
        usage_map = self.get_usage_counters_by_ip()
        usage = usage_map.get(str(client_ip).strip(), {})
        upload_bytes = max(0, int(usage.get("upload_bytes", 0)))
        download_bytes = max(0, int(usage.get("download_bytes", 0)))
        return {
            "upload_bytes": upload_bytes,
            "download_bytes": download_bytes,
            "total_bytes": upload_bytes + download_bytes,
        }


# Singleton instance
_firewall_manager = None

def get_firewall_manager() -> LinuxFirewallManager:
    """Get or create firewall manager instance"""
    global _firewall_manager
    if _firewall_manager is None:
        _firewall_manager = LinuxFirewallManager()
    return _firewall_manager


def get_usage_counters_by_ip() -> Dict[str, Dict[str, int]]:
    """Get live usage counters keyed by client IP."""
    return get_firewall_manager().get_usage_counters_by_ip()


def get_usage_for_client_ip(client_ip: str) -> Dict[str, int]:
    """Get live usage counters for a specific client IP."""
    return get_firewall_manager().get_usage_for_client_ip(client_ip)

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

        # Ensure local services for hotspot clients are reachable.
        _ensure_rule(
            "INPUT",
            ["-i", manager.hotspot_interface, "-p", "tcp", "--dport", "5000", "-j", "ACCEPT"],
            insert_position=1,
        )
        _ensure_rule(
            "INPUT",
            ["-i", manager.hotspot_interface, "-p", "udp", "--dport", "67", "-j", "ACCEPT"],
            insert_position=1,
        )
        _ensure_rule(
            "INPUT",
            ["-i", manager.hotspot_interface, "-p", "udp", "--dport", "53", "-j", "ACCEPT"],
            insert_position=1,
        )
        _ensure_rule(
            "INPUT",
            ["-i", manager.hotspot_interface, "-p", "tcp", "--dport", "53", "-j", "ACCEPT"],
            insert_position=1,
        )
        
        manager.update_from_database()

        logger.info("✅ Captive portal firewall configured for hotspot traffic")
        return True
    except Exception as e:
        logger.error(f"Failed to setup captive portal: {e}")
        return False

def allow_authenticated_user(client_ip: str):
    """Allow internet access for authenticated user"""
    manager = get_firewall_manager()
    
    try:
        _ensure_chain(HOTSPOT_AUTH_CHAIN)
        _ensure_chain(HOTSPOT_USAGE_CHAIN)
        _ensure_rule(HOTSPOT_USAGE_CHAIN, ["-j", "RETURN"])

        _ensure_rule(
            HOTSPOT_AUTH_CHAIN,
            [
                "-s",
                client_ip,
                "-i",
                manager.hotspot_interface,
                "-o",
                manager.internet_interface,
                "-j",
                "ACCEPT",
            ],
        )

        # Add per-client usage accounting rules (upload/download bytes).
        _ensure_rule(
            HOTSPOT_USAGE_CHAIN,
            _usage_upload_rule_args(client_ip, manager.hotspot_interface, manager.internet_interface),
            insert_position=1,
        )
        _ensure_rule(
            HOTSPOT_USAGE_CHAIN,
            _usage_download_rule_args(client_ip, manager.hotspot_interface, manager.internet_interface),
            insert_position=1,
        )

        # Exempt authenticated users from captive HTTP redirect.
        _ensure_chain(HOTSPOT_PREROUTING_CHAIN, table="nat")
        _ensure_rule(
            HOTSPOT_PREROUTING_CHAIN,
            ["-s", client_ip, "-j", "RETURN"],
            table="nat",
            insert_position=1,
        )
        
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
        # Remove per-client usage accounting rules.
        _delete_rule_all(
            HOTSPOT_USAGE_CHAIN,
            _usage_upload_rule_args(client_ip, manager.hotspot_interface, manager.internet_interface),
        )
        _delete_rule_all(
            HOTSPOT_USAGE_CHAIN,
            _usage_download_rule_args(client_ip, manager.hotspot_interface, manager.internet_interface),
        )

        # Remove filter accept rule for this IP.
        _delete_rule_all(
            HOTSPOT_AUTH_CHAIN,
            [
                "-s",
                client_ip,
                "-i",
                manager.hotspot_interface,
                "-o",
                manager.internet_interface,
                "-j",
                "ACCEPT",
            ],
        )

        # Re-enable captive portal redirect for this client.
        _delete_rule_all(
            HOTSPOT_PREROUTING_CHAIN,
            ["-s", client_ip, "-j", "RETURN"],
            table="nat",
        )
        
        if client_ip in manager.authenticated_ips:
            manager.authenticated_ips.remove(client_ip)
        logger.info(f"✅ Blocked internet access for {client_ip}")
        return True
    except Exception as e:
        logger.error(f"Failed to block user {client_ip}: {e}")
        return False

def setup_hotspot_firewall():
    """Initial setup for hotspot firewall with captive portal"""
    # This delegates to captive-portal setup so chain hooks are refreshed.
    success = setup_captive_portal()
    
    manager = get_firewall_manager()
    if success:
        manager.save_rules()
    return success


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
