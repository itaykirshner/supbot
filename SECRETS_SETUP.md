# Secrets Setup Guide

This guide explains how to set up the Kubernetes secrets for the Slack bot with RAG integration.

## 🔐 **Security Overview**

- **`secrets.yaml.template`** - Template file (safe to commit to Git)
- **`secrets.yaml`** - Actual secrets file (NEVER commit to Git)
- **All values must be base64 encoded** for Kubernetes secrets

## 📋 **Setup Steps**

### **1. Copy the Template**

```bash
cp kubernetes/secrets.yaml.template kubernetes/secrets.yaml
```

### **2. Get Your Credentials**

#### **Slack App Credentials**
1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Select your app or create a new one
3. Go to **OAuth & Permissions**
4. Copy the **App-Level Token** (starts with `xapp-`)
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

#### **LLM API Configuration**
- **Endpoint**: Your LLM service URL (e.g., `http://your-llm-service:8080/v1/chat/completions`)
- **API Key**: Optional, if your LLM service requires authentication

#### **Confluence Credentials**
1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create a new API token
3. Get your Confluence URL (e.g., `https://yourcompany.atlassian.net`)
4. Get your Cloud ID from [Confluence REST API](https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-about/)

#### **Jira Credentials**
1. Use the same API token from Confluence
2. Use the same URL as Confluence (if using Atlassian Cloud)

