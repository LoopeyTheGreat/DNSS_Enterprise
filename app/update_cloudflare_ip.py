#!/usr/bin/env python3
"""
Cloudflare DNS Root and Wildcard Records Updater

This script automatically updates both the apex domain (example.com) and wildcard DNS records (*.example.com) 
in Cloudflare with your current public IP address. It preserves all other custom DNS records 
(like specific subdomains or TXT records for Traefik challenges).

Configuration is stored in dnss_enterprise/config/config.yaml

Environment Variables (optional, will override config file):
    DOMAIN1, DOMAIN2, etc: Base domain names to manage (e.g., example.com, not sub.example.com)
    CF_API_KEY1, CF_API_KEY2, etc: Corresponding Cloudflare API keys for each domain

Usage:
    python update_cloudflare_ip.py          # Normal update operation
    python update_cloudflare_ip.py --healthcheck  # Perform healthcheck on records
"""

import os
import sys
import requests
import logging
import time
import random
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Tuple, Optional

# Import configuration and notification modules
try:
    from config_manager import config_manager
    from notify import discord_notifier
except ImportError as e:
    print(f"Error: Could not import required modules: {e}")
    print("Make sure all required modules are in the same directory.")
    sys.exit(1)

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"

# Welcome and exit messages for the Star Trek theme
WELCOME_MESSAGES = [
    '🚀 "Welcome to dnss_enterprise: boldly resolving where no DNS has resolved before!"',
    '🖖 "DNS shields up. Ready to intercept rogue IP packets, Captain!"',
    '🛸 "You have entered the Neutral Zone of DNS. Proceed with humor and caution."',
    '🖥️ "Engage! DNS warp engines at full — expect occasional anomalies."',
    '👨‍🔬 "Dr. McCoy here: I\'m a doctor, not a DNS server! Oh wait... never mind."',
    '🖖 "Klingon proverb: \'Only a fool enters battle without verifying his DNS entries.\'"',
    '🚨 "Red alert! Someone requested an A record. All hands to their keyboards!"',
    '📡 "Resistance is futile. Your DNS queries will be answered."',
    '🪐 "Welcome to dnss_enterprise. Infinite diversity in infinite IP addresses."',
    '👨‍🚀 "Scotty: \'She cannae take much more, Captain... these DNS queries are going to blow the nacelles!\'"',
    '🛠️ "Q just dropped by. He said your PTR records are \'quaint\' but will allow them... for now."',
    '🖖 "Worf: \'If DNS fails, today is a good day to die.\'"',
    '🛸 "You are now accessing DNS... powered by dilithium crystals and caffeine."',
    '👩‍💻 "Lt. Uhura here. Your DNS transmission is clear — but seriously, fix your reverse lookups."',
    '🖖 "dnss_enterprise reporting for duty! Phasers set to \'resolve.\'"'
]

EXIT_MESSAGES = [
    '🖖 "dnss_enterprise signing off. May your packets find their destinations — unlike Voyager."',
    '🚀 "Warp core shutting down... DNS entries secured. No tribbles detected."',
    '🛸 "Mission complete. Returning to Starfleet Command for debriefing and tacos."',
    '👨‍🚀 "Engines offline. If anything breaks, just blame Wesley."',
    '🖥️ "Session terminated. DNS server going into stasis — snore sounds intensify."',
    '🚨 "All decks report: DNS stable. Shields down. Time for Raktajino."',
    '🛠️ "Mr. Scott says, \'I gave her all she\'s got, Captain!\' Shutting down before she really blows."',
    '👾 "Borg transmission ended. We have temporarily ceased assimilation... for now."',
    '🛸 "Another DNS mission accomplished. Somewhere, a Romulan cries softly."',
    '🖖 "dnss_enterprise: \'Computer, end program.\' Holodeck fantasy over."',
    '📡 "*Goodbye, Starfleet cadet. Your DNS training is... adequate."',
    '👨‍⚕️ "Dr. McCoy: \'I\'m a doctor, not a sysadmin! Thank Kahless we\'re done.\'"',
    '🚀 "Impulse engines engaged. Gliding gracefully into maintenance mode."',
    '🛸 "Your DNS session has concluded. Recommend two shots of Romulan Ale and a nap."',
    '🖥️ "Final log entry: DNS resolved. Morale high. Klingons moderately appeased."'
]

def display_random_welcome_message():
    """Display a random welcome message from the Star Trek theme"""
    message = random.choice(WELCOME_MESSAGES)
    print("\n" + "=" * 80)
    print(message)
    print("=" * 80 + "\n")

def display_random_exit_message():
    """Display a random exit message from the Star Trek theme"""
    message = random.choice(EXIT_MESSAGES)
    print("\n" + "=" * 80)
    print(message)
    print("=" * 80 + "\n")

