import os
import logging
import datetime
import requests
from logging.handlers import TimedRotatingFileHandler
from config_manager import config_manager

# Logging levels
CRITICAL = 50
ERROR = 40
WARNING = 30
INFO = 20
DEBUG = 10

class DiscordWebhookHandler(logging.Handler):
    """Custom logging handler to send logs to Discord webhook"""
    def __init__(self, webhook_url, min_level=WARNING):
        super().__init__()
        self.webhook_url = webhook_url
        self.min_level = min_level
    def emit(self, record):
        if not self.webhook_url or record.levelno < self.min_level:
            return
        log_message = self.format(record)
        colors = {
            CRITICAL: 0xED4245,
            ERROR: 0xED4245,
            WARNING: 0xFEE75C,
            INFO: 0x57F287,
            DEBUG: 0x5865F2
        }
        color = colors.get(record.levelno, 0x95A5A6)
        embed = {
            "title": f"DNSS Enterprise Log: {record.levelname}",
            "description": log_message,
            "color": color,
            "timestamp": datetime.datetime.now().isoformat(),
            "footer": {
                "text": f"USS Enterprise NCC-1701-DNS | {record.module}.{record.funcName}"
            }
        }
        try:
            data = {"username": "Starfleet DNS Monitor", "embeds": [embed]}
            requests.post(self.webhook_url, json=data)
        except Exception:
            pass

def setup_logging(app_name):
    """Set up logging based on config file and environment variables"""
    # Get logging config from YAML config file
    config = config_manager.get_config() if hasattr(config_manager, 'get_config') else {}
    log_cfg = config.get('logging', {}) if config else {}
    log_level_name = os.environ.get("LOG_LEVEL") or log_cfg.get('level', 'INFO')
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    retention_days = int(os.environ.get("LOG_RETENTION_DAYS", log_cfg.get('backup_count', 7)))
    logs_dir = "/app/logs"
    os.makedirs(logs_dir, exist_ok=True)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)
    log_file = os.path.join(logs_dir, f"{app_name}.log")
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=retention_days
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    # Discord webhook handler
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or \
        config.get('notifications', {}).get('discord', {}).get('webhook_url', '')
    discord_enabled = os.environ.get("DISCORD_ENABLED") or \
        str(config.get('notifications', {}).get('discord', {}).get('enabled', False)).lower()
    if webhook_url and discord_enabled in ["true", "1", "yes"]:
        discord_level_name = os.environ.get("DISCORD_LOG_LEVEL") or "WARNING"
        discord_level = getattr(logging, discord_level_name.upper(), logging.WARNING)
        discord_handler = DiscordWebhookHandler(webhook_url, discord_level)
        discord_handler.setFormatter(formatter)
        logger.addHandler(discord_handler)
        logger.info(f"Discord webhook notifications enabled at level {discord_level_name}")
    logger.info(f"Logging initialized for {app_name} at level {log_level_name}")
    logger.info(f"Log retention set to {retention_days} days")
    return logger

def get_domain_logger(app_name, domain):
    """Get a logger instance for a specific domain"""
    logger = logging.getLogger(f"{app_name}.{domain}")
    return logger