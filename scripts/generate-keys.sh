#!/bin/bash

# ===================================
# SecureTempMail - Key Generator
# ===================================
# Generates secure encryption keys for production deployment
# Usage: bash scripts/generate-keys.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Header
echo -e "${BLUE}"
echo "===================================="
echo "  SecureTempMail Key Generator"
echo "===================================="
echo -e "${NC}"
echo ""

# Check if openssl is available
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: openssl is not installed!${NC}"
    echo "Please install openssl first:"
    echo "  Ubuntu/Debian: sudo apt-get install openssl"
    echo "  macOS: brew install openssl"
    echo "  Windows: Download from https://slproweb.com/products/Win32OpenSSL.html"
    exit 1
fi

echo -e "${GREEN}Generating secure encryption keys...${NC}"
echo ""

# Generate keys
SECRET_KEY=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)

# Display keys
echo -e "${YELLOW}Copy these values to your .env file:${NC}"
echo ""
echo "# ==================================="
echo "# SECURITY KEYS (KEEP SECRET!)"
echo "# ==================================="
echo "SECRET_KEY=$SECRET_KEY"
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"
echo "API_KEY=$API_KEY"
echo ""
echo "# ==================================="
echo "# DATABASE PASSWORDS"
echo "# ==================================="
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
echo ""

# Security warning
echo -e "${RED}"
echo "===================================="
echo "  SECURITY WARNING!"
echo "===================================="
echo -e "${NC}"
echo -e "${YELLOW}⚠️  NEVER share or commit these keys!${NC}"
echo -e "${YELLOW}⚠️  Add .env to your .gitignore${NC}"
echo -e "${YELLOW}⚠️  Store backups securely${NC}"
echo -e "${YELLOW}⚠️  Rotate keys regularly${NC}"
echo ""

# Optional: Save to file
read -p "Save keys to .env.local? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ENV_FILE=".env.local"
    
    # Create backup if file exists
    if [ -f "$ENV_FILE" ]; then
        BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${YELLOW}Backing up existing file to $BACKUP_FILE${NC}"
        cp "$ENV_FILE" "$BACKUP_FILE"
    fi
    
    # Write keys to file
    cat > "$ENV_FILE" << EOF
# ===================================
# SECURITY KEYS (KEEP SECRET!)
# Generated: $(date)
# ===================================
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
API_KEY=$API_KEY

# ===================================
# DATABASE PASSWORDS
# ===================================
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
EOF
    
    echo -e "${GREEN}✓ Keys saved to $ENV_FILE${NC}"
    echo -e "${YELLOW}Remember to merge with your full .env configuration!${NC}"
else
    echo -e "${BLUE}Keys not saved. Copy them manually.${NC}"
fi

echo ""
echo -e "${GREEN}Done!${NC}"