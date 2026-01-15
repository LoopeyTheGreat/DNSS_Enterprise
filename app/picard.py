# Renamed from caprica_6.py to picard.py for Star Trek theme

import os
import sys
import time
import subprocess
import socket
import re
from logger import setup_logging, get_domain_logger
from notify import discord_notifier, get_random_welcome_message, get_random_exit_message
from config_manager import config_manager
from update_cloudflare_ip import get_public_ip, upsert_dns_record, get_zone_id

log = setup_logging("picard")
logger = log  # for compatibility with get_domain_logger usage
notify = sys.modules["notify"] if "notify" in sys.modules else None  # fallback for notify usage

def print_welcome():
    """Print welcome message with ship identification"""
    hostname = socket.gethostname()
    os.system('cls' if os.name == 'nt' else 'clear')
    print(r"""
   _____ _             _        _         _   _            _   _                 _   
  / ____| |           | |      | |       | | | |          | \ | |               | |  
 | (___ | |_ ___   ___| | _____| |_ ___  | |_| |__   ___  |  \| | ___  _   _ ___| |_ 
  \___ \| __/ _ \ / __| |/ / _ \ __/ __| | __| '_ \ / _ \ | . ` |/ _ \| | | / __| __|
  ____) | || (_) | (__|   <  __/ |_\__ \ | |_| | | |  __/ | |\  | (_) | |_| \__ \ |_ 
 |_____/ \__\___/ \___|_|\_\___|\__|___/  \__|_| |_|\___| |_| \_|\___/ \__,_|___/\__|
-------------------------------------------------------------------------------------
      Welcome to Starfleet DNS Console - "Make it so."
      (Star Trek DNS Operations Console)
-------------------------------------------------------------------------------------
    """)
    print(f"USS ENTERPRISE NCC-1701-DNS [{hostname}]")
    print(f"Stardate: {time.strftime('%Y%m31.%H%M')}")
    print(f"Authenticated via: SSH Key")
    print("-------------------------------------------------------------------------------------")
    print()

    # Get SSH client info
    ssh_client = os.environ.get('SSH_CLIENT', 'unknown')
    
    # Log successful login
    log.info(f"Successful login via SSH from {ssh_client}")
    
    # Send Discord notification for login
    try:
        # Extract source IP from SSH_CLIENT (format: "IP PORT LOCALPORT")
        source_ip = ssh_client.split()[0] if ' ' in ssh_client else ssh_client
        
        # Get username if available
        username = os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'
        
        # Send notification
        discord_notifier.notify_login(username, source_ip)
    except Exception as e:
        log.error(f"Failed to send login notification: {str(e)}")

def read_env_file(env_path='.env'):
    """Read domain and API key pairs from .env file"""
    pairs = []
    domain_pattern = re.compile(r'DOMAIN(\d+)=(.+)')
    api_key_pattern = re.compile(r'CF_API_KEY(\d+)=(.+)')
    
    domains = {}
    api_keys = {}
    
    # Check if .env file exists
    if not os.path.exists(env_path):
        log.warning(f"Warning: {env_path} file not found")
        # Try alternative locations
        for alt_path in ['/app/.env', '../.env', '~/.env']:
            expanded_path = os.path.expanduser(alt_path)
            if os.path.exists(expanded_path):
                env_path = expanded_path
                log.info(f"Found environment file at {env_path}")
                break
    
    # If env file exists, parse it
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Match domain entries
                    domain_match = domain_pattern.match(line)
                    if domain_match:
                        idx, domain = domain_match.groups()
                        # Strip whitespace and carriage returns
                        domains[idx] = domain.strip().replace('\r', '').replace('\n', '')
                        continue
                    
                    # Match API key entries
                    api_key_match = api_key_pattern.match(line)
                    if api_key_match:
                        idx, api_key = api_key_match.groups()
                        # Strip whitespace and carriage returns
                        api_keys[idx] = api_key.strip().replace('\r', '').replace('\n', '')
        except Exception as e:
            log.error(f"Error reading .env file: {e}")
    
    # Create pairs from matched domains and API keys
    for idx in sorted(domains.keys()):
        if idx in api_keys:
            pairs.append((domains[idx], api_keys[idx]))
            log.debug(f"Loaded configuration for domain: {domains[idx]}")
    
    return pairs