# Setup logging using configuration
config = config_manager.get_config()
log_dir = "/app/logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "cloudflare_updater.log")

# Get logging configuration from config file
log_level = config.get('logging', {}).get('level', 'INFO')
log_max_size = config.get('logging', {}).get('max_size_mb', 5) * 1024 * 1024
log_backup_count = config.get('logging', {}).get('backup_count', 3)

# Map string log levels to their numeric values
log_level_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
log_level_numeric = log_level_map.get(log_level, logging.INFO)

# Setup logger
logger = logging.getLogger("cloudflare_updater")
if not logger.hasHandlers():
    logger.setLevel(log_level_numeric)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    file_handler = RotatingFileHandler(log_file, maxBytes=log_max_size, backupCount=log_backup_count)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def get_public_ip() -> Optional[str]:
    """Get the current public IPv4 address."""
    # Get the list of IP detection services from config
    ip_services = config_manager.get('ip_detection_services', [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ])
    
    for service in ip_services:
        try:
            logger.debug(f"Trying to get IP from {service}")
            ip = requests.get(service, timeout=10).text.strip()
            logger.debug(f"Got IP: {ip} from {service}")
            return ip
        except Exception as e:
            logger.warning(f"Error getting IP from {service}: {e}")
            continue
    
    logger.error("Failed to get public IP from all services")
    return None

def get_public_ipv6() -> Optional[str]:
    """Get the current public IPv6 address if enabled."""
    # Check if IPv6 is enabled in config
    ipv6_enabled = config_manager.get('ipv6.enabled', False)
    if not ipv6_enabled:
        logger.debug("IPv6 updates are disabled in config")
        return None
    
    try:
        return requests.get('https://api64.ipify.org', timeout=10).text.strip()
    except Exception as e:
        logger.error(f"Error getting public IPv6: {e}")
        return None

def get_zone_id(domain: str, api_key: str) -> Optional[str]:
    """Get Cloudflare zone ID for the specified domain."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(f"{CLOUDFLARE_API_BASE}/zones?name={domain}", headers=headers, timeout=10)
        if resp.ok and resp.json()['result']:
            return resp.json()['result'][0]['id']
        logger.error(f"Could not get zone id for {domain}: {resp.text}")
        return None
    except Exception as e:
        logger.error(f"Exception getting zone id for {domain}: {e}")
        return None

def get_dns_record_id(zone_id: str, record_name: str, api_key: str, record_type: str = 'A') -> Optional[str]:
    """Get DNS record ID for the specified record name and type."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(
            f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records?type={record_type}&name={record_name}", 
            headers=headers,
            timeout=10
        )
        if resp.ok and resp.json()['result']:
            return resp.json()['result'][0]['id']
        return None
    except Exception as e:
        logger.error(f"Exception getting record id for {record_name}: {e}")
        return None

