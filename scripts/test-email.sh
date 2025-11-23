#!/bin/bash

# ===================================
# SecureTempMail - Email Tester
# ===================================
# Sends a test email to verify SMTP server functionality
# Usage: bash scripts/test-email.sh [smtp_host] [smtp_port] <to_address>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SMTP_HOST=${1:-localhost}
SMTP_PORT=${2:-8025}
TO_ADDRESS=$3

# Header
echo -e "${BLUE}"
echo "===================================="
echo "  SecureTempMail Email Tester"
echo "===================================="
echo -e "${NC}"
echo ""

# Validate arguments
if [ -z "$TO_ADDRESS" ]; then
    echo -e "${RED}Error: Missing recipient address!${NC}"
    echo ""
    echo "Usage: $0 [smtp_host] [smtp_port] <to_address>"
    echo ""
    echo "Examples:"
    echo "  $0 localhost 8025 test@yourdomain.com"
    echo "  $0 mail.example.com 25 tmp_abc123@example.com"
    echo ""
    exit 1
fi

echo -e "${YELLOW}Configuration:${NC}"
echo "  SMTP Host: $SMTP_HOST"
echo "  SMTP Port: $SMTP_PORT"
echo "  To Address: $TO_ADDRESS"
echo ""

# Check if swaks is available, otherwise use alternative
if command -v swaks &> /dev/null; then
    echo -e "${GREEN}Using swaks to send test email...${NC}"
    echo ""
    
    # Send email using swaks
    swaks \
        --to "$TO_ADDRESS" \
        --from "test@securetempmail.local" \
        --server "$SMTP_HOST:$SMTP_PORT" \
        --header "Subject: Test Email - $(date '+%Y-%m-%d %H:%M:%S')" \
        --body "This is a test email sent from SecureTempMail test script.\n\nTimestamp: $(date)\nSMTP Server: $SMTP_HOST:$SMTP_PORT\nRecipient: $TO_ADDRESS\n\nIf you received this, your SMTP server is working correctly!"
    
    echo ""
    echo -e "${GREEN}✓ Email sent successfully!${NC}"
    
elif command -v python3 &> /dev/null; then
    echo -e "${YELLOW}swaks not found, using Python...${NC}"
    echo ""
    
    # Send email using Python
    python3 << EOF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Create message
msg = MIMEMultipart()
msg['From'] = 'test@securetempmail.local'
msg['To'] = '$TO_ADDRESS'
msg['Subject'] = f'Test Email - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

body = f"""This is a test email sent from SecureTempMail test script.

Timestamp: {datetime.now()}
SMTP Server: $SMTP_HOST:$SMTP_PORT
Recipient: $TO_ADDRESS

If you received this, your SMTP server is working correctly!
"""

msg.attach(MIMEText(body, 'plain'))

# Send email
try:
    server = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT)
    server.sendmail('test@securetempmail.local', '$TO_ADDRESS', msg.as_string())
    server.quit()
    print('Email sent successfully!')
except Exception as e:
    print(f'Error sending email: {e}')
    exit(1)
EOF
    
    echo ""
    echo -e "${GREEN}✓ Email sent successfully!${NC}"
    
elif command -v nc &> /dev/null || command -v netcat &> /dev/null; then
    echo -e "${YELLOW}Using netcat to send email...${NC}"
    echo ""
    
    # Determine netcat command
    NC_CMD="nc"
    if ! command -v nc &> /dev/null; then
        NC_CMD="netcat"
    fi
    
    # Send email using netcat
    (echo "HELO test.local"
     sleep 0.5
     echo "MAIL FROM: <test@securetempmail.local>"
     sleep 0.5
     echo "RCPT TO: <$TO_ADDRESS>"
     sleep 0.5
     echo "DATA"
     sleep 0.5
     echo "From: test@securetempmail.local"
     echo "To: $TO_ADDRESS"
     echo "Subject: Test Email - $(date '+%Y-%m-%d %H:%M:%S')"
     echo ""
     echo "This is a test email sent from SecureTempMail test script."
     echo ""
     echo "Timestamp: $(date)"
     echo "SMTP Server: $SMTP_HOST:$SMTP_PORT"
     echo "Recipient: $TO_ADDRESS"
     echo ""
     echo "If you received this, your SMTP server is working correctly!"
     echo "."
     sleep 0.5
     echo "QUIT") | $NC_CMD $SMTP_HOST $SMTP_PORT
    
    echo ""
    echo -e "${GREEN}✓ Email sent successfully!${NC}"
    
else
    echo -e "${RED}Error: No suitable email sending tool found!${NC}"
    echo ""
    echo "Please install one of the following:"
    echo "  - swaks: apt-get install swaks (recommended)"
    echo "  - python3: apt-get install python3"
    echo "  - netcat: apt-get install netcat"
    echo ""
    exit 1
fi

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Check the inbox at: http://localhost:8000"
echo "  2. Or use the API:"
echo "     curl http://localhost:8000/api/v1/inboxes/{inbox_id}/messages \\"
echo "       -H 'Authorization: Bearer {token}'"
echo ""
echo -e "${YELLOW}Note: It may take a few seconds for the email to appear.${NC}"
echo ""