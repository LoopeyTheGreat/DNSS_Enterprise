#!/bin/bash

PYTHON_BIN="/usr/local/bin/python3"

# Create crontab directory if it doesn't exist
mkdir -p /var/spool/cron/crontabs

# Get the cron schedule from the config file using Python
CRON_SCHEDULE=$(${PYTHON_BIN} -c 'import sys; sys.path.append("/app/app"); import config_manager; print(config_manager.get("cron_schedule", "*/10 * * * *"))')

# Create the crontab entry with proper working directory and environment
echo "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" > /var/spool/cron/crontabs/root
echo "${CRON_SCHEDULE} set -a; [ -f /app/.env ] && . /app/.env; set +a; cd /app && PYTHONPATH=/app/app ${PYTHON_BIN} /app/app/update_cloudflare_ip.py >> /app/logs/cloudflare_updater.log 2>&1" >> /var/spool/cron/crontabs/root

# Set proper permissions for the crontab file
chmod 600 /var/spool/cron/crontabs/root

# Cron daemon is managed by supervisord
exit 0