def print_menu():
    os.system('cls' if os.name == 'nt' else 'clear')
    hostname = socket.gethostname()
    print(r"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     STARFLEET DNS OPERATIONS CONSOLE                        ║
║                           "Make it so."                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Insert random welcome message here, with spacing
    welcome_msg = get_random_welcome_message()
    print(f"┌─ Message from Starfleet Command ─┐")
    print(f"│ {welcome_msg[:76]:<76} │")
    if len(welcome_msg) > 76:
        print(f"│ {welcome_msg[76:]:<76} │")
    print(f"└─{'─' * 76}─┘")
    print()
    
    try:
        discord_notifier.notify_custom("Welcome", welcome_msg)
    except Exception as e:
        log.debug(f"Failed to send welcome message to Discord: {str(e)}")
    
    print(f"USS ENTERPRISE NCC-1701-DNS [{hostname}]")
    print(f"Stardate: {time.strftime('%Y%m31.%H%M')}")
    print(f"Authenticated via: SSH Key")
    print("─" * 80)
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                           MAIN OPERATIONS MENU                              ║")
    print("╠══════════════════════════════════════════════════════════════════════════════╣")
    print("║  1. 🔍 Show DNS Status           │  5. ⏰ Show Update Schedule             ║")
    print("║     (Scan for anomalies)         │     (Current auto-update config)       ║")
    print("║                                  │                                         ║")
    print("║  2. 🔄 Update All Records        │  6. ⚙️  Modify Update Schedule          ║")
    print("║     (Sync with Starfleet Command)│     (Change frequency)                 ║")
    print("║                                  │                                         ║")
    print("║  3. 🎯 Update Single Record      │  7. 📋 Captain's Log                   ║")
    print("║     (Manual Override)            │     (View system logs)                 ║")
    print("║                                  │                                         ║")
    print("║  4. 🔧 Network Tools             │  8. 🚪 Exit Console                    ║")
    print("║     (Diagnostics & Testing)      │     (End Transmission)                 ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print()
    print("Enter your selection (1-8) or type 'help' for command reference:")
    print()

def network_tools_menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("""
--- Network Tools ---
1. Ping a host (ICMP echo)
2. Traceroute to a host (trace network path)
3. Nslookup a domain (DNS query)
4. Show current IP configuration (ip addr)
5. Show routing table (ip route)
6. Curl a URL (HTTP request)
7. Wget a URL (download test)
8. iperf3 (Test network bandwidth)
9. Back to main menu
""")
        choice = input("Select a tool: ").strip()
        if choice == "1":
            host = input("Enter host to ping: ").strip()
            print(f"\n--- ping {host} ---")
            subprocess.run(["ping", "-c", "4", host])
            input("Press Enter to continue...")
        elif choice == "2":
            host = input("Enter host for traceroute: ").strip()
            print(f"\n--- traceroute {host} ---")
            subprocess.run(["traceroute", host])
            input("Press Enter to continue...")
        elif choice == "3":
            domain = input("Enter domain for nslookup: ").strip()
            print(f"\n--- nslookup {domain} ---")
            subprocess.run(["nslookup", domain])
            input("Press Enter to continue...")
        elif choice == "4":
            print("\n--- ip addr ---")
            subprocess.run(["ip", "addr"])  # Use 'ip addr' instead of 'ifconfig'
            input("Press Enter to continue...")
        elif choice == "5":
            print("\n--- ip route ---")
            subprocess.run(["ip", "route"])  # Use 'ip route' instead of 'netstat -rn'
            input("Press Enter to continue...")
        elif choice == "6":
            url = input("Enter URL for curl: ").strip()
            print(f"\n--- curl {url} ---")
            subprocess.run(["curl", "-I", url])
            input("Press Enter to continue...")
        elif choice == "7":
            url = input("Enter URL for wget: ").strip()
            print(f"\n--- wget {url} ---")
            subprocess.run(["wget", "--spider", url]) # Use --spider to check, not download
            input("Press Enter to continue...")
        elif choice == "8":
            server_ip = input("Enter iperf3 server IP: ").strip()
            print(f"\n--- iperf3 client to {server_ip} ---")
            subprocess.run(["iperf3", "-c", server_ip])
            input("Press Enter to continue...")
        elif choice == "9":
            break
        else:
            print("Invalid choice.")
            input("Press Enter to continue...")

def get_env_pairs():
    """Get domain and API key pairs from environment or .env file"""
    # First try to get from environment variables
    pairs = []
    i = 1
    while True:
        domain = os.environ.get(f"DOMAIN{i}")
        api_key = os.environ.get(f"CF_API_KEY{i}")
        # Strip whitespace and carriage returns from env vars
        if domain:
            domain = domain.strip().replace('\r', '').replace('\n', '')
        if api_key:
            api_key = api_key.strip().replace('\r', '').replace('\n', '')
        if not domain or not api_key:
            break
        pairs.append((domain, api_key))
        log.debug(f"Loaded domain from environment variables: {domain}")
        i += 1

    # If no pairs found in environment, try reading from .env file
    if not pairs:
        log.debug("No domains found in environment variables, checking .env file")
        pairs = read_env_file()
    return pairs

def show_status(pairs):
    log.info("Performing DNS status check for all domains")
    print("\n--- Status ---")
    print("Scanning DNS records for configured domains...")

    # Get the container's public IP address
    try:
        container_ip_result = subprocess.run(
            ["curl", "-s", "https://icanhazip.com"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        container_public_ip = container_ip_result.stdout.strip()
        print(f"Container's Public IP: {container_public_ip}\n")
        log.info(f"Container's public IP: {container_public_ip}")
    except Exception as e:
        print(f"Error getting container's public IP: {str(e)}\n")
        log.error(f"Failed to get container's public IP: {str(e)}")

    for domain, api_key in pairs:
        domain_logger = get_domain_logger("picard", domain)
        domain_logger.info(f"Checking status for domain {domain}")
        print(f"Domain: {domain}")
        dns_ips = []
        # Try dig first
        try:
            dig_result = subprocess.run(["dig", "+short", domain, "A", "@1.1.1.1"], capture_output=True, text=True, timeout=5)
            dig_output = dig_result.stdout.strip()
            if dig_output:
                for line in dig_output.splitlines():
                    if re.match(r"^\d+\.\d+\.\d+\.\d+$", line):
                        dns_ips.append(line)
        except Exception:
            pass
        # If dig failed or not found, try nslookup
        if not dns_ips:
            try:
                nslookup_result = subprocess.run(["nslookup", domain, "1.1.1.1"], capture_output=True, text=True, timeout=5)
                nslookup_output = nslookup_result.stdout
                for line in nslookup_output.splitlines():
                    if re.match(r"^Address: +\d+\.\d+\.\d+\.\d+$", line) and "1.1.1.1" not in line:
                        ip = line.split(":")[1].strip()
                        dns_ips.append(ip)
            except Exception:
                pass
        # If still no result, try Google DNS API
        if not dns_ips:
            try:
                import requests
                resp = requests.get(f"https://dns.google/resolve?name={domain}&type=A", timeout=5)
                if resp.ok:
                    data = resp.json()
                    if "Answer" in data:
                        for answer in data["Answer"]:
                            if answer["type"] == 1:  # A record
                                dns_ips.append(answer["data"])
            except Exception:
                pass
        # Print results
        if dns_ips:
            print(f"  Current DNS IP(s): {', '.join(dns_ips)}")
            domain_logger.debug(f"Current DNS IP(s): {', '.join(dns_ips)}")
        else:
            print(f"  Current DNS IP: Unable to resolve (no A records)")
            domain_logger.warning(f"Unable to resolve DNS IP for {domain}")
        # Get current public IP
        try:
            ip_result = subprocess.run(["curl", "-s", "https://api.ipify.org"], capture_output=True, text=True, timeout=10)
            current_ip = ip_result.stdout.strip()
        except Exception:
            current_ip = "?"
        print(f"  Current Public IP: {current_ip}")
        domain_logger.debug(f"Current public IP: {current_ip}")
        # Check if DNS IP matches current public IP
        if container_public_ip in dns_ips:
            print(f"  Status: ✓ DNS matches container's IP")
            domain_logger.info(f"DNS record matches container's IP ({container_public_ip})")
        elif current_ip in dns_ips:
            print(f"  Status: ✓ DNS matches detected public IP")
            domain_logger.info(f"DNS record matches detected public IP ({current_ip})")
        else:
            print(f"  Status: ✗ DNS needs updating")
            domain_logger.warning(f"DNS needs updating - current DNS IP(s) {dns_ips} don't match public IP {current_ip}")
        print()
    input("Press Enter to continue...")

def get_cloudflare_records():
    """
    Retrieve all DNS records from Cloudflare for the configured domains.
    This is a placeholder implementation. Replace with actual API calls as needed.
    """
    # Example: Return a list of dummy records for demonstration
    # In production, replace this with actual Cloudflare API integration
    return [
        {"id": "1", "name": "example.com", "type": "A", "content": "1.2.3.4"},
        {"id": "2", "name": "www.example.com", "type": "A", "content": "1.2.3.4"},
    ]

def update_all():
    """Update all DNS records with the current public IP"""
    log.info("Starting update all records process")
    print("\n╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                           UPDATE ALL RECORDS                                ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    pairs = get_env_pairs()
    current_ip = get_public_ip()
    
    if not current_ip:
        print("❌ Failed to retrieve public IP address. Please try again later.")
        input("\nPress Enter to continue...")
        return
        
    if not pairs:
        print("❌ No domain/API key pairs found in configuration.")
        input("\nPress Enter to continue...")
        return
    
    print(f"🌐 Current Public IP: {current_ip}")
    print(f"📋 Processing {len(pairs)} domain(s)...")
    print()
    
    success_count = 0
    total_updates = 0
    
    for domain, api_key in pairs:
        print(f"🔄 Processing {domain}...")
        domain_success = True
        
        try:
            zone_id = get_zone_id(domain, api_key)
            if not zone_id:
                print(f"  ❌ Could not get zone ID for {domain}")
                continue
            
            # Update root domain A record
            print(f"  📍 Updating root domain: {domain}")
            success = upsert_dns_record(zone_id, domain, current_ip, api_key, 'A')
            total_updates += 1
            if success:
                print(f"    ✅ Root domain updated successfully")
            else:
                print(f"    ❌ Failed to update root domain")
                domain_success = False
            
            # Check if wildcard sync is enabled in config
            wildcard_sync_enabled = config_manager.get('wildcard_dns.sync_with_root', True)
            if wildcard_sync_enabled:
                # Update wildcard record
                wildcard_domain = f"*.{domain}"
                print(f"  🌟 Updating wildcard domain: {wildcard_domain}")
                success = upsert_dns_record(zone_id, wildcard_domain, current_ip, api_key, 'A')
                total_updates += 1
                if success:
                    print(f"    ✅ Wildcard domain updated successfully")
                else:
                    print(f"    ❌ Failed to update wildcard domain")
                    domain_success = False
            else:
                print(f"  ⚠️  Wildcard sync disabled - skipping *.{domain}")
                
            if domain_success:
                success_count += 1
                print(f"  🎉 {domain} processing completed successfully")
            else:
                print(f"  ⚠️  {domain} processing completed with errors")
                
        except Exception as e:
            print(f"  ❌ Failed to process {domain}: {str(e)}")
            log.error(f"Error processing {domain}: {str(e)}")
            
        print()  # Add spacing between domains
    
    print("─" * 80)
    print(f"📊 Update Summary:")
    print(f"   • Domains processed: {len(pairs)}")
    print(f"   • Successful domains: {success_count}")
    print(f"   • Total record updates attempted: {total_updates}")
    print(f"   • Current IP: {current_ip}")
    print("─" * 80)
    
    if success_count == len(pairs):
        print("🎉 All updates completed successfully!")
    elif success_count > 0:
        print("⚠️  Some updates completed with warnings/errors - check details above")
    else:
        print("❌ All updates failed - check your configuration and API keys")
    
    input("\nPress Enter to continue...")

def update_single_record():
    """Update a single DNS record with the current public IP"""
    log.info("Starting update single record process")
    print("\n--- Update Single Record ---")
    pairs = get_env_pairs()
    if not pairs:
        print("No DNS records found to update.")
        input("\nPress Enter to continue...")
        return
    print("\nAvailable Domains:")
    for i, (domain, _) in enumerate(pairs):
        print(f"{i + 1}. {domain}")
    selection = None
    while selection is None:
        try:
            input_val = input("\nSelect a domain to update (number) or 'c' to cancel: ")
            if input_val.lower() == 'c':
                return
            selection = int(input_val) - 1
            if selection < 0 or selection >= len(pairs):
                print("Invalid selection.")
                selection = None
        except ValueError:
            print("Please enter a valid number.")
    domain, api_key = pairs[selection]
    current_ip = get_public_ip()
    if not current_ip:
        print("Failed to retrieve public IP address. Please try again later.")
        input("\nPress Enter to continue...")
        return
    print(f"\nDetected public IP address: {current_ip}")
    confirm = input(f"\nUpdate {domain} to {current_ip}? (y/n): ")
    if confirm.lower() != 'y':
        return
    try:
        # upsert_dns_record(zone_id, domain, current_ip, api_key, 'A')
        print(f"(Stub) Would update {domain} to {current_ip}")
    except Exception as e:
        print(f"❌ Failed to update {domain}: {str(e)}")
    input("\nPress Enter to continue...")

def show_update_schedule():
    """Display the current cron schedule for the IP updater"""
    log.info("Displaying update schedule information")
    print("\n--- Current Automatic Update Schedule ---")
    
    try:
        # Import the config manager
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Get schedule from config
        cron_schedule = config_manager.get("cron_schedule", "*/10 * * * *")
        print(f"Current schedule: {cron_schedule}")
        log.debug(f"Current cron schedule from config file: {cron_schedule}")
        
        # Parse the cron expression
        minute, hour, day, month, weekday = cron_schedule.split()
        
        # Create a human-readable explanation
        explanation = "Currently scheduled "
        
        # Minute explanations
        if minute == "*":
            explanation += "every minute"
        elif minute.startswith("*/"):
            interval = minute.split("/")[1]
            explanation += f"every {interval} minutes"
        elif "," in minute:
            minutes = minute.split(",")
            explanation += f"at minute(s): {', '.join(minutes)}"
        else:
            explanation += f"at minute: {minute}"
            
        # Hour explanations    
        if hour == "*":
            explanation += " of every hour"
        elif hour.startswith("*/"):
            interval = hour.split("/")[1]
            explanation += f" every {interval} hours"
        elif "," in hour:
            hours = hour.split(",")
            explanation += f" during hour(s): {', '.join(hours)}"
        else:
            explanation += f" at hour: {hour}"
            
        # Day explanations
        if day != "*":
            explanation += f" on day(s) {day} of the month"
            
        # Month explanations    
        if month != "*":
            months_dict = {
                "1": "January", "2": "February", "3": "March", 
                "4": "April", "5": "May", "6": "June",
                "7": "July", "8": "August", "9": "September",
                "10": "October", "11": "November", "12": "December"
            }
            if "," in month:
                months_list = []
                for m in month.split(","):
                    months_list.append(months_dict.get(m, m))
                explanation += f" in {', '.join(months_list)}"
            else:
                explanation += f" in {months_dict.get(month, month)}"
                
        # Weekday explanations
        if weekday != "*":
            weekdays_dict = {
                "0": "Sunday", "1": "Monday", "2": "Tuesday", 
                "3": "Wednesday", "4": "Thursday", "5": "Friday", "6": "Saturday"
            }
            if "," in weekday:
                weekday_list = []
                for d in weekday.split(","):
                    if "-" in d:
                        start, end = d.split("-")
                        start_day = weekdays_dict.get(start, start)
                        end_day = weekdays_dict.get(end, end)
                        weekday_list.append(f"{start_day} through {end_day}")
                    else:
                        weekday_list.append(weekdays_dict.get(d, d))
                explanation += f" on {', '.join(weekday_list)}"
            elif "-" in weekday:
                start, end = weekday.split("-")
                start_day = weekdays_dict.get(start, start)
                end_day = weekdays_dict.get(end, end)
                explanation += f" on {start_day} through {end_day}"
            else:
                explanation += f" on {weekdays_dict.get(weekday, weekday)}"
        
        print(f"\n{explanation}")
        
        print("\n--- Schedule Explanation ---")
        
        # Minute explanations
        if minute == "*":
            print("• Runs every minute")
        elif minute.startswith("*/"):
            interval = minute.split("/")[1]
            print(f"• Runs every {interval} minutes")
        elif "," in minute:
            minutes = minute.split(",")
            print(f"• Runs at minute(s): {', '.join(minutes)}")
        else:
            print(f"• Runs at minute: {minute}")
            
        # Hour explanations    
        if hour == "*":
            print("• Every hour")
        elif hour.startswith("*/"):
            interval = hour.split("/")[1]
            print(f"• Every {interval} hours")
        elif "," in hour:
            hours = hour.split(",")
            print(f"• During hour(s): {', '.join(hours)}")
        else:
            print(f"• At hour: {hour}")
            
        # Day explanations
        if day != "*":
            print(f"• On day(s) of month: {day}")
            
        # Month explanations    
        if month != "*":
            if "," in month:
                months_list = []
                for m in month.split(","):
                    months_list.append(months_dict.get(m, m))
                print(f"• In month(s): {', '.join(months_list)}")
            else:
                print(f"• In month: {months_dict.get(month, month)}")
                
        # Weekday explanations
        if weekday != "*":
            if "," in weekday:
                weekday_list = []
                for d in weekday.split(","):
                    if "-" in d:
                        start, end = d.split("-")
                        start_day = weekdays_dict.get(start, start)
                        end_day = weekdays_dict.get(end, end)
                        weekday_list.append(f"{start_day} through {end_day}")
                    else:
                        weekday_list.append(weekdays_dict.get(d, d))
                print(f"• On: {', '.join(weekday_list)}")
            elif "-" in weekday:
                start, end = weekday.split("-")
                start_day = weekdays_dict.get(start, start)
                end_day = weekdays_dict.get(end, end)
                print(f"• On: {start_day} through {end_day}")
            else:
                print(f"• On: {weekdays_dict.get(weekday, weekday)}")
        
        # Display wildcard configuration status
        wildcard_sync = config_manager.get("wildcard_dns.sync_with_root", True)
        print("\n--- Wildcard DNS Configuration ---")
        if wildcard_sync:
            print("• Wildcard DNS sync: ENABLED")
            print("  (Wildcard records like *.loopey.net will automatically match their root domains)")
            
            # Show additional wildcard settings
            ttl_override = config_manager.get("wildcard_dns.ttl_override")
            if ttl_override:
                print(f"• Wildcard TTL override: {ttl_override} seconds")
            else:
                print("• Wildcard TTL: Same as root domain")
                
            match_proxy = config_manager.get("wildcard_dns.match_proxy_settings", True)
            if match_proxy:
                print("• Wildcard proxy settings: Match root domain")
            else:
                print("• Wildcard proxy settings: Always disabled")
        else:
            print("• Wildcard DNS sync: DISABLED")
            print("  (Wildcard records will not be automatically updated)")
            
    except Exception as e:
        log.error(f"Error retrieving configuration: {str(e)}")
        print("\nCould not determine the current schedule due to an error.")
        print("Default schedule is: */10 * * * * (every 10 minutes)")
    
    print("\n--- To Modify Settings ---")
    print("The schedule and wildcard configuration are now stored in:")
    print(f"  {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.yaml')}")
    print("\nYou can:")
    print("1. Edit the config.yaml file directly")
    print("2. Use the Picard console to manage settings (future update)")
    
    print("\nCron schedule format:")
    print("* * * * * = minute hour day month day-of-week")
    print("\nCommon examples:")
    print("*/5 * * * *   = every 5 minutes")
    print("*/10 * * * *  = every 10 minutes")
    print("0 */1 * * *   = every hour at minute 0")
    print("0 0 * * *     = every day at midnight")
      input("\nPress Enter to continue...")

def captain_log_viewer():
    """Advanced log viewing system with filtering and search capabilities"""
    logs_dir = "/app/logs"
    
    while True:
        os.system('clear')
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║                              CAPTAIN'S LOG                                  ║")
        print("║                        'Ship's Records & Archives'                          ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        
        # Get available log files
        log_files = []
        try:
            for file in os.listdir(logs_dir):
                if file.endswith('.log'):
                    log_path = os.path.join(logs_dir, file)
                    size = os.path.getsize(log_path)
                    modified = os.path.getmtime(log_path)
                    mod_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified))
                    log_files.append((file, size, mod_time, log_path))
        except Exception as e:
            print(f"❌ Error reading log directory: {str(e)}")
            log_files = []
        
        if not log_files:
            print("\n📁 No log files found in the ship's archives.")
            print("Logging may be disabled or no events have been recorded yet.")
            print("\nTo enable logging, ensure your Docker environment is configured correctly.")
            input("\nPress Enter to return to main console...")
            break
            
        print("\n--- Available Ship's Records ---")
        for i, (file, size, mod_time, _) in enumerate(log_files, 1):
            size_kb = size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            print(f"{i:2}. {file:<25} {size_str:<10} Modified: {mod_time}")
            
        print("\n--- Log Operations ---")
        print(f"{len(log_files) + 1:2}. 📊 View recent events (consolidated)")
        print(f"{len(log_files) + 2:2}. 🔍 Filter logs by severity")
        print(f"{len(log_files) + 3:2}. 🔎 Search all logs")
        print(f"{len(log_files) + 4:2}. 📈 System health summary")
        print(f"{len(log_files) + 5:2}. 🚪 Return to main console")
        
        choice = input("\nEnter your selection: ").strip()
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(log_files):
                # View specific log file
                view_log_file(log_files[choice_num - 1][3])
            elif choice_num == len(log_files) + 1:
                # View recent events (consolidated)
                view_recent_events(log_files)
            elif choice_num == len(log_files) + 2:
                # Filter logs by severity
                filter_logs_by_severity(log_files)
            elif choice_num == len(log_files) + 3:
                # Search logs
                search_logs(log_files)
            elif choice_num == len(log_files) + 4:
                # System health summary
                show_system_health_summary(log_files)
            elif choice_num == len(log_files) + 5:
                # Return to main menu
                break
            else:
                print("❌ Invalid selection.")
                input("Press Enter to continue...")
        except ValueError:
            print("❌ Please enter a valid number.")
            input("Press Enter to continue...")

def view_log_file(log_path, filter_level=None, search_term=None, max_lines=50):
    """View contents of a log file with optional filtering"""
    try:
        os.system('clear')
        
        file_name = os.path.basename(log_path)
        print(f"╔══════════════════════════════════════════════════════════════════════════════╗")
        print(f"║                              VIEWING: {file_name:<35} ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        
        if filter_level:
            print(f"🔍 Filtered to show {filter_level} level and above")
        if search_term:
            print(f"🔎 Showing only entries containing: '{search_term}'")
        
        print("\n" + "─" * 80 + "\n")
        
        # Define level priorities
        level_priority = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
        
        # Filter level we're looking for (if specified)
        min_priority = level_priority.get(filter_level.upper(), 0) if filter_level else 0
        
        # Read and filter log file
        matched_lines = []
        
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                # Apply search filter
                if search_term and search_term.lower() not in line.lower():
                    continue
                    
                # Apply level filter
                if filter_level:
                    line_priority = 0
                    for level, priority in level_priority.items():
                        if f"[{level}]" in line:
                            line_priority = priority
                            break
                    if line_priority < min_priority:
                        continue
                        
                matched_lines.append(line)
        
        # Display the most recent matching lines
        total_lines = len(matched_lines)
        if total_lines > max_lines:
            display_lines = matched_lines[-max_lines:]
            print(f"📊 Showing most recent {max_lines} of {total_lines} matching entries")
        else:
            display_lines = matched_lines
            print(f"📊 Showing all {total_lines} matching entries")
        
        print("─" * 80)
        
        for line in display_lines:
            # Color code log levels
            if "[WARNING]" in line:
                colored_line = f"\033[93m{line}\033[0m"  # Yellow
            elif "[ERROR]" in line or "[CRITICAL]" in line:
                colored_line = f"\033[91m{line}\033[0m"  # Red
            elif "[INFO]" in line:
                colored_line = f"\033[92m{line}\033[0m"  # Green
            elif "[DEBUG]" in line:
                colored_line = f"\033[94m{line}\033[0m"  # Blue
            else:
                colored_line = line
                
            print(colored_line)
        
        print("\n" + "─" * 80)
        print("Navigation: [F] Filter by level | [S] Search | [M] More lines | [Q] Return")
        
        # Interactive navigation
        while True:
            cmd = input("Command: ").lower().strip()
            if cmd == 'q':
                break
            elif cmd == 'f':
                # Filter by level
                levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                print("\nSelect minimum log level to show:")
                for i, level in enumerate(levels, 1):
                    print(f"{i}. {level}")
                try:
                    level_choice = int(input("Enter number (or 0 to show all): "))
                    if 1 <= level_choice <= len(levels):
                        view_log_file(log_path, levels[level_choice-1], search_term, max_lines)
                    elif level_choice == 0:
                        view_log_file(log_path, None, search_term, max_lines)
                except ValueError:
                    print("❌ Invalid input.")
                break
            elif cmd == 's':
                # Search within log
                term = input("Enter search term: ")
                if term:
                    view_log_file(log_path, filter_level, term, max_lines)
                break
            elif cmd == 'm':
                # Show more lines
                new_max = max_lines + 25
                view_log_file(log_path, filter_level, search_term, new_max)
                break
            else:
                print("❌ Invalid command. Use F, S, M, or Q.")
                
    except Exception as e:
        print(f"❌ Error reading log file: {str(e)}")
        
    input("\nPress Enter to return to log menu...")

def view_recent_events(log_files, max_events=50):
    """Show recent events across all log files"""
    try:
        os.system('clear')
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║                            RECENT SHIP'S ACTIVITY                           ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝")
        
        # Collect recent events from all logs
        all_events = []
        
        for _, _, _, log_path in log_files:
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse the timestamp from the log entry
                        try:
                            # Try to extract timestamp from various formats
                            if ' [' in line and '] ' in line:
                                timestamp_str = line.split(' [')[0].strip()
                                timestamp = time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                all_events.append((timestamp, line, os.path.basename(log_path)))
                        except (IndexError, ValueError):
                            # Skip lines that don't match the expected format
                            continue
            except Exception as e:
                print(f"⚠️  Error reading {os.path.basename(log_path)}: {str(e)}")
        
        # Sort events by timestamp (most recent first)
        all_events.sort(key=lambda x: x[0], reverse=True)
        
        # Display recent events
        display_events = all_events[:max_events]
        
        print(f"\n📊 Showing {len(display_events)} most recent events:")
        print("─" * 80)
        
        for timestamp, line, source_file in display_events:
            # Color code by log level
            if "[WARNING]" in line:
                colored_line = f"\033[93m{line}\033[0m"  # Yellow
            elif "[ERROR]" in line or "[CRITICAL]" in line:
                colored_line = f"\033[91m{line}\033[0m"  # Red
            elif "[INFO]" in line:
                colored_line = f"\033[92m{line}\033[0m"  # Green
            elif "[DEBUG]" in line:
                colored_line = f"\033[94m{line}\033[0m"  # Blue
            else:
                colored_line = line
            
            print(f"[{source_file}] {colored_line}")
        
        if len(all_events) > max_events:
            print(f"\n📝 ({len(all_events) - max_events} older events not shown)")
            
        print("\n" + "─" * 80)
        
    except Exception as e:
        print(f"❌ Error processing recent events: {str(e)}")
        
    input("\nPress Enter to return to log menu...")

def filter_logs_by_severity(log_files):
    """Filter logs by severity level"""
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    os.system('clear')
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                          FILTER LOGS BY SEVERITY                            ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    print("\nSelect minimum log level to show:")
    for i, level in enumerate(levels, 1):
        print(f"{i}. {level}")
    
    try:
        level_choice = int(input("\nEnter number: "))
        if 1 <= level_choice <= len(levels):
            selected_level = levels[level_choice-1]
            
            # Ask which log file to filter
            os.system('clear')
            print(f"🔍 Filtering by {selected_level} and above\n")
            print("Select log file to filter:")
            
            for i, (file, _, _, _) in enumerate(log_files, 1):
                print(f"{i}. {file}")
            print(f"{len(log_files) + 1}. All log files (consolidated)")
            
            file_choice = int(input("\nEnter number: "))
            if 1 <= file_choice <= len(log_files):
                # Filter specific log file
                view_log_file(log_files[file_choice-1][3], selected_level)
            elif file_choice == len(log_files) + 1:
                # Filter all logs (consolidated view)
                view_consolidated_logs(log_files, selected_level)
    except ValueError:
        print("❌ Invalid input.")
        input("Press Enter to continue...")

def search_logs(log_files):
    """Search all logs for a specific term"""
    os.system('clear')
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                              SEARCH SHIP'S LOGS                             ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    search_term = input("\n🔎 Enter search term: ").strip()
    if not search_term:
        print("❌ No search term provided.")
        input("Press Enter to continue...")
        return
    
    print(f"\n🔍 Searching for: '{search_term}'")
    print("─" * 80)
    
    total_matches = 0
    
    for file_name, _, _, log_path in log_files:
        try:
            matches = []
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if search_term.lower() in line.lower():
                        matches.append((line_num, line.strip()))
            
            if matches:
                print(f"\n📁 {file_name} ({len(matches)} matches):")
                for line_num, line in matches[-10:]:  # Show last 10 matches
                    # Color code by log level
                    if "[WARNING]" in line:
                        colored_line = f"\033[93m{line}\033[0m"  # Yellow
                    elif "[ERROR]" in line or "[CRITICAL]" in line:
                        colored_line = f"\033[91m{line}\033[0m"  # Red
                    elif "[INFO]" in line:
                        colored_line = f"\033[92m{line}\033[0m"  # Green
                    elif "[DEBUG]" in line:
                        colored_line = f"\033[94m{line}\033[0m"  # Blue
                    else:
                        colored_line = line
                    
                    print(f"  {line_num:4}: {colored_line}")
                
                if len(matches) > 10:
                    print(f"    ... ({len(matches) - 10} more matches not shown)")
                
                total_matches += len(matches)
                
        except Exception as e:
            print(f"❌ Error searching {file_name}: {str(e)}")
    
    print(f"\n📊 Total matches found: {total_matches}")
    input("\nPress Enter to return to log menu...")

def view_consolidated_logs(log_files, filter_level=None):
    """View logs from all files consolidated and sorted by timestamp"""
    try:
        os.system('clear')
        
        title = "╔══════════════════════════════════════════════════════════════════════════════╗\n"
        title += "║                          CONSOLIDATED SHIP'S RECORDS                        ║\n"
        if filter_level:
            title += f"║                            (Filtered to {filter_level}+)                             ║\n"
        title += "╚══════════════════════════════════════════════════════════════════════════════╝"
        print(title)
        
        # Define level priorities
        level_priority = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
        
        # Filter level we're looking for (if specified)
        min_priority = level_priority.get(filter_level.upper(), 0) if filter_level else 0
        
        # Collect entries from all log files
        all_entries = []
        
        for file_name, _, _, log_path in log_files:
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        if filter_level:
                            # Check log level
                            line_priority = 0
                            for level, priority in level_priority.items():
                                if f"[{level}]" in line:
                                    line_priority = priority
                                    break
                            if line_priority < min_priority:
                                continue
                        
                        # Parse timestamp
                        try:
                            if ' [' in line and '] ' in line:
                                timestamp_str = line.split(' [')[0].strip()
                                timestamp = time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                all_entries.append((timestamp, line, file_name))
                        except (IndexError, ValueError):
                            # Skip lines that don't match expected format
                            continue
                            
            except Exception as e:
                print(f"❌ Error reading {file_name}: {str(e)}")
        
        # Sort by timestamp (most recent first)
        all_entries.sort(key=lambda x: x[0], reverse=True)
        
        # Display entries
        max_display = 100
        display_entries = all_entries[:max_display]
        
        print(f"\n📊 Showing {len(display_entries)} most recent entries:")
        print("─" * 80)
        
        for timestamp, line, source_file in display_entries:
            # Color code by log level
            if "[WARNING]" in line:
                colored_line = f"\033[93m{line}\033[0m"  # Yellow
            elif "[ERROR]" in line or "[CRITICAL]" in line:
                colored_line = f"\033[91m{line}\033[0m"  # Red
            elif "[INFO]" in line:
                colored_line = f"\033[92m{line}\033[0m"  # Green
            elif "[DEBUG]" in line:
                colored_line = f"\033[94m{line}\033[0m"  # Blue
            else:
                colored_line = line
            
            print(f"[{source_file}] {colored_line}")
        
        if len(all_entries) > max_display:
            print(f"\n📝 ({len(all_entries) - max_display} older entries not shown)")
            
        print("\n" + "─" * 80)
        
    except Exception as e:
        print(f"❌ Error processing consolidated logs: {str(e)}")
        
    input("\nPress Enter to return to log menu...")

def show_system_health_summary(log_files):
    """Show a summary of system health based on log analysis"""
    os.system('clear')
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                            SYSTEM HEALTH SUMMARY                            ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    # Initialize counters
    total_events = 0
    debug_count = 0
    info_count = 0
    warning_count = 0
    error_count = 0
    critical_count = 0
    
    recent_events = []
    dns_updates = 0
    api_failures = 0
    
    # Analyze logs
    for file_name, _, _, log_path in log_files:
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    total_events += 1
                    
                    # Count by log level
                    if "[DEBUG]" in line:
                        debug_count += 1
                    elif "[INFO]" in line:
                        info_count += 1
                    elif "[WARNING]" in line:
                        warning_count += 1
                    elif "[ERROR]" in line:
                        error_count += 1
                    elif "[CRITICAL]" in line:
                        critical_count += 1
                    
                    # Count specific events
                    if "DNS update" in line or "Updated A" in line:
                        dns_updates += 1
                    if "API" in line and ("error" in line.lower() or "failed" in line.lower()):
                        api_failures += 1
                    
                    # Collect recent events (last 24 hours worth)
                    try:
                        if ' [' in line and '] ' in line:
                            timestamp_str = line.split(' [')[0].strip()
                            timestamp = time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            event_time = time.mktime(timestamp)
                            current_time = time.time()
                            
                            if current_time - event_time < 86400:  # 24 hours
                                recent_events.append((timestamp, line))
                    except:
                        pass
                        
        except Exception as e:
            print(f"❌ Error analyzing {file_name}: {str(e)}")
    
    print("\n--- Event Summary ---")
    print(f"📊 Total logged events: {total_events:,}")
    print(f"🐛 Debug messages: {debug_count:,}")
    print(f"ℹ️  Info messages: {info_count:,}")
    print(f"⚠️  Warnings: {warning_count:,}")
    print(f"❌ Errors: {error_count:,}")
    print(f"🚨 Critical events: {critical_count:,}")
    
    print("\n--- DNS Operations ---")
    print(f"🔄 DNS updates performed: {dns_updates:,}")
    print(f"🌐 API failures detected: {api_failures:,}")
    
    # Calculate health score
    total_issues = warning_count + error_count + critical_count
    if total_events > 0:
        health_percentage = max(0, 100 - ((total_issues / total_events) * 100))
    else:
        health_percentage = 100
    
    print("\n--- System Health Status ---")
    if health_percentage >= 95:
        status_emoji = "🟢"
        status_text = "EXCELLENT"
        status_color = "\033[92m"  # Green
    elif health_percentage >= 85:
        status_emoji = "🟡"
        status_text = "GOOD"
        status_color = "\033[93m"  # Yellow
    elif health_percentage >= 70:
        status_emoji = "🟠"
        status_text = "FAIR"
        status_color = "\033[93m"  # Yellow
    else:
        status_emoji = "🔴"
        status_text = "NEEDS ATTENTION"
        status_color = "\033[91m"  # Red
    
    print(f"{status_emoji} System Health: {status_color}{health_percentage:.1f}% - {status_text}\033[0m")
    
    print(f"\n--- Recent Activity (Last 24 Hours) ---")
    print(f"📈 Recent events: {len(recent_events):,}")
    
    if recent_events:
        # Sort by timestamp (most recent first)
        recent_events.sort(key=lambda x: x[0], reverse=True)
        
        print("\n🔍 Latest events:")
        for i, (timestamp, line) in enumerate(recent_events[:5]):
            # Color code by log level
            if "[WARNING]" in line:
                colored_line = f"\033[93m{line}\033[0m"  # Yellow
            elif "[ERROR]" in line or "[CRITICAL]" in line:
                colored_line = f"\033[91m{line}\033[0m"  # Red
            elif "[INFO]" in line:
                colored_line = f"\033[92m{line}\033[0m"  # Green
            else:
                colored_line = line
            
            print(f"  {colored_line}")
        
        if len(recent_events) > 5:
            print(f"  ... and {len(recent_events) - 5} more recent events")
    
    print("\n" + "─" * 80)
    input("Press Enter to return to log menu...")

def improve_dns_status_display():
    """Improved DNS status display with better formatting and anomaly detection"""
    os.system('clear')
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║                           DNS ANOMALY SCANNER                               ║")
    print("║                      'Scanning for temporal anomalies'                      ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    
    pairs = get_env_pairs()
    
    if not pairs:
        print("\n❌ No domain configuration found.")
        print("Please ensure your environment variables or config files are set up correctly.")
        input("\nPress Enter to continue...")
        return
    
    print(f"\n🔍 Scanning {len(pairs)} configured domain(s) for anomalies...")
    print("─" * 80)
    
    # Get container's public IP for comparison
    try:
        container_ip_result = subprocess.run(["curl", "-s", "https://api.ipify.org"], 
                                           capture_output=True, text=True, timeout=10)
        container_public_ip = container_ip_result.stdout.strip()
        print(f"🌐 Container's Public IP: {container_public_ip}")
    except Exception:
        container_public_ip = "Unable to determine"
        print(f"🌐 Container's Public IP: {container_public_ip}")
    
    log.info(f"Container's public IP: {container_public_ip}")
    print("─" * 80)
    
    anomalies_found = 0
    all_good = True
    
    for domain, api_key in pairs:
        domain_logger = get_domain_logger(domain)
        log.info(f"Checking status for domain {domain}")
        domain_logger.info(f"Checking status for domain {domain}")
        
        print(f"\n🔎 Analyzing: {domain}")
        
        # Get DNS information
        dns_ips = []
        wildcard_ips = []
        
        try:
            # Check root domain
            result = subprocess.run(["dig", "+short", domain], capture_output=True, text=True, timeout=10)
            for line in result.stdout.strip().split('\n'):
                if line and '.' in line and not line.startswith(';'):
                    # Basic IP validation
                    parts = line.split('.')
                    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                        dns_ips.append(line)
            
            # Check wildcard domain
            wildcard_domain = f"*.{domain}"
            wildcard_result = subprocess.run(["dig", "+short", f"test.{domain}"], capture_output=True, text=True, timeout=10)
            for line in wildcard_result.stdout.strip().split('\n'):
                if line and '.' in line and not line.startswith(';'):
                    # Basic IP validation
                    parts = line.split('.')
                    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                        wildcard_ips.append(line)
                        
        except Exception as e:
            dns_ips = []
            wildcard_ips = []
            print(f"  ❌ DNS query failed: {str(e)}")
            domain_logger.error(f"DNS query failed: {str(e)}")
            anomalies_found += 1
            all_good = False
            continue
        
        # Analyze results
        print(f"  📋 Root domain DNS IPs: {', '.join(dns_ips) if dns_ips else 'None found'}")
        print(f"  🌟 Wildcard DNS IPs: {', '.join(wildcard_ips) if wildcard_ips else 'None found'}")
        
        domain_logger.debug(f"Root domain DNS IPs: {dns_ips}")
        domain_logger.debug(f"Wildcard DNS IPs: {wildcard_ips}")
        
        # Check for anomalies
        status_indicators = []
        
        # Anomaly 1: No DNS records found
        if not dns_ips:
            status_indicators.append("❌ No A records found for root domain")
            anomalies_found += 1
            all_good = False
            domain_logger.warning("No A records found for root domain")
        
        # Anomaly 2: IP mismatch with container
        if dns_ips and container_public_ip != "Unable to determine":
            if container_public_ip not in dns_ips:
                status_indicators.append(f"⚠️  DNS IP doesn't match container IP")
                anomalies_found += 1
                all_good = False
                domain_logger.warning(f"DNS IP mismatch - DNS: {dns_ips}, Container: {container_public_ip}")
            else:
                status_indicators.append("✅ DNS matches container IP")
                domain_logger.info(f"DNS record matches container IP ({container_public_ip})")
        
        # Anomaly 3: Root and wildcard mismatch
        if dns_ips and wildcard_ips:
            if set(dns_ips) != set(wildcard_ips):
                status_indicators.append("⚠️  Root and wildcard IPs don't match")
                anomalies_found += 1
                all_good = False
                domain_logger.warning(f"Root/wildcard mismatch - Root: {dns_ips}, Wildcard: {wildcard_ips}")
            else:
                status_indicators.append("✅ Root and wildcard IPs match")
                domain_logger.info("Root and wildcard IPs are synchronized")
        elif dns_ips and not wildcard_ips:
            status_indicators.append("ℹ️  No wildcard records configured")
            domain_logger.info("No wildcard records found")
        
        # Anomaly 4: Multiple different IPs (could indicate load balancing or misconfiguration)
        if len(set(dns_ips)) > 1:
            status_indicators.append("ℹ️  Multiple IPs detected (load balancing?)")
            domain_logger.info(f"Multiple IPs detected: {dns_ips}")
        
        # Display status
        for status in status_indicators:
            print(f"    {status}")
        
        print()
    
    # Summary
    print("─" * 80)
    if all_good and anomalies_found == 0:
        print("🎉 SCAN COMPLETE - All systems nominal!")
        print("   No temporal anomalies detected in the DNS grid.")
        print("   The Enterprise is operating within normal parameters.")
        log.info("DNS scan completed - no anomalies detected")
    else:
        print(f"⚠️  SCAN COMPLETE - {anomalies_found} anomal{'y' if anomalies_found == 1 else 'ies'} detected!")
        print("   Recommend immediate review of DNS configuration.")
        print("   Consider running option 2 (Update All Records) to resolve issues.")
        log.warning(f"DNS scan completed - {anomalies_found} anomalies detected")
    
    print("─" * 80)
    input("\nPress Enter to continue...")

def main():
    """Main function to run the command interface."""
    print_welcome()
    session_start_time = time.time()  # Record session start time
    
    while True:
        print_menu()  # Display the menu each time
        command = input("Captain> ").strip().lower()
        
        # Handle exit commands
        if command in ["exit", "quit", "8"]:
            # Calculate session duration
            session_duration = int(time.time() - session_start_time)
            
            # Format duration as hours:minutes:seconds
            hours, remainder = divmod(session_duration, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration_str = f"{hours:02}:{minutes:02}:{seconds:02}"
            
            # Log the exit
            log.info(f"User exited. Session duration: {duration_str}")
            
            # Send Discord notification for exit
            try:
                # Get username if available
                username = os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'
                
                # Send notification with formatted duration
                discord_notifier.notify_exit(username, duration_str)
            except Exception as e:
                log.error(f"Failed to send exit notification: {str(e)}")
                
            exit_msg = get_random_exit_message()
            print("\n" + "="*80)
            print("🖖 Exiting Starfleet DNS Console. Live long and prosper.")
            print(exit_msg)
            print("="*80 + "\n")
            try:
                discord_notifier.notify_custom("Exit", exit_msg)
            except Exception as e:
                log.error(f"Failed to send exit message to Discord: {str(e)}")
            sys.exit(0)
        
        # Handle menu selection commands
        elif command in ["menu", "help", "?"]:
            continue  # Menu will be displayed at top of loop
          # Handle numeric and text commands
        elif command in ["1", "status"]:
            improve_dns_status_display()
        elif command in ["2", "update", "update all"]:
            update_all()
        elif command in ["3", "update single"]:
            update_single_record()
        elif command in ["4", "tools", "network", "network tools"]:
            network_tools_menu()        elif command in ["5", "schedule", "show schedule"]:
            show_update_schedule()
        elif command in ["6", "modify schedule", "change schedule"]:
            print("🚧 Modify update schedule: (Not yet implemented)")
            input("Press Enter to continue...")
        elif command in ["7", "logs", "log", "captain's log"]:
            captain_log_viewer()
        else:
            print("❌ Unknown command. Please enter a number (1-8) or type 'help'.")
            log.warning(f"Invalid command entered: {command}")
            input("Press Enter to continue...")
            time.sleep(1)

if __name__ == "__main__":
    main()