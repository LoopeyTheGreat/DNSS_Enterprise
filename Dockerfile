FROM python:3.11-slim

WORKDIR /app

# Install supervisor, cron, SSH server, and network tools
RUN apt-get update && apt-get install -y \
    supervisor \
    cron \
    openssh-server \
    iputils-ping \
    dnsutils \
    net-tools \
    traceroute \
    curl \
    wget \
    iperf3 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd

# Ensure crontab directory exists and has correct permissions for cron jobs
RUN mkdir -p /var/spool/cron/crontabs \
    && chmod 1730 /var/spool/cron/crontabs

# Create a user for SSH access and set home directory to /app
RUN useradd -m -d /app -s /bin/bash starfleet && \
    chown -R starfleet:starfleet /app

# Configure SSH for key-based auth and force execution of .bashrc
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/g' /etc/ssh/sshd_config \
    && sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/g' /etc/ssh/sshd_config \
    && echo "AuthorizedKeysFile %h/.ssh/authorized_keys" >> /etc/ssh/sshd_config \
    && echo "PermitUserEnvironment yes" >> /etc/ssh/sshd_config

# Setup SSH directories with proper permissions
RUN mkdir -p /app/.ssh \
    && chmod 700 /app/.ssh \
    && touch /app/.ssh/authorized_keys \
    && chmod 600 /app/.ssh/authorized_keys \
    && chown -R starfleet:starfleet /app/.ssh

# Create .profile to force execution of .bashrc
RUN echo '#!/bin/bash' > /app/.profile && \
    echo 'if [ -f ~/.bashrc ]; then' >> /app/.profile && \
    echo '    . ~/.bashrc' >> /app/.profile && \
    echo 'fi' >> /app/.profile && \
    chown starfleet:starfleet /app/.profile && \
    chmod 644 /app/.profile

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files from the app directory
COPY app/update_cloudflare_ip.py /app/
COPY app/picard.py /app/
COPY app/logger.py /app/
COPY app/config_manager.py /app/
COPY app/notify.py /app/

# Copy cron setup script
COPY cron_setup.sh /app/
RUN chmod +x /app/cron_setup.sh

# Create logs directory and set proper permissions
RUN mkdir -p /app/logs && \
    chown -R starfleet:starfleet /app/logs

# Create a dummy SSH key as placeholder
RUN echo "# This is a placeholder. SSH keys will be mounted at runtime" > /app/.ssh/authorized_keys && \
    chown starfleet:starfleet /app/.ssh/authorized_keys && \
    chmod 600 /app/.ssh/authorized_keys

# Optional - Create a script to process SSH keys at container startup
RUN echo '#!/bin/bash' > /app/process_ssh_keys.sh && \
    echo 'if [ -d /ssh_keys ] && [ "$(ls -A /ssh_keys/*.pub 2>/dev/null)" ]; then' >> /app/process_ssh_keys.sh && \
    echo '  echo "Processing SSH keys..."' >> /app/process_ssh_keys.sh && \
    echo '  cat /ssh_keys/*.pub > /app/.ssh/authorized_keys' >> /app/process_ssh_keys.sh && \
    echo '  chown starfleet:starfleet /app/.ssh/authorized_keys' >> /app/process_ssh_keys.sh && \
    echo '  chmod 600 /app/.ssh/authorized_keys' >> /app/process_ssh_keys.sh && \
    echo '  echo "SSH keys installed successfully"' >> /app/process_ssh_keys.sh && \
    echo 'else' >> /app/process_ssh_keys.sh && \
    echo '  echo "No SSH keys found. SSH access will be limited."' >> /app/process_ssh_keys.sh && \
    echo 'fi' >> /app/process_ssh_keys.sh && \
    chmod +x /app/process_ssh_keys.sh

# Create a .bashrc file for starfleet user that will load env variables and auto-launch picard.py
RUN echo '#!/bin/bash' > /app/.bashrc && \
    echo 'echo "Welcome to the USS Enterprise NCC-1701-DNS"' >> /app/.bashrc && \
    echo 'echo "Loading environment variables..."' >> /app/.bashrc && \
    echo 'export $(grep -v "^#" /app/.env | xargs -d "\n")' >> /app/.bashrc && \
    echo 'echo "Starfleet DNS Console is ready."' >> /app/.bashrc && \
    echo 'if [[ -n $SSH_CONNECTION ]]; then' >> /app/.bashrc && \
    echo '  # When connecting via SSH, auto-launch picard.py' >> /app/.bashrc && \
    echo '  python /app/picard.py' >> /app/.bashrc && \
    echo '  # Exit SSH session when picard.py exits' >> /app/.bashrc && \
    echo '  exit' >> /app/.bashrc && \
    echo 'else' >> /app/.bashrc && \
    echo '  echo "Type ./picard.py to launch the Starfleet DNS Console"' >> /app/.bashrc && \
    echo 'fi' >> /app/.bashrc && \
    chown starfleet:starfleet /app/.bashrc && \
    chmod 644 /app/.bashrc

# Make picard.py executable
RUN chmod +x /app/picard.py

# Create SSH environment file (correctly placed in .ssh directory)
RUN echo "TERM=xterm-256color" > /app/.ssh/environment && \
    echo "FORCE_INTERACTIVE=true" >> /app/.ssh/environment && \
    chown starfleet:starfleet /app/.ssh/environment && \
    chmod 644 /app/.ssh/environment

# Create a copy of the environment file in the container
RUN touch /app/.env && \
    chown starfleet:starfleet /app/.env && \
    chmod 600 /app/.env

# Setup supervisord configuration directly in the Dockerfile
RUN echo "[supervisord]" > /etc/supervisor/conf.d/supervisord.conf \
    && echo "nodaemon=true" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "[program:sshd]" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "command=/usr/sbin/sshd -D" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autorestart=true" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile=/dev/stdout" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile=/dev/stderr" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "[program:process_ssh_keys]" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "command=/app/process_ssh_keys.sh" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autorestart=false" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "startsecs=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "startretries=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile=/dev/stdout" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile=/dev/stderr" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "[program:cron_setup]" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "command=/app/cron_setup.sh" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autorestart=false" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "startsecs=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "startretries=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile=/dev/stdout" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile=/dev/stderr" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "[program:cron]" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "command=/usr/sbin/cron -f -L 15" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autostart=true" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "autorestart=true" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile=/dev/stdout" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stdout_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile=/dev/stderr" >> /etc/supervisor/conf.d/supervisord.conf \
    && echo "stderr_logfile_maxbytes=0" >> /etc/supervisor/conf.d/supervisord.conf

# Remove the init_env.sh script and its supervisord entry
RUN rm -f /app/init_env.sh

# Expose SSH port
EXPOSE 22

ENTRYPOINT ["/usr/bin/supervisord"]