def get_dns_record(zone_id: str, record_id: str, api_key: str) -> Optional[Dict]:
    """Get DNS record details."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        resp = requests.get(
            f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}", 
            headers=headers,
            timeout=10
        )
        if resp.ok:
            return resp.json()['result']
        return None
    except Exception as e:
        logger.error(f"Exception getting record details for {record_id}: {e}")
        return None

def upsert_dns_record(zone_id: str, record_name: str, ip: str, api_key: str, record_type: str = 'A') -> bool:
    """
    Update or create a DNS record with the specified IP address.
    Used for apex domains (example.com) and wildcard records (*.example.com) in this script.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    record_id = get_dns_record_id(zone_id, record_name, api_key, record_type)
    old_ip = None
    
    # Get current record details to compare if the IP has changed
    if record_id:
        record = get_dns_record(zone_id, record_id, api_key)
        if record:
            old_ip = record.get('content')
            
            # Check if IP is already up to date
            if old_ip == ip:
                logger.info(f"{record_type} {record_name} already has correct IP: {ip}")
                return True
    
    # Determine TTL and proxied settings
    if record_name.startswith('*.'):
        # This is a wildcard record - check for TTL override
        ttl_override = config_manager.get('wildcard_dns.ttl_override')
        ttl = ttl_override if ttl_override is not None else 300
        
        # Check if we should match proxy settings from root domain
        match_proxy_settings = config_manager.get('wildcard_dns.match_proxy_settings', True)
        proxied = False
        
        if match_proxy_settings:
            # Extract root domain from wildcard and check its proxy settings
            root_domain = record_name[2:]  # Remove the *. part
            root_record_id = get_dns_record_id(zone_id, root_domain, api_key, record_type)
            if root_record_id:
                root_record = get_dns_record(zone_id, root_record_id, api_key)
                if root_record:
                    proxied = root_record.get('proxied', False)
    else:
        # Regular record
        ttl = 300
        proxied = False
    
    data = {
        "type": record_type,
        "name": record_name,
        "content": ip,
        "ttl": ttl,
        "proxied": proxied
    }
    
    try:
        if record_id:
            resp = requests.put(
                f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}", 
                headers=headers, 
                json=data,
                timeout=10
            )
            if resp.ok:
                logger.info(f"Updated {record_type} {record_name} from {old_ip} to {ip}")
                
                # Send notification if IP changed
                if old_ip and old_ip != ip:
                    discord_notifier.notify_ip_changed(old_ip, ip)
                
                # Send success notification
                discord_notifier.notify_update_success(record_name, [record_type], ip)
                return True
            else:
                error_msg = f"Failed to update {record_type} {record_name}: {resp.text}"
                logger.error(error_msg)
                discord_notifier.notify_update_failure(record_name, error_msg)
                
                if record_type == 'A' and record_name.startswith('*.'):
                    logger.warning(f"Cloudflare may not allow wildcard A records if a CNAME exists for {record_name}")
                return False
        else:
            resp = requests.post(
                f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records", 
                headers=headers, 
                json=data,
                timeout=10
            )
            if resp.ok:
                logger.info(f"Created {record_type} {record_name} with {ip}")
                discord_notifier.notify_update_success(record_name, [record_type], ip)
                return True
            else:
                error_msg = f"Failed to create {record_type} {record_name}: {resp.text}"
                logger.error(error_msg)
                discord_notifier.notify_update_failure(record_name, error_msg)
                
                if record_type == 'A' and record_name.startswith('*.'):
                    logger.warning(f"Cloudflare may not allow wildcard A records if a CNAME exists for {record_name}")
                return False
    except Exception as e:
        error_msg = f"Exception during DNS record upsert for {record_name}: {e}"
        logger.error(error_msg)
        discord_notifier.notify_update_failure(record_name, str(e))
        return False

def check_wildcard_status(domain: str, api_key: str) -> bool:
    """
    Check if wildcard DNS record exists and matches the root domain record.
    Returns True if the records match or wildcard sync is disabled, False if there's a mismatch.
    """
    # Check if wildcard sync is enabled in config
    wildcard_sync_enabled = config_manager.get('wildcard_dns.sync_with_root', True)
    if not wildcard_sync_enabled:
        logger.debug(f"Wildcard sync disabled for {domain} in config")
        return True
    
    zone_id = get_zone_id(domain, api_key)
    if not zone_id:
        return False
        
    # Get the root domain record
    root_record_id = get_dns_record_id(zone_id, domain, api_key, 'A')
    if not root_record_id:
        logger.warning(f"Root domain record not found for {domain}")
        return True  # No action needed
        
    root_record = get_dns_record(zone_id, root_record_id, api_key)
    if not root_record:
        return True
        
    root_ip = root_record.get('content')
    
    # Get the wildcard record
    wildcard_name = f"*.{domain}"
    wildcard_record_id = get_dns_record_id(zone_id, wildcard_name, api_key, 'A')
    
    if not wildcard_record_id:
        # Wildcard doesn't exist but should be synced
        logger.info(f"Wildcard record doesn't exist for {domain}, will create it")
        return False
        
    wildcard_record = get_dns_record(zone_id, wildcard_record_id, api_key)
    if not wildcard_record:
        return False
        
    wildcard_ip = wildcard_record.get('content')
    
    # Compare the IPs
    if root_ip != wildcard_ip:
        logger.warning(f"Root domain {domain} ({root_ip}) doesn't match wildcard *.{domain} ({wildcard_ip})")
        discord_notifier.notify_wildcard_mismatch(domain, root_ip, wildcard_ip)
        return False
        
    return True

def get_env_pairs() -> List[Tuple[str, str]]:
    """Get domain and API key pairs from environment variables."""
    pairs = []
    env = os.environ
    
    for k, v in env.items():
        if k.startswith('DOMAIN'):
            idx = k[6:]
            domain = v.strip()
            api_key = env.get(f'CF_API_KEY{idx}', '').strip()
            if not api_key:
                logger.warning(f"Skipping {domain}: missing CF_API_KEY{idx}")
                continue
            if domain and api_key:
                pairs.append((domain, api_key))
                
    return pairs

