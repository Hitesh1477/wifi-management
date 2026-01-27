import time
import schedule
import logging
from firewall_manager import update_firewall_rules

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def job():
    try:
        logging.info("Scheduled Task: Refreshing Firewall IPs...")
        update_firewall_rules()
        logging.info("Task Completed.")
    except Exception as e:
        logging.error(f"Task Failed: {e}")

if __name__ == "__main__":
    logging.info("🚀 Starting IP Refresh Service (Every 6 hours)")
    
    # Run once immediately on startup
    job()
    
    # Schedule every 6 hours
    schedule.every(6).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
