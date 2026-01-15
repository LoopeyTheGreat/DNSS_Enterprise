# DNSS Enterprise - Starfleet DNS Operations Console

A secure containerized DNS management system for automatic CloudFlare DNS record updates. The system includes an optional SSH key-based authentication interface with a Star Trek-themed console for manual management.

## Quick Start (Automated Updates Only)

If you only want automatic DNS updates without the SSH management interface:

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/dnss_enterprise.git
   cd dnss_enterprise
   ```

2. Create your configuration files:
   ```bash
   cp .env.example .env
   cp config/config.yaml.example config/config.yaml
   ```

3. Edit the `.env` file with your CloudFlare domain and API keys

4. Build and start the container:
   ```bash
   docker compose up -d
   ```

That's it! The container will automatically check your IP address every 10 minutes (configurable) and update your CloudFlare DNS records if it changes.

## Quick Start (With SSH Management Interface)

For the full experience including the SSH management interface:

1. Follow steps 1-3 above

2. Add your SSH public key to the `ssh_keys` directory:
   ```bash
   cp ~/.ssh/id_ed25519.pub ssh_keys/
   ```

3. Build and start the containers:
   ```bash
   docker compose up --build -d
   ```

4. Connect via SSH:
   ```bash
   ssh -p 1701 starfleet@your-host-ip
   ```
   ### Tip: Create a Quick Connect Script

   For convenience, you can create a simple executable script to connect to the SSH management interface. For example, create a file named `connect.sh`:

   ```bash
   #!/bin/bash
   ssh -p 1701 starfleet@your-host-ip
   ```

   Make it executable:

   ```bash
   chmod +x connect.sh
   ```

   Now you can connect quickly by running:

   ```bash
   ./connect.sh
   ```
## Features

- **Automated IP Detection & DNS Updates**: Updates your CloudFlare DNS records every 10 minutes (configurable)
- Secure SSH key-based authentication (optional)
- Terminal-based interface with Star Trek theming (optional)
- Support for managing multiple domains
- Built-in network diagnostic tools
- Comprehensive logging system with Discord notifications
- Automatic log rotation and retention policy

## Configuration

### Environment Variables

Edit the `.env` file with your CloudFlare domains and API keys:

```
DOMAIN1=yourdomain.com
CF_API_KEY1=your_cloudflare_api_key

# Optional additional domains
DOMAIN2=yoursecondomain.com
CF_API_KEY2=your_second_cloudflare_api_key
```

### SSH Keys (Optional)

If you want to use the SSH management interface, add your public SSH keys to the `ssh_keys` directory. All `.pub` files in this directory will be authorized for SSH access.

### YAML Configuration

Edit `config/config.yaml` to customize:

- Update frequency (cron schedule) - default is every 10 minutes
- Wildcard DNS record behavior
- Discord notification settings
- IPv6 support
- Logging preferences

## Discord Integration

To enable Discord notifications:

1. Create a Discord webhook in your server's settings
2. Add the webhook URL to your `.env` file:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url_here
   ```
3. Notifications are color-coded by severity level

## Maintenance

### Accessing Logs

Logs are stored in the `logs` directory and can be viewed from your host:

```bash
tail -f logs/cloudflare_updater.log  # DNS update logs
tail -f logs/picard.log              # CLI application logs (if using SSH interface)
```

### Updating CloudFlare Domains

1. Edit the `.env` file with your domain information
2. Restart: `docker compose restart`

## How It Works

1. The container runs a cron job (default: every 10 minutes) that executes `update_cloudflare_ip.py`
2. The script detects your public IP address using external services
3. If your IP has changed since the last check, it updates all configured CloudFlare DNS records
4. Optional SSH interface provides manual control for one-off updates and other management tasks

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Star Trek™ is a trademark of CBS Studios Inc.
- This project is not affiliated with or endorsed by CBS Studios Inc.