#!/bin/bash

# Create crontab directory if it doesn't exist
mkdir -p /var/spool/cron/crontabs

# Get the cron schedule from the config file using Python
CRON_SCHEDULE=$(python3 -c 'import sys; sys.path.append("/app"); import config_manager; print(config_manager.get("cron_schedule", "*/10 * * * *"))')

# Create the crontab entry with proper working directory and environment
echo "${CRON_SCHEDULE} cd /app && python3 /app/update_cloudflare_ip.py" > /var/spool/cron/crontabs/root

# Set proper permissions for the crontab file
chmod 600 /var/spool/cron/crontabs/root

# Execute cron in the foreground
exec cron -f