#### **Zoho Desk Credentials**
1. Go to [https://desk.zoho.com/DeskAPIDocument#Authentication](https://desk.zoho.com/DeskAPIDocument#Authentication)
2. Create a new OAuth application
3. Get Client ID, Client Secret, and generate Refresh Token
4. Get your Organization ID from Zoho Desk

### **3. Encode Values to Base64**

**On macOS/Linux:**
```bash
echo -n "your-secret-value" | base64
```

**On Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-secret-value"))
```

**Example:**
```bash
# Slack App Token
echo -n "xapp-1-A09AP8KLH8D-9368818578404-0dac6aaa472b6d83771fc77e3f2403d81def42afdfaa60059c9085e01639ebe5" | base64
# Output: eGFwcC0xLUEwOUFQOEtMSDhELTkzNjg4MTg1Nzg0MDQtMGRhYzZhYWE0NzJiNmQ4Mzc3MWZjNzdlM2YyNDAzZDgxZGVmNDJhZmRmYWE2MDA1OWM5MDg1ZTAxNjM5ZWJlNQ==

# Slack Bot Token
echo -n "xoxb-3934850236-9368831584148-TrAuU5eJ2c2nVMuFO6ozQlkR" | base64
# Output: eG94Yi0zOTM0ODUwMjM2LTkzNjg4MzE1ODQxNDgtVHJBdVU1ZUoyYzJuVk11Rk82b3pRbGtS
```

### **4. Update secrets.yaml**

Replace all `<base64-encoded-...>` placeholders with your actual base64-encoded values:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: slack-app-secrets
  namespace: bot-infra
type: Opaque
data:
  SLACK_APP_TOKEN: eGFwcC0xLUEwOUFQOEtMSDhELTkzNjg4MTg1Nzg0MDQtMGRhYzZhYWE0NzJiNmQ4Mzc3MWZjNzdlM2YyNDAzZDgxZGVmNDJhZmRmYWE2MDA1OWM5MDg1ZTAxNjM5ZWJlNQ==
  SLACK_BOT_TOKEN: eG94Yi0zOTM0ODUwMjM2LTkzNjg4MzE1ODQxNDgtVHJBdVU1ZUoyYzJuVk11Rk82b3pRbGtS
  LLM_API_ENDPOINT: aHR0cDovL251Y2xpby1tbHJ1bi12bGxtLW15LXZsbG0ubWxydW4uc3ZjLmNsdXN0ZXIubG9jYWw6ODA4MC92MS9jaGF0L2NvbXBsZXRpb25z
  LLM_API_KEY: 
  # ... continue with other secrets
```

## 🚨 **Security Best Practices**

### **1. Never Commit Secrets**
```bash
# Add to .gitignore
echo "kubernetes/secrets.yaml" >> .gitignore
echo "*.env" >> .gitignore
echo "secrets/" >> .gitignore
```

### **2. Use Environment-Specific Secrets**
- **Development**: Use test credentials
- **Staging**: Use staging credentials  
- **Production**: Use production credentials

### **3. Rotate Secrets Regularly**
- **API Tokens**: Rotate every 90 days
- **OAuth Tokens**: Rotate when expired
- **Passwords**: Rotate every 60 days

### **4. Use Kubernetes Secret Management**
Consider using external secret management tools:
- **AWS Secrets Manager** with External Secrets Operator
- **HashiCorp Vault** with Vault Agent
- **Azure Key Vault** with External Secrets Operator

## 🔧 **Validation**

### **1. Check Base64 Encoding**
```bash
# Decode to verify
echo "eGFwcC0xLUEwOUFQOEtMSDhELTkzNjg4MTg1Nzg0MDQtMGRhYzZhYWE0NzJiNmQ4Mzc3MWZjNzdlM2YyNDAzZDgxZGVmNDJhZmRmYWE2MDA1OWM5MDg1ZTAxNjM5ZWJlNQ==" | base64 -d
# Should output: xapp-1-A09AP8KLH8D-9368818578404-0dac6aaa472b6d83771fc77e3f2403d81def42afdfaa60059c9085e01639ebe5
```

### **2. Test Secret Deployment**
```bash
# Apply secrets
kubectl apply -f kubernetes/secrets.yaml

# Verify secrets are created
kubectl get secrets -n bot-infra

# Check specific secret
kubectl describe secret slack-app-secrets -n bot-infra
```

### **3. Test Application**
```bash
# Check if app can read secrets
kubectl logs -n bot-infra -l app=slack-app | grep "Bot User ID"
```

## 📝 **Troubleshooting**

### **Common Issues**

1. **Base64 Encoding Errors**
   - Ensure no newlines in encoded values
   - Use `echo -n` to prevent trailing newlines

2. **Secret Not Found**
   - Check namespace: `kubectl get secrets -n bot-infra`
   - Verify secret name matches deployment

3. **Authentication Failures**
   - Verify credentials are correct
   - Check if tokens are expired
   - Ensure proper permissions

4. **Encoding Issues**
   - Use UTF-8 encoding for special characters
   - Test decode/encode cycle

### **Debug Commands**

```bash
# Check secret contents (base64 encoded)
kubectl get secret slack-app-secrets -n bot-infra -o yaml

# Decode secret value
kubectl get secret slack-app-secrets -n bot-infra -o jsonpath='{.data.SLACK_APP_TOKEN}' | base64 -d

# Check pod environment
kubectl exec -n bot-infra deployment/slack-app -- env | grep SLACK
```

## 🔄 **Secret Rotation**

### **1. Update Secret**
```bash
# Update the secret value
kubectl patch secret slack-app-secrets -n bot-infra -p '{"data":{"SLACK_APP_TOKEN":"<new-base64-value>"}}'
```

### **2. Restart Application**
```bash
# Restart to pick up new secret
kubectl rollout restart deployment/slack-app -n bot-infra
```

### **3. Verify Update**
```bash
# Check if new secret is being used
kubectl logs -n bot-infra -l app=slack-app | grep "Bot User ID"
```

## 📚 **Additional Resources**

- [Kubernetes Secrets Documentation](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Slack API Authentication](https://api.slack.com/authentication)
- [Confluence REST API Authentication](https://developer.atlassian.com/cloud/confluence/rest/v1/api-group-about/)
- [Jira REST API Authentication](https://developer.atlassian.com/cloud/jira/platform/rest/v2/intro/#authentication)
- [Zoho Desk API Authentication](https://desk.zoho.com/DeskAPIDocument#Authentication)

Remember: **Never commit the actual `secrets.yaml` file to version control!**
