#!/usr/bin/env python3
"""
Discord Notification Handler for DNSS Enterprise

Sends notifications to Discord webhooks for various DNS-related events.
"""

import requests
import logging
import json
import time
import os
import random
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    from config_manager import config_manager
except ImportError:
    # Fallback for when config_manager is not available
    class MockConfigManager:
        def get(self, key, default=None):
            return default
    config_manager = MockConfigManager()

# Setup logging
logger = logging.getLogger("discord_notifier")

class DiscordNotifier:
    """Handles sending notifications to Discord"""
    
    def __init__(self):
        """Initialize the Discord notifier"""
        # Check environment variable first, then fall back to config file
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '') or config_manager.get('notifications.discord.webhook_url', '')
        self.enabled = bool(self.webhook_url) or config_manager.get('notifications.discord.enabled', False)
        self.events = config_manager.get('notifications.discord.events', {})
        
    def reload_config(self):
        """Reload configuration values"""
        # Check environment variable first, then fall back to config file
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK_URL', '') or config_manager.get('notifications.discord.webhook_url', '')
        self.enabled = bool(self.webhook_url) or config_manager.get('notifications.discord.enabled', False)
        self.events = config_manager.get('notifications.discord.events', {})
        
    def is_enabled(self, event_type: str) -> bool:
        """Check if notifications are enabled for a specific event type"""
        if not self.enabled or not self.webhook_url:
            return False
            
        # Check if this specific event type is enabled
        return self.events.get(event_type, False)
        
    def _send_discord_message(self, embed: Dict[str, Any]) -> bool:
        """Send a message to Discord webhook"""
        if not self.enabled or not self.webhook_url:
            logger.debug("Discord notifications disabled or webhook not configured")
            return False
            
        # Format the payload for Discord
        payload = {
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 204:  # Discord returns 204 No Content on success
                logger.debug("Discord notification sent successfully")
                return True
            else:
                logger.warning(f"Discord notification failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            return False
            
    def notify_ip_changed(self, old_ip: str, new_ip: str) -> bool:
        """Send notification when the public IP address changes"""
        if not self.is_enabled('ip_changed'):
            return False
            
        embed = {
            "title": "🌐 Public IP Address Changed",
            "description": f"The public IP address has changed from {old_ip} to {new_ip}.",
            "color": 3447003,  # Blue
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DNSS Enterprise IP Monitor"
            }
        }
        
        return self._send_discord_message(embed)
        
    def notify_update_success(self, domain: str, record_types: List[str], ip: str) -> bool:
        """Send notification when DNS records are successfully updated"""
        if not self.is_enabled('update_success'):
            return False
            
        embed = {
            "title": "✅ DNS Records Updated Successfully",
            "description": f"DNS records for **{domain}** have been updated to {ip}.\n"
                          f"Record types: {', '.join(record_types)}",
            "color": 3066993,  # Green
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DNSS Enterprise DNS Updater"
            }
        }
        
        return self._send_discord_message(embed)
        
    def notify_update_failure(self, domain: str, error: str) -> bool:
        """Send notification when DNS record updates fail"""
        if not self.is_enabled('update_failure'):
            return False
            
        embed = {
            "title": "❌ DNS Update Failed",
            "description": f"Failed to update DNS records for **{domain}**.\n"
                          f"Error: {error}",
            "color": 15158332,  # Red
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DNSS Enterprise DNS Updater"
            }
        }
        
        return self._send_discord_message(embed)
        
    def notify_wildcard_mismatch(self, domain: str, root_ip: str, wildcard_ip: str) -> bool:
        """Send notification when root and wildcard DNS records don't match"""
        if not self.is_enabled('root_wildcard_mismatch'):
            return False
            
        embed = {
            "title": "⚠️ DNS Record Mismatch Detected",
            "description": f"The root domain and wildcard records for **{domain}** have different IPs.\n"
                          f"Root domain: {root_ip}\n"
                          f"Wildcard domain: {wildcard_ip}",
            "color": 16225054,  # Yellow
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DNSS Enterprise DNS Monitor"
            }
        }
        
        return self._send_discord_message(embed)
        
    def notify_custom(self, title: str, description: str, color: int = 3447003) -> bool:
        """Send a custom notification"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DNSS Enterprise"
            }
        }
        
        return self._send_discord_message(embed)
    
    def notify_login(self, username: str = "Unknown", source_ip: str = "Unknown") -> bool:
        """Send notification when a user logs into the system"""
        if not self.is_enabled('login'):
            return False
            
        embed = {
            "title": "🔐 System Login Detected",
            "description": f"User **{username}** has logged into the DNSS Enterprise system\n"
                          f"Source IP: {source_ip}",
            "color": 5793266,  # Green-blue
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DNSS Enterprise Security Monitor"
            }
        }
        
        return self._send_discord_message(embed)
        
    def notify_exit(self, username: str = "Unknown", session_duration: str = "Unknown") -> bool:
        """Send notification when a user exits the system"""
        if not self.is_enabled('exit'):
            return False
            
        embed = {
            "title": "👋 System Exit Detected",
            "description": f"User **{username}** has exited the DNSS Enterprise system\n"
                          f"Session duration: {session_duration}",
            "color": 10181046,  # Purple
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "DNSS Enterprise Security Monitor"
            }
        }
        
        return self._send_discord_message(embed)

# Create a singleton instance
discord_notifier = DiscordNotifier()

WELCOME_MESSAGES = [
    "🚀 'Welcome to dnss_enterprise: boldly resolving where no DNS has resolved before!'",
    "🖖 'DNS shields up. Ready to intercept rogue IP packets, Captain!'",
    "🛸 'You have entered the Neutral Zone of DNS. Proceed with humor and caution.'",
    "🖥️ 'Engage! DNS warp engines at full — expect occasional anomalies.'",
    "👨‍🔬 'Dr. McCoy here: I'm a doctor, not a DNS server! Oh wait... never mind.'",
    "🖖 'Klingon proverb: \'Only a fool enters battle without verifying his DNS entries.\''",
    "🚨 'Red alert! Someone requested an A record. All hands to their keyboards!'",
    "📡 'Resistance is futile. Your DNS queries will be answered.'",
    "🪐 'Welcome to dnss_enterprise. Infinite diversity in infinite IP addresses.'",
    "👨‍🚀 'Scotty: \'She cannae take much more, Captain... these DNS queries are going to blow the nacelles!\''",
    "🛠️ 'Q just dropped by. He said your PTR records are \'quaint\' but will allow them... for now.'",
    "🖖 'Worf: \'If DNS fails, today is a good day to die.\''",
    "🛸 'You are now accessing DNS... powered by dilithium crystals and caffeine.'",
    "👩‍💻 'Lt. Uhura here. Your DNS transmission is clear — but seriously, fix your reverse lookups.'",
    "🖖 'dnss_enterprise reporting for duty! Phasers set to \'resolve.\''"
]

EXIT_MESSAGES = [
    "🖖 'dnss_enterprise signing off. May your packets find their destinations — unlike Voyager.'",
    "🚀 'Warp core shutting down... DNS entries secured. No tribbles detected.'",
    "🛸 'Mission complete. Returning to Starfleet Command for debriefing and tacos.'",
    "👨‍🚀 'Engines offline. If anything breaks, just blame Wesley.'",
    "🖥️ 'Session terminated. DNS server going into stasis — snore sounds intensify.'",
    "🚨 'All decks report: DNS stable. Shields down. Time for Raktajino.'",
    "🛠️ 'Mr. Scott says, \'I gave her all she\'s got, Captain!\' Shutting down before she really blows.'",
    "👾 'Borg transmission ended. We have temporarily ceased assimilation... for now.'",
    "🛸 'Another DNS mission accomplished. Somewhere, a Romulan cries softly.'",
    "🖖 'dnss_enterprise: \'Computer, end program.\' Holodeck fantasy over.'",
    "📡 '*Goodbye, Starfleet cadet. Your DNS training is... adequate.'",
    "👨‍⚕️ 'Dr. McCoy: \'I'm a doctor, not a sysadmin! Thank Kahless we\'re done.'",
    "🚀 'Impulse engines engaged. Gliding gracefully into maintenance mode.'",
    "🛸 'Your DNS session has concluded. Recommend two shots of Romulan Ale and a nap.'",
    "🖥️ 'Final log entry: DNS resolved. Morale high. Klingons moderately appeased.'"
]

def get_random_welcome_message():
    return random.choice(WELCOME_MESSAGES)

def get_random_exit_message():
    return random.choice(EXIT_MESSAGES)

if __name__ == "__main__":
    # Test the notification system
    logging.basicConfig(level=logging.INFO)
    
    # Set the webhook URL for testing
    webhook_url = input("Enter Discord webhook URL for testing (or press Enter to skip): ")
    if webhook_url:
        config_manager.set("notifications.discord.webhook_url", webhook_url)
        config_manager.set("notifications.discord.enabled", True)
        discord_notifier.reload_config()
        
        print("Sending test notifications...")
        discord_notifier.notify_ip_changed("192.168.1.1", "203.0.113.1")
        time.sleep(1)  # Add delay to prevent rate limiting
        discord_notifier.notify_update_success("example.com", ["A", "AAAA"], "203.0.113.1")
        time.sleep(1)
        discord_notifier.notify_update_failure("example.com", "API authentication failed")
        time.sleep(1)
        discord_notifier.notify_wildcard_mismatch("example.com", "203.0.113.1", "192.168.1.1")
        
        print("Test notifications sent. Check your Discord channel.")
    else:
        print("Skipping test notifications.")