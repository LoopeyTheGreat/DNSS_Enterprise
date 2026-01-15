#!/bin/bash

# UFW Firewall Configuration Script
# Allows connections from detected LAN subnet to port 1701
# Author: DNSS Enterprise
# Date: $(date)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if UFW is installed
check_ufw() {
    if ! command -v ufw &> /dev/null; then
        error "UFW is not installed. Please install it first:"
        echo "  Ubuntu/Debian: sudo apt install ufw"
        echo "  CentOS/RHEL: sudo yum install ufw"
        exit 1
    fi
}

# Detect LAN subnet
detect_lan_subnet() {
    log "Detecting LAN subnet..."
    
    # Get the default route interface
    DEFAULT_INTERFACE=$(ip route | grep '^default' | awk '{print $5}' | head -n1)
    
    if [[ -z "$DEFAULT_INTERFACE" ]]; then
        error "Could not detect default network interface"
        exit 1
    fi
    
    log "Default interface: $DEFAULT_INTERFACE"
    
    # Get the subnet for the default interface
    LAN_SUBNET=$(ip route | grep "$DEFAULT_INTERFACE" | grep -E '192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.' | awk '{print $1}' | head -n1)
    
    # Fallback method if first method doesn't work
    if [[ -z "$LAN_SUBNET" ]]; then
        LAN_SUBNET=$(ip addr show "$DEFAULT_INTERFACE" | grep 'inet ' | awk '{print $2}' | grep -E '192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.' | head -n1)
        if [[ -n "$LAN_SUBNET" ]]; then
            # Convert IP/CIDR to network/CIDR
            LAN_SUBNET=$(ipcalc-ng "$LAN_SUBNET" --network 2>/dev/null | grep -E '^[0-9]' || echo "$LAN_SUBNET" | cut -d'/' -f1,2)
        fi
    fi
    
    # Additional fallback - try to get from route table
    if [[ -z "$LAN_SUBNET" ]]; then
        LAN_SUBNET=$(ip route | grep "$DEFAULT_INTERFACE" | grep 'scope link' | awk '{print $1}' | head -n1)
    fi
    
    if [[ -z "$LAN_SUBNET" ]]; then
        error "Could not automatically detect LAN subnet"
        echo "Please manually specify your LAN subnet (e.g., 192.168.1.0/24):"
        read -p "LAN Subnet: " LAN_SUBNET
        
        if [[ -z "$LAN_SUBNET" ]]; then
            error "No subnet provided. Exiting."
            exit 1
        fi
    fi
    
    log "Detected LAN subnet: $LAN_SUBNET"
}

# Configure UFW rules
configure_firewall() {
    log "Configuring UFW firewall rules..."
    
    # Enable UFW if not already enabled
    log "Enabling UFW..."
    ufw --force enable
    
    # Set default policies
    log "Setting default policies..."
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (important to not lock yourself out)
    log "Allowing SSH access..."
    ufw allow ssh
    
    # Allow connections from LAN subnet to port 1701
    log "Allowing connections from $LAN_SUBNET to port 1701..."
    ufw allow from "$LAN_SUBNET" to any port 1701
    
    # Allow connections from LAN subnet to port 1701 UDP (in case needed)
    log "Allowing UDP connections from $LAN_SUBNET to port 1701..."
    ufw allow from "$LAN_SUBNET" to any port 1701 proto udp
    
    # Allow loopback
    log "Allowing loopback connections..."
    ufw allow from 127.0.0.0/8
    
    # Show status
    log "Current UFW status:"
    ufw status numbered
}

# Backup existing UFW rules
backup_rules() {
    BACKUP_DIR="/etc/ufw/backup"
    BACKUP_FILE="$BACKUP_DIR/ufw_rules_backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    log "Creating backup of existing UFW rules..."
    mkdir -p "$BACKUP_DIR"
    
    if [[ -d "/etc/ufw" ]]; then
        tar -czf "$BACKUP_FILE" -C /etc ufw/ 2>/dev/null || warning "Could not create backup"
        if [[ -f "$BACKUP_FILE" ]]; then
            success "Backup created: $BACKUP_FILE"
        fi
    fi
}

# Main function
main() {
    log "Starting UFW Firewall Configuration for DNSS Enterprise"
    log "This script will allow connections from your LAN subnet to port 1701"
    echo
    
    # Checks
    check_root
    check_ufw
    
    # Create backup
    backup_rules
    
    # Detect network
    detect_lan_subnet
    
    # Confirm with user
    echo
    warning "About to configure firewall with the following settings:"
    echo "  - LAN Subnet: $LAN_SUBNET"
    echo "  - Allow port: 1701 (TCP and UDP)"
    echo "  - Default policy: Deny incoming, Allow outgoing"
    echo
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Operation cancelled by user"
        exit 0
    fi
    
    # Configure firewall
    configure_firewall
    
    echo
    success "UFW firewall configuration completed successfully!"
    success "Port 1701 is now accessible from LAN subnet: $LAN_SUBNET"
    
    log "To manually add additional subnets, use:"
    echo "  sudo ufw allow from <subnet> to any port 1701"
    
    log "To remove a rule, use:"
    echo "  sudo ufw delete <rule_number>"
    
    log "To check firewall status:"
    echo "  sudo ufw status numbered"
}

# Run main function
main "$@"