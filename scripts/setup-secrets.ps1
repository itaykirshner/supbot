# Secrets Setup Script for Slack Bot with RAG Integration (Windows PowerShell)
# This script helps you set up Kubernetes secrets securely

param(
    [switch]$Force
)

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to encode to base64
function Encode-Base64 {
    param([string]$Value)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    return [Convert]::ToBase64String($bytes)
}

# Function to validate base64
function Test-Base64 {
    param([string]$Value)
    try {
        [Convert]::FromBase64String($Value) | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Check if secrets.yaml already exists
if (Test-Path "kubernetes/secrets.yaml") {
    if (-not $Force) {
        Write-Warning "secrets.yaml already exists!"
        $overwrite = Read-Host "Do you want to overwrite it? (y/N)"
        if ($overwrite -notmatch "^[Yy]$") {
            Write-Status "Exiting without changes."
            exit 0
        }
    }
}

Write-Status "Setting up Kubernetes secrets for Slack Bot with RAG Integration"
Write-Host ""

# Copy template
Write-Status "Copying secrets template..."
Copy-Item "kubernetes/secrets.yaml.template" "kubernetes/secrets.yaml"
Write-Success "Template copied to kubernetes/secrets.yaml"

Write-Host ""
Write-Status "Please provide the following credentials:"
Write-Host ""

# Slack App Configuration
Write-Host "=== SLACK APP CONFIGURATION ===" -ForegroundColor Cyan
$SLACK_APP_TOKEN = Read-Host "Slack App Token (xapp-...)"
$SLACK_BOT_TOKEN = Read-Host "Slack Bot Token (xoxb-...)"

# LLM Configuration
Write-Host ""
Write-Host "=== LLM API CONFIGURATION ===" -ForegroundColor Cyan
$LLM_API_ENDPOINT = Read-Host "LLM API Endpoint"
$LLM_API_KEY = Read-Host "LLM API Key (optional, press Enter to skip)"

# Confluence Configuration
Write-Host ""
Write-Host "=== CONFLUENCE CONFIGURATION ===" -ForegroundColor Cyan
$CONFLUENCE_URL = Read-Host "Confluence URL"
$CONFLUENCE_USERNAME = Read-Host "Confluence Username"
$CONFLUENCE_API_TOKEN = Read-Host "Confluence API Token"
$CONFLUENCE_CLOUD_ID = Read-Host "Confluence Cloud ID"

# Jira Configuration
Write-Host ""
Write-Host "=== JIRA CONFIGURATION ===" -ForegroundColor Cyan
$JIRA_URL = Read-Host "Jira URL"
$JIRA_USERNAME = Read-Host "Jira Username"
$JIRA_API_TOKEN = Read-Host "Jira API Token"

# Zoho Desk Configuration
Write-Host ""
Write-Host "=== ZOHO DESK CONFIGURATION ===" -ForegroundColor Cyan
$ZOHO_CLIENT_ID = Read-Host "Zoho Client ID"
$ZOHO_CLIENT_SECRET = Read-Host "Zoho Client Secret"
$ZOHO_REFRESH_TOKEN = Read-Host "Zoho Refresh Token"
$ZOHO_ORG_ID = Read-Host "Zoho Org ID"

Write-Host ""
Write-Status "Encoding credentials to base64..."

# Encode all values
$SLACK_APP_TOKEN_B64 = Encode-Base64 $SLACK_APP_TOKEN
$SLACK_BOT_TOKEN_B64 = Encode-Base64 $SLACK_BOT_TOKEN
$LLM_API_ENDPOINT_B64 = Encode-Base64 $LLM_API_ENDPOINT
$LLM_API_KEY_B64 = Encode-Base64 $LLM_API_KEY
$CONFLUENCE_URL_B64 = Encode-Base64 $CONFLUENCE_URL
$CONFLUENCE_USERNAME_B64 = Encode-Base64 $CONFLUENCE_USERNAME
$CONFLUENCE_API_TOKEN_B64 = Encode-Base64 $CONFLUENCE_API_TOKEN
$CONFLUENCE_CLOUD_ID_B64 = Encode-Base64 $CONFLUENCE_CLOUD_ID
$JIRA_URL_B64 = Encode-Base64 $JIRA_URL
$JIRA_USERNAME_B64 = Encode-Base64 $JIRA_USERNAME
$JIRA_API_TOKEN_B64 = Encode-Base64 $JIRA_API_TOKEN
$ZOHO_CLIENT_ID_B64 = Encode-Base64 $ZOHO_CLIENT_ID
$ZOHO_CLIENT_SECRET_B64 = Encode-Base64 $ZOHO_CLIENT_SECRET
$ZOHO_REFRESH_TOKEN_B64 = Encode-Base64 $ZOHO_REFRESH_TOKEN
$ZOHO_ORG_ID_B64 = Encode-Base64 $ZOHO_ORG_ID

Write-Success "All credentials encoded to base64"

# Update secrets.yaml
Write-Status "Updating secrets.yaml file..."

# Read the file content
$content = Get-Content "kubernetes/secrets.yaml" -Raw

# Replace all placeholders
$content = $content -replace "<base64-encoded-slack-app-token>", $SLACK_APP_TOKEN_B64
$content = $content -replace "<base64-encoded-slack-bot-token>", $SLACK_BOT_TOKEN_B64
$content = $content -replace "<base64-encoded-llm-api-endpoint>", $LLM_API_ENDPOINT_B64
$content = $content -replace "<base64-encoded-llm-api-key-or-empty>", $LLM_API_KEY_B64
$content = $content -replace "<base64-encoded-confluence-url>", $CONFLUENCE_URL_B64
$content = $content -replace "<base64-encoded-confluence-username>", $CONFLUENCE_USERNAME_B64
$content = $content -replace "<base64-encoded-confluence-api-token>", $CONFLUENCE_API_TOKEN_B64
$content = $content -replace "<base64-encoded-confluence-cloud-id>", $CONFLUENCE_CLOUD_ID_B64
$content = $content -replace "<base64-encoded-jira-url>", $JIRA_URL_B64
$content = $content -replace "<base64-encoded-jira-username>", $JIRA_USERNAME_B64
$content = $content -replace "<base64-encoded-jira-api-token>", $JIRA_API_TOKEN_B64
$content = $content -replace "<base64-encoded-zoho-client-id>", $ZOHO_CLIENT_ID_B64
$content = $content -replace "<base64-encoded-zoho-client-secret>", $ZOHO_CLIENT_SECRET_B64
$content = $content -replace "<base64-encoded-zoho-refresh-token>", $ZOHO_REFRESH_TOKEN_B64
$content = $content -replace "<base64-encoded-zoho-org-id>", $ZOHO_ORG_ID_B64

# Write the updated content back to the file
Set-Content "kubernetes/secrets.yaml" -Value $content

Write-Success "secrets.yaml updated with your credentials"

# Validate the file
Write-Status "Validating secrets.yaml..."

# Check if all placeholders were replaced
if ($content -match "<base64-encoded-") {
    Write-Error "Some placeholders were not replaced. Please check the file manually."
    exit 1
}

Write-Success "All placeholders replaced successfully"

# Test base64 encoding
Write-Status "Testing base64 encoding..."
if ((Test-Base64 $SLACK_APP_TOKEN_B64) -and (Test-Base64 $SLACK_BOT_TOKEN_B64)) {
    Write-Success "Base64 encoding validation passed"
} else {
    Write-Error "Base64 encoding validation failed"
    exit 1
}

Write-Host ""
Write-Success "Secrets setup completed successfully!"
Write-Host ""
Write-Status "Next steps:"
Write-Host "1. Review the generated kubernetes/secrets.yaml file"
Write-Host "2. Apply the secrets to your Kubernetes cluster:"
Write-Host "   kubectl apply -f kubernetes/secrets.yaml"
Write-Host "3. Verify the secrets were created:"
Write-Host "   kubectl get secrets -n bot-infra"
Write-Host "4. Deploy your application:"
Write-Host "   kubectl apply -f kubernetes/"
Write-Host ""
Write-Warning "Remember: Never commit kubernetes/secrets.yaml to version control!"
Write-Host ""
Write-Status "For more information, see SECRETS_SETUP.md"
