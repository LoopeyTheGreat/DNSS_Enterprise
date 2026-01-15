#!/usr/bin/env python3
"""
Configuration Manager for DNSS Enterprise

Handles loading, parsing, and saving configuration from YAML files.
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional

# Default configuration values
DEFAULT_CONFIG = {
    "cron_schedule": "*/10 * * * *",
    "wildcard_dns": {
        "sync_with_root": True,
        "match_proxy_settings": True,
        "ttl_override": None
    },
    "notifications": {
        "discord": {
            "enabled": False,
            "webhook_url": "",
            "events": {
                "ip_changed": True,
                "update_success": True,
                "update_failure": True,
                "root_wildcard_mismatch": True
            }
        }
    },
    "ipv6": {
        "enabled": False
    },
    "ip_detection_services": [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ],
    "logging": {
        "level": "INFO",
        "max_size_mb": 5,
        "backup_count": 3
    }
}

# Setup basic logging until config is loaded
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger("config_manager")

class ConfigManager:
    """Manager for configuration handling"""
    def __init__(self, config_dir: str = None):
        """Initialize the configuration manager"""
        # Determine the config directory location
        if config_dir is None:
            # Use the default config directory - check if we're in container first
            if os.path.exists("/app/config"):
                self.config_dir = "/app/config"
            else:
                # Fallback for development/local testing
                script_dir = os.path.dirname(os.path.abspath(__file__))
                self.config_dir = os.path.join(os.path.dirname(script_dir), "config")
        else:
            self.config_dir = config_dir
            
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.config_file = os.path.join(self.config_dir, "config.yaml")
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file, or create default if not exists"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as file:
                    config = yaml.safe_load(file)
                logger.info(f"Configuration loaded from {self.config_file}")
                
                # Validate and merge with defaults for any missing values
                return self._merge_with_defaults(config)
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                logger.warning("Using default configuration")
                return DEFAULT_CONFIG.copy()
        else:
            # Create default configuration file
            logger.info(f"Creating default configuration file at {self.config_file}")
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
            
    def _merge_with_defaults(self, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge user configuration with default values for missing keys"""
        if user_config is None:
            return DEFAULT_CONFIG.copy()
            
        result = DEFAULT_CONFIG.copy()
        
        def merge_dict(default_dict, user_dict):
            """Helper function to recursively merge dictionaries"""
            for key, default_value in default_dict.items():
                if key in user_dict:
                    if isinstance(default_value, dict) and isinstance(user_dict[key], dict):
                        merge_dict(default_value, user_dict[key])
                    else:
                        default_dict[key] = user_dict[key]
        
        # Create a deep copy to avoid modifying the original
        merged = result.copy()
        merge_dict(merged, user_config)
        return merged
            
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as file:
                yaml.dump(config, file, default_flow_style=False, sort_keys=False)
            logger.debug(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
            
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration"""
        return self.config
        
    def set_config(self, config: Dict[str, Any]) -> bool:
        """Update and save the configuration"""
        # Validate and merge with defaults
        self.config = self._merge_with_defaults(config)
        return self._save_config(self.config)
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value using dot notation (e.g., 'wildcard_dns.sync_with_root')"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any) -> bool:
        """Set a specific configuration value using dot notation and save the config"""
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        parent = config
        for k in keys[:-1]:
            if k not in parent or not isinstance(parent[k], dict):
                parent[k] = {}
            parent = parent[k]
                
        # Set the value and save
        parent[keys[-1]] = value
        return self._save_config(config)

# Create a singleton instance
config_manager = ConfigManager()

def get_config() -> Dict[str, Any]:
    """Convenience function to get the current configuration"""
    return config_manager.get_config()
    
def get(key: str, default: Any = None) -> Any:
    """Convenience function to get a specific configuration value"""
    return config_manager.get(key, default)
    
def set(key: str, value: Any) -> bool:
    """Convenience function to set a specific configuration value"""
    return config_manager.set(key, value)

if __name__ == "__main__":
    # Simple test to print current configuration
    config = get_config()
    print("Current configuration:")
    print(yaml.dump(config, default_flow_style=False))