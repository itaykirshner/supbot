# Security Quick Reference

## 🚀 **Quick Setup**

### **1. Generate Secrets (macOS/Linux)**
```bash
# Make script executable
chmod +x scripts/setup-secrets.sh

# Run setup script
./scripts/setup-secrets.sh
```

### **2. Generate Secrets (Windows)**
```powershell
# Run PowerShell script
.\scripts\setup-secrets.ps1

# Or with force flag
.\scripts\setup-secrets.ps1 -Force
```

### **3. Manual Setup**
```bash
# Copy template
cp kubernetes/secrets.yaml.template kubernetes/secrets.yaml

# Edit with your credentials
nano kubernetes/secrets.yaml

# Encode values to base64
echo -n "your-secret" | base64
```

## 🔐 **Base64 Encoding**

### **macOS/Linux**
```bash
echo -n "your-secret-value" | base64
```

### **Windows PowerShell**
```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("your-secret-value"))
```

### **Online Tool**
- [Base64 Encode/Decode](https://www.base64encode.org/)

## 📋 **Required Credentials**

### **Slack App**
- **App Token**: `xapp-...` (from Slack API dashboard)
- **Bot Token**: `xoxb-...` (from Slack API dashboard)

### **LLM API**
- **Endpoint**: Your LLM service URL
- **API Key**: Optional authentication key

### **Confluence**
- **URL**: `https://yourcompany.atlassian.net`
- **Username**: Your email address
- **API Token**: From Atlassian account settings
- **Cloud ID**: From Confluence REST API

### **Jira**
- **URL**: Same as Confluence (if using Atlassian Cloud)
- **Username**: Same as Confluence
- **API Token**: Same as Confluence

### **Zoho Desk**
- **Client ID**: From Zoho OAuth application
- **Client Secret**: From Zoho OAuth application
- **Refresh Token**: Generated OAuth token
- **Org ID**: Your Zoho organization ID

## 🛡️ **Security Commands**

### **Check Secrets**
```bash
# List all secrets
kubectl get secrets -n bot-infra

# View specific secret
kubectl describe secret slack-app-secrets -n bot-infra

# Decode secret value
kubectl get secret slack-app-secrets -n bot-infra -o jsonpath='{.data.SLACK_APP_TOKEN}' | base64 -d
```

### **Apply Secrets**
```bash
# Apply secrets
kubectl apply -f kubernetes/secrets.yaml

# Verify application
kubectl logs -n bot-infra -l app=slack-app
```

### **Rotate Secrets**
```bash
# Update secret
kubectl patch secret slack-app-secrets -n bot-infra -p '{"data":{"SLACK_APP_TOKEN":"<new-base64-value>"}}'

# Restart application
kubectl rollout restart deployment/slack-app -n bot-infra
```

## 🔍 **Validation**

### **Check Base64 Encoding**
```bash
# Test encoding
echo "test" | base64 | base64 -d
# Should output: test
```

### **Verify Secret Format**
```bash
# Check YAML syntax
kubectl apply -f kubernetes/secrets.yaml --dry-run=client

# Validate secret structure
kubectl get secret slack-app-secrets -n bot-infra -o yaml
```

## 🚨 **Security Warnings**

### **❌ Never Do This**
- Commit `secrets.yaml` to Git
- Share secrets in plain text
- Use default passwords
- Expose admin interfaces publicly

### **✅ Always Do This**
- Use base64 encoding for secrets
- Rotate credentials regularly
- Monitor access logs
- Follow least privilege principle

## 📚 **Quick Links**

- **Setup Guide**: [SECRETS_SETUP.md](SECRETS_SETUP.md)
- **Security Checklist**: [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md)
- **Kubernetes Deployment**: [KUBERNETES_DEPLOYMENT.md](KUBERNETES_DEPLOYMENT.md)

## 🆘 **Troubleshooting**

### **Common Issues**

1. **Base64 Encoding Error**
   ```bash
   # Check encoding
   echo "your-value" | base64 | base64 -d
   ```

2. **Secret Not Found**
   ```bash
   # Check namespace
   kubectl get secrets -n bot-infra
   
   # Check secret name
   kubectl describe secret slack-app-secrets -n bot-infra
   ```

3. **Authentication Failed**
   ```bash
   # Check logs
   kubectl logs -n bot-infra -l app=slack-app
   
   # Verify secret values
   kubectl get secret slack-app-secrets -n bot-infra -o jsonpath='{.data.SLACK_APP_TOKEN}' | base64 -d
   ```

4. **Permission Denied**
   ```bash
   # Check RBAC
   kubectl get rolebinding -n bot-infra
   
   # Check service account
   kubectl get serviceaccount -n bot-infra
   ```

## 🔧 **Emergency Procedures**

### **Revoke Access**
```bash
# Delete secrets
kubectl delete secret slack-app-secrets -n bot-infra

# Restart application
kubectl rollout restart deployment/slack-app -n bot-infra
```

### **Update Credentials**
```bash
# Update secret
kubectl patch secret slack-app-secrets -n bot-infra -p '{"data":{"SLACK_APP_TOKEN":"<new-value>"}}'

# Restart application
kubectl rollout restart deployment/slack-app -n bot-infra
```

### **Rollback Changes**
```bash
# Rollback deployment
kubectl rollout undo deployment/slack-app -n bot-infra

# Check status
kubectl rollout status deployment/slack-app -n bot-infra
```

Remember: **Security is everyone's responsibility!**
