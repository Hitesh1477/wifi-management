import subprocess
import socket
import logging
from db import web_filter_collection
from Detection_Management.domain_map import DOMAIN_APP_MAP

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RULE_NAME_PREFIX = "WiFi_Block_"

def get_blocked_domains():
    """Fetch all blocked domains from MongoDB configuration."""
    config = web_filter_collection.find_one({"type": "config"})
    if not config:
        return []

    blocked_domains = set(config.get("manual_blocks", []))
    
    # Add categories
    categories = config.get("categories", {})
    for cat_name, details in categories.items():
        if details.get("active"):
            blocked_domains.update(details.get("sites", []))
            
    return list(blocked_domains)

def resolve_domain_ips(domain):
    """Resolve a domain to its IPv4 addresses."""
    ips = set()
    try:
        # Try resolving the domain itself
        addr_info = socket.getaddrinfo(domain, None, socket.AF_INET)
        for info in addr_info:
            ips.add(info[4][0])
            
        # Try adding www. prefix if not present
        if not domain.startswith("www."):
            try:
                addr_info_www = socket.getaddrinfo(f"www.{domain}", None, socket.AF_INET)
                for info in addr_info_www:
                    ips.add(info[4][0])
            except:
                pass
    except Exception as e:
        logging.warning(f"Failed to resolve {domain}: {e}")
        
    return list(ips)

def update_firewall_rules():
    """Sync Windows Firewall rules with the blocked list."""
    logging.info("Syncing firewall rules...")
    domains = get_blocked_domains()
    
    all_ips = []
    for domain in domains:
        ips = resolve_domain_ips(domain)
        if ips:
            all_ips.extend(ips)
            
    # Clean up duplicate IPs
    all_ips = list(set(all_ips))
    
    if not all_ips:
        logging.info("No IPs to block. Clearing rules.")
        clear_firewall_rules()
        return

    # Create/Update a single consolidated rule (Windows Firewall handles many IPs well)
    # Breaking into chunks if too large (thousands), but for < 500 IPs one rule is usually fine.
    # PowerShell command to creating 'Block' rule for Outbound traffic
    
    rule_name = f"{RULE_NAME_PREFIX}Global"
    ip_string = ",".join(all_ips)
    
    # We use PowerShell for more robust handling
    ps_script = f"""
    $RuleName = "{rule_name}"
    $IPs = "{ip_string}"
    
    # Remove existing rule if exists
    Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    
    # Create new rule
    if ($IPs.Length -gt 0) {{
        New-NetFirewallRule -DisplayName $RuleName -Direction Outbound -Action Block -RemoteAddress $IPs.Split(',') -Description "Blocks access to restricted websites for students"
        Write-Host "Rule updated with $($IPs.Split(',').Count) IPs"
    }}
    """
    
    try:
        subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True)
        logging.info(f"Firewall rule updated. Blocked {len(all_ips)} IPs.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to update firewall: {e}")

def clear_firewall_rules():
    """Remove all blocking rules."""
    ps_script = f"""
    Get-NetFirewallRule -DisplayName "{RULE_NAME_PREFIX}*" | Remove-NetFirewallRule
    """
    try:
        subprocess.run(["powershell", "-Command", ps_script], check=True)
        logging.info("Cleared firewall rules.")
    except Exception as e:
        logging.error(f"Failed to clear rules: {e}")

if __name__ == "__main__":
    update_firewall_rules()
