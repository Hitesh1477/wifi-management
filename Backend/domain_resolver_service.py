#!/usr/bin/env python3
"""
Domain Resolver Service - Periodically refresh IPs for blocked domains
Runs as a background service to keep firewall rules updated
"""

import time
import logging
from datetime import datetime
from linux_firewall_manager import get_firewall_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DomainResolverService:
    def __init__(self, refresh_interval=3600):
        """
        Initialize resolver service
        
        Args:
            refresh_interval: Seconds between IP refresh (default 1 hour)
        """
        self.refresh_interval = refresh_interval
        self.firewall_manager = get_firewall_manager()
        self.running = False
    
    def run(self):
        """Main service loop"""
        self.running = True
        logger.info(f"Domain Resolver Service started (refresh every {self.refresh_interval}s)")
        
        while self.running:
            try:
                logger.info("Refreshing firewall rules from database...")
                success = self.firewall_manager.update_from_database()
                
                if success:
                    self.firewall_manager.save_rules()
                    stats = self.firewall_manager.get_blocked_ips_count()
                    logger.info(f"✅ Rules updated - {stats['total_blocked_ips']} IPs blocked")
                else:
                    logger.error("❌ Failed to update firewall rules")
                
                # Wait for next refresh
                logger.info(f"Next refresh in {self.refresh_interval} seconds...")
                time.sleep(self.refresh_interval)
                
            except KeyboardInterrupt:
                logger.info("Received stop signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in resolver service: {e}")
                time.sleep(60)  # Wait 1 minute before retrying on error
        
        logger.info("Domain Resolver Service stopped")
    
    def stop(self):
        """Stop the service"""
        self.running = False


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Domain Resolver Service')
    parser.add_argument(
        '--interval',
        type=int,
        default=3600,
        help='Refresh interval in seconds (default: 3600 = 1 hour)'
    )
    
    args = parser.parse_args()
    
    service = DomainResolverService(refresh_interval=args.interval)
    
    try:
        service.run()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        sys.exit(0)