def healthcheck() -> bool:
    """Perform healthcheck on DNS records."""
    ip = get_public_ip()
    if not ip:
        logger.error("Healthcheck failed: could not get public IPv4")
        return False
        
    # Check environment variables first, then fall back to config
    env = os.environ
    domain = env.get('DOMAIN1')
    api_key = env.get('CF_API_KEY1')
    
    # If not in environment, try to get first domain from config
    # Note: We'll need to implement a way to store domains in the config
    
    if not (domain and api_key):
        logger.error("Healthcheck failed: missing DOMAIN1 or CF_API_KEY1")
        return False
        
    zone_id = get_zone_id(domain, api_key)
    if not zone_id:
        logger.error("Healthcheck failed: could not get zone id")
        return False
        
    # Check the apex domain record
    record_id = get_dns_record_id(zone_id, domain, api_key, 'A')
    if not record_id:
        logger.error("Healthcheck failed: could not get DNS record id for apex domain")
        return False
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    resp = requests.get(f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}", headers=headers)
    if not resp.ok or resp.json()['result']['content'] != ip:
        logger.error("Healthcheck failed: apex domain DNS record does not match public IP")
        return False
        
    # Check the wildcard domain record if enabled
    wildcard_sync_enabled = config_manager.get('wildcard_dns.sync_with_root', True)
    if wildcard_sync_enabled:
        wildcard_domain = f"*.{domain}"
        record_id = get_dns_record_id(zone_id, wildcard_domain, api_key, 'A')
        
        if not record_id:
            logger.error("Healthcheck failed: could not get DNS record id for wildcard domain")
            return False
            
        resp = requests.get(f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records/{record_id}", headers=headers)
        if resp.ok:
            record_ip = resp.json()['result']['content']
            if record_ip != ip:
                logger.error(f"Healthcheck failed: wildcard DNS IP {record_ip} != public IP {ip}")
                return False
        else:
            logger.error("Healthcheck failed: could not fetch DNS record")
            return False
            
    logger.info("Healthcheck passed")
    return True

def main() -> int:
    """Main function to execute the DNS update process."""
    # Display welcome message when starting
    display_random_welcome_message()
    
    # Get domain/API key pairs from environment variables
    pairs = get_env_pairs()
    
    if not pairs:
        logger.error("No valid domain/API key pairs found. Exiting.")
        sys.exit(1)
        
    logger.info(f"Found {len(pairs)} domain(s) to process")
    
    # Get current public IP
    ip = get_public_ip()
    if not ip:
        logger.error("Could not determine public IPv4. Exiting.")
        sys.exit(1)
        
    logger.info(f"Current public IPv4: {ip}")
    
    # Check for IPv6 support
    ipv6_enabled = config_manager.get('ipv6.enabled', False)
    ipv6 = None
    if ipv6_enabled:
        ipv6 = get_public_ipv6()
        if ipv6:
            logger.info(f"Current public IPv6: {ipv6}")
        else:
            logger.warning("Could not determine public IPv6 despite being enabled. Skipping AAAA records.")
            
    # Process all domains
    for domain, api_key in pairs:
        logger.info(f"Processing domain: {domain}")
        
        zone_id = get_zone_id(domain, api_key)
        if not zone_id:
            continue
            
        # Update root domain A record
        logger.info(f"Updating root domain {domain}")
        success = upsert_dns_record(zone_id, domain, ip, api_key, 'A')
        
        # Check if we should sync wildcard record
        wildcard_sync_enabled = config_manager.get('wildcard_dns.sync_with_root', True)
        if wildcard_sync_enabled:
            # Update wildcard record
            wildcard_domain = f"*.{domain}"
            logger.info(f"Updating wildcard domain {wildcard_domain}")
            upsert_dns_record(zone_id, wildcard_domain, ip, api_key, 'A')
        else:
            logger.debug(f"Wildcard sync disabled for {domain}, skipping")
        
        # Update IPv6 records if enabled
        if ipv6_enabled and ipv6:
            logger.info(f"Updating IPv6 records for {domain}")
            
            # Update root domain AAAA record
            upsert_dns_record(zone_id, domain, ipv6, api_key, 'AAAA')
            
            # Update wildcard AAAA record if enabled
            if wildcard_sync_enabled:
                upsert_dns_record(zone_id, f"*.{domain}", ipv6, api_key, 'AAAA')
                
        logger.info(f"Completed updates for {domain}")
        
    logger.info("DNS update process complete")
    
    # Display exit message before finishing
    display_random_exit_message()
    return 0

if __name__ == "__main__":
    # Display welcome message
    display_random_welcome_message()
    
    # Check if healthcheck flag is provided
    if len(sys.argv) > 1 and sys.argv[1] == "--healthcheck":
        # Run healthchecks
        success = healthcheck()
        if success:
            print("Healthcheck OK")
            sys.exit(0)
        else:
            print("Healthcheck failed")
            sys.exit(1)
    else:
        # Run normal update
        sys.exit(main())
        
    # Display exit message before exit
    display_random_exit_message()
