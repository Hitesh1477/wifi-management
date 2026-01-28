"""
Domain Resolver Module
Resolves domain names to IP addresses for firewall blocking
"""

import socket
import dns.resolver
from typing import List, Set


def resolve_domain_to_ips(domain: str) -> Set[str]:
    """
    Resolve a domain to all its IP addresses (IPv4 and IPv6).
    CDN sites like Instagram have multiple IPs for load balancing.
    
    Args:
        domain: Domain name to resolve (e.g., 'instagram.com')
    
    Returns:
        Set of IP addresses (both IPv4 and IPv6)
    """
    ips = set()
    
    # Remove 'www.' prefix if present for cleaner resolution
    domain_clean = domain.replace('www.', '')
    
    try:
        # Method 1: Use dns.resolver for detailed DNS queries (more IPs)
        try:
            # Get IPv4 addresses (A records)
            ipv4_records = dns.resolver.resolve(domain_clean, 'A')
            for record in ipv4_records:
                ips.add(str(record))
            print(f"  ✅ Found {len(ipv4_records)} IPv4 addresses for {domain_clean}")
        except Exception as e:
            print(f"  ⚠️  No IPv4 records for {domain_clean}: {e}")
        
        try:
            # Get IPv6 addresses (AAAA records)
            ipv6_records = dns.resolver.resolve(domain_clean, 'AAAA')
            for record in ipv6_records:
                ips.add(str(record))
            print(f"  ✅ Found {len(ipv6_records)} IPv6 addresses for {domain_clean}")
        except Exception as e:
            print(f"  ⚠️  No IPv6 records for {domain_clean}: {e}")
    
    except Exception as e:
        print(f"  ⚠️  DNS resolution failed for {domain_clean}: {e}")
    
    # Method 2: Fallback to socket.getaddrinfo (sometimes gets different IPs)
    try:
        addr_info = socket.getaddrinfo(domain_clean, None)
        for info in addr_info:
            ip = info[4][0]
            ips.add(ip)
    except Exception as e:
        print(f"  ⚠️  Socket resolution failed for {domain_clean}: {e}")
    
    # Also try with 'www.' prefix
    if not domain_clean.startswith('www.'):
        www_domain = f'www.{domain_clean}'
        try:
            addr_info = socket.getaddrinfo(www_domain, None)
            for info in addr_info:
                ip = info[4][0]
                ips.add(ip)
        except:
            pass
    
    return ips


def resolve_multiple_domains(domains: List[str]) -> dict:
    """
    Resolve multiple domains to their IP addresses.
    
    Args:
        domains: List of domain names
    
    Returns:
        Dictionary mapping domain -> set of IPs
    """
    result = {}
    
    print(f"\n🔍 Resolving {len(domains)} domains to IP addresses...")
    
    for domain in domains:
        print(f"\n📡 Resolving: {domain}")
        ips = resolve_domain_to_ips(domain)
        
        if ips:
            result[domain] = ips
            print(f"  ✅ Total IPs found: {len(ips)}")
            # Show first 3 IPs as example
            sample_ips = list(ips)[:3]
            for ip in sample_ips:
                print(f"     - {ip}")
            if len(ips) > 3:
                print(f"     ... and {len(ips) - 3} more")
        else:
            result[domain] = set()
            print(f"  ❌ No IPs found for {domain}")
    
    return result


if __name__ == "__main__":
    # Test the resolver
    test_domains = ["instagram.com", "facebook.com", "steampowered.com"]
    
    print("="*60)
    print("Domain Resolver Test")
    print("="*60)
    
    results = resolve_multiple_domains(test_domains)
    
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    
    total_ips = 0
    for domain, ips in results.items():
        print(f"{domain}: {len(ips)} IPs")
        total_ips += len(ips)
    
    print(f"\nTotal IPs to block: {total_ips}")
