# Cloudflare API Setup for DNSS Enterprise

This guide shows how to create domain-specific API tokens for secure Cloudflare DNS management with DNSS Enterprise.

## Prerequisites

- A Cloudflare account
- At least one domain configured to use Cloudflare's nameservers

## Step 1: Create a Domain-Specific API Token

1. Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click your **profile icon** in the top-right corner
3. Select **My Profile** from the dropdown menu
4. Click on the **API Tokens** tab
5. Click **Create Token**
6. Select **Create Custom Token**
7. Name your token (e.g., "DNSS Enterprise - example.com")
8. Under **Permissions**, add the following:
   - **Zone** - **DNS** - **Edit**
   - **Zone** - **Zone** - **Read**
9. Under **Zone Resources**:
   - Set to **Include** - **Specific zone** - Select your domain(s)
10. Set a token expiration (or leave as "No expiration" if you prefer)
11. Click **Continue to summary**
12. Review your settings and click **Create Token**
13. **COPY YOUR TOKEN NOW** - You won't be able to see it again!

![Cloudflare API Token Creation](https://example.com/cloudflare-api-token-creation.png)

> **Security Advantage**: This creates a limited-scope API token that can only modify DNS records for specific domains, following the principle of least privilege.

## Step 2: Configure Your DNSS Enterprise Container

1. Create or edit the `.env` file in your project's root directory:

```ini
# First domain configuration
DOMAIN1=example.com          # Replace with your domain name
CF_API_KEY1=your_api_token   # Replace with your API token created above

# Optional: Additional domains (if you have multiple)
DOMAIN2=anotherdomain.com    
CF_API_KEY2=another_token    # Create a separate token for each domain for best security

# Optional: Discord notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url
```

## Step 3: Verify DNS Record Configuration

The DNSS Enterprise container will automatically:

- Detect your current public IP address
- Update the root domain A record (e.g., example.com)
- Update wildcard A records (e.g., *.example.com) if enabled in your config

You can check which records will be updated by:

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain
3. Go to **DNS** > **Records**
4. Look for A records pointing to your previous IP address

## Advanced Configuration Options

### Wildcard DNS Settings

Edit `config/config.yaml` to customize wildcard DNS behavior:

```yaml
# Wildcard DNS record management
wildcard_dns:
  # Enable automatic synchronization of wildcard records with root domain
  sync_with_root: true
  # Apply same proxy settings as root domain (true/false)
  match_proxy_settings: true
```

### Update Frequency

The default update interval is 10 minutes. To change this, modify the `cron_schedule` value in `config/config.yaml`:

```yaml
# Cron schedule for automatic DNS updates
# Format: minute hour day month day-of-week
# Example: "*/10 * * * *" = every 10 minutes
cron_schedule: "*/10 * * * *"
```

Common cron patterns:
- Every 5 minutes: `*/5 * * * *`
- Every hour: `0 * * * *`
- Every 6 hours: `0 */6 * * *`
- Once a day at midnight: `0 0 * * *`

## Troubleshooting

If your DNS records are not updating correctly:

1. Verify your API token is correct in the `.env` file
2. Check the logs: `docker logs dnss_enterprise_cron`
3. Make sure your API token has the correct permissions (Zone:DNS:Edit and Zone:Zone:Read)
4. Ensure your domain is using Cloudflare nameservers
5. Verify the A records exist in your Cloudflare DNS configuration

For more detailed error information, check the log files in the `logs/` directory:
```
tail -f logs/cloudflare_updater.log
```

## Token Security Best Practices

- Create separate tokens for each domain when possible
- Set appropriate expiration dates on your tokens
- Revoke tokens immediately if they're ever compromised
- Review and clean up unused tokens periodically

## Additional Resources

- [Cloudflare API Tokens Documentation](https://developers.cloudflare.com/api/tokens/)
- [DNSS Enterprise GitHub Repository](https://github.com/yourusername/dnss_enterprise)

