#!/bin/bash

# Secrets Setup Script for Slack Bot with RAG Integration
# This script helps you set up Kubernetes secrets securely

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to encode to base64
encode_base64() {
    echo -n "$1" | base64
}

# Function to validate base64
validate_base64() {
    if echo "$1" | base64 -d > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check if secrets.yaml already exists
if [ -f "kubernetes/secrets.yaml" ]; then
    print_warning "secrets.yaml already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Exiting without changes."
        exit 0
    fi
fi

print_status "Setting up Kubernetes secrets for Slack Bot with RAG Integration"
echo

# Copy template
print_status "Copying secrets template..."
cp kubernetes/secrets.yaml.template kubernetes/secrets.yaml
print_success "Template copied to kubernetes/secrets.yaml"

echo
print_status "Please provide the following credentials:"
echo

# Slack App Configuration
echo "=== SLACK APP CONFIGURATION ==="
read -p "Slack App Token (xapp-...): " SLACK_APP_TOKEN
read -p "Slack Bot Token (xoxb-...): " SLACK_BOT_TOKEN

# LLM Configuration
echo
echo "=== LLM API CONFIGURATION ==="
read -p "LLM API Endpoint: " LLM_API_ENDPOINT
read -p "LLM API Key (optional, press Enter to skip): " LLM_API_KEY

# Confluence Configuration
echo
echo "=== CONFLUENCE CONFIGURATION ==="
read -p "Confluence URL: " CONFLUENCE_URL
read -p "Confluence Username: " CONFLUENCE_USERNAME
read -p "Confluence API Token: " CONFLUENCE_API_TOKEN
read -p "Confluence Cloud ID: " CONFLUENCE_CLOUD_ID

# Jira Configuration
echo
echo "=== JIRA CONFIGURATION ==="
read -p "Jira URL: " JIRA_URL
read -p "Jira Username: " JIRA_USERNAME
read -p "Jira API Token: " JIRA_API_TOKEN

# Zoho Desk Configuration
echo
echo "=== ZOHO DESK CONFIGURATION ==="
read -p "Zoho Client ID: " ZOHO_CLIENT_ID
read -p "Zoho Client Secret: " ZOHO_CLIENT_SECRET
read -p "Zoho Refresh Token: " ZOHO_REFRESH_TOKEN
read -p "Zoho Org ID: " ZOHO_ORG_ID

echo
print_status "Encoding credentials to base64..."

# Encode all values
SLACK_APP_TOKEN_B64=$(encode_base64 "$SLACK_APP_TOKEN")
SLACK_BOT_TOKEN_B64=$(encode_base64 "$SLACK_BOT_TOKEN")
LLM_API_ENDPOINT_B64=$(encode_base64 "$LLM_API_ENDPOINT")
LLM_API_KEY_B64=$(encode_base64 "$LLM_API_KEY")
CONFLUENCE_URL_B64=$(encode_base64 "$CONFLUENCE_URL")
CONFLUENCE_USERNAME_B64=$(encode_base64 "$CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN_B64=$(encode_base64 "$CONFLUENCE_API_TOKEN")
CONFLUENCE_CLOUD_ID_B64=$(encode_base64 "$CONFLUENCE_CLOUD_ID")
JIRA_URL_B64=$(encode_base64 "$JIRA_URL")
JIRA_USERNAME_B64=$(encode_base64 "$JIRA_USERNAME")
JIRA_API_TOKEN_B64=$(encode_base64 "$JIRA_API_TOKEN")
ZOHO_CLIENT_ID_B64=$(encode_base64 "$ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET_B64=$(encode_base64 "$ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN_B64=$(encode_base64 "$ZOHO_REFRESH_TOKEN")
ZOHO_ORG_ID_B64=$(encode_base64 "$ZOHO_ORG_ID")

print_success "All credentials encoded to base64"

# Update secrets.yaml
print_status "Updating secrets.yaml file..."

# Use sed to replace placeholders (works on both macOS and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/<base64-encoded-slack-app-token>/$SLACK_APP_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-slack-bot-token>/$SLACK_BOT_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-llm-api-endpoint>/$LLM_API_ENDPOINT_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-llm-api-key-or-empty>/$LLM_API_KEY_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-confluence-url>/$CONFLUENCE_URL_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-confluence-username>/$CONFLUENCE_USERNAME_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-confluence-api-token>/$CONFLUENCE_API_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-confluence-cloud-id>/$CONFLUENCE_CLOUD_ID_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-jira-url>/$JIRA_URL_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-jira-username>/$JIRA_USERNAME_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-jira-api-token>/$JIRA_API_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-zoho-client-id>/$ZOHO_CLIENT_ID_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-zoho-client-secret>/$ZOHO_CLIENT_SECRET_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-zoho-refresh-token>/$ZOHO_REFRESH_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i '' "s/<base64-encoded-zoho-org-id>/$ZOHO_ORG_ID_B64/g" kubernetes/secrets.yaml
else
    # Linux
    sed -i "s/<base64-encoded-slack-app-token>/$SLACK_APP_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-slack-bot-token>/$SLACK_BOT_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-llm-api-endpoint>/$LLM_API_ENDPOINT_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-llm-api-key-or-empty>/$LLM_API_KEY_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-confluence-url>/$CONFLUENCE_URL_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-confluence-username>/$CONFLUENCE_USERNAME_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-confluence-api-token>/$CONFLUENCE_API_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-confluence-cloud-id>/$CONFLUENCE_CLOUD_ID_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-jira-url>/$JIRA_URL_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-jira-username>/$JIRA_USERNAME_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-jira-api-token>/$JIRA_API_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-zoho-client-id>/$ZOHO_CLIENT_ID_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-zoho-client-secret>/$ZOHO_CLIENT_SECRET_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-zoho-refresh-token>/$ZOHO_REFRESH_TOKEN_B64/g" kubernetes/secrets.yaml
    sed -i "s/<base64-encoded-zoho-org-id>/$ZOHO_ORG_ID_B64/g" kubernetes/secrets.yaml
fi

print_success "secrets.yaml updated with your credentials"

# Validate the file
print_status "Validating secrets.yaml..."

# Check if all placeholders were replaced
if grep -q "<base64-encoded-" kubernetes/secrets.yaml; then
    print_error "Some placeholders were not replaced. Please check the file manually."
    exit 1
fi

print_success "All placeholders replaced successfully"

# Test base64 encoding
print_status "Testing base64 encoding..."
if validate_base64 "$SLACK_APP_TOKEN_B64" && validate_base64 "$SLACK_BOT_TOKEN_B64"; then
    print_success "Base64 encoding validation passed"
else
    print_error "Base64 encoding validation failed"
    exit 1
fi

echo
print_success "Secrets setup completed successfully!"
echo
print_status "Next steps:"
echo "1. Review the generated kubernetes/secrets.yaml file"
echo "2. Apply the secrets to your Kubernetes cluster:"
echo "   kubectl apply -f kubernetes/secrets.yaml"
echo "3. Verify the secrets were created:"
echo "   kubectl get secrets -n bot-infra"
echo "4. Deploy your application:"
echo "   kubectl apply -f kubernetes/"
echo
print_warning "Remember: Never commit kubernetes/secrets.yaml to version control!"
echo
print_status "For more information, see SECRETS_SETUP.md"
