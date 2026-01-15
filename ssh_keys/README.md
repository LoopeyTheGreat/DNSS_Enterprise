# SSH Keys for DNSS Enterprise

This directory stores the SSH public keys for systems authorized to access the DNSS Enterprise container.

## How to Add Your SSH Key

1. Generate an SSH key if you don't have one:
   ```
   ssh-keygen -t ed25519 -C "your_name@your_system.com"
   ```

2. Copy your public key (`.pub` file) to this directory

3. When building the container, all `.pub` files in this directory will be added to the authorized keys

## Security Note

* Only public keys (`.pub` files) should be placed in this directory
* Never commit private keys to a repository
* The `.gitignore` file is set to ignore all `.pub` files in this directory to prevent accidental commits