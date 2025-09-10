# Slack Bot RAG Solution - File Structure & Purpose Guide

This document explains what each file does in the modular RAG solution for your Slack bot.

## 📁 **Directory Structure & File Purposes**

### **slack-app/** - Main Slack Bot Application
```
slack-app/
├── Dockerfile           # Container image for Slack bot
├── requirements.txt     # Python dependencies for bot
├── app.py              # Main Slack bot application
├── config.py           # Configuration management
└── health.py           # Health check HTTP endpoints
```

**📄 `app.py`** - The heart of your Slack bot
- Handles Slack events (mentions, DMs)
- Imports and uses the RAG module for enhanced responses  
- Manages conversation history and context
- Processes LLM requests in background threads
- Deletes "thinking" messages after getting responses

**📄 `config.py`** - Centralized configuration
- Loads environment variables with defaults
- Validates required settings on startup
- Provides single source of truth for all settings

**📄 `health.py`** - Kubernetes health checks
- `/health` endpoint for liveness probes
- `/ready` endpoint for readiness probes
- Checks Slack connection and RAG system status
- Runs HTTP server on port 8080 for Kubernetes

### **rag-module/** - Reusable RAG Library
```
rag-module/
├── __init__.py         # Module exports
├── rag_client.py       # ChromaDB client and search
├── embeddings.py       # Text embedding generation
└── utils.py            # Text processing utilities
```

**📄 `rag_client.py`** - Vector database operations
- Connects to your ChromaDB service
- Adds documents (single or batch)
- Searches for relevant context given a query
- Manages collections and health checks

**📄 `embeddings.py`** - Text to vector conversion
- Uses sentence-transformers model
- Generates embeddings for text chunks
- Handles batch processing for efficiency
- Caches model to avoid reloading

**📄 `utils.py`** - Text processing helpers
- Cleans HTML content from Confluence
- Splits text into overlapping chunks
- Formats Confluence/Jira data for storage
- Handles text normalization

### **sync-job/** - Data Ingestion CronJob
```
sync-job/
├── Dockerfile          # Container image for sync job
├── requirements.txt    # Python dependencies
├── sync_data.py        # Main sync orchestrator
├── confluence_client.py # Confluence API client
├── jira_client.py      # Jira API client  
└── data_processor.py   # Content processing
```

**📄 `sync_data.py`** - Orchestrates the nightly sync
- Main entry point for CronJob
- Coordinates Confluence and Jira sync
- Manages incremental vs full sync
- Handles batching and error recovery
- Reports sync statistics

**📄 `confluence_client.py`** - Confluence API wrapper
- Connects to Confluence REST API
- Fetches spaces, pages, and content
- Handles pagination and rate limits
- Gets recently updated pages for incremental sync

**📄 `jira_client.py`** - Jira API wrapper  
- Connects to Jira REST API
- Fetches resolved issues for knowledge base
- Builds JQL queries for filtering
- Handles authentication and timeouts

**📄 `data_processor.py`** - Content transformation
- Converts HTML to clean text
- Chunks large documents for better retrieval
- Formats metadata for vector storage
- Handles both Confluence and Jira content

### **kubernetes/** - Deployment Manifests
```
kubernetes/
├── namespace.yaml      # Creates bot-infra namespace
├── configmaps.yaml     # Non-secret configuration
├── secrets.yaml.template # Secret values template
├── slack-app/
│   ├── deployment.yaml # Slack bot pod definition
│   ├── service.yaml    # Service for health checks
│   └── hpa.yaml        # Horizontal pod autoscaler
├── sync-job/
│   └── cronjob.yaml    # Nightly sync job definition
└── rbac/
    ├── serviceaccount.yaml # Service account
    ├── role.yaml          # RBAC permissions  
    └── rolebinding.yaml   # Permission bindings
```

**📄 `namespace.yaml`** - Creates isolated environment
- Defines `bot-infra` namespace for all resources

**📄 `configmaps.yaml`** - Non-sensitive configuration
- Bot settings (timeouts, limits, features)
- Sync job configuration (schedules, spaces)
- ChromaDB connection details

**📄 `secrets.yaml.template`** - Sensitive data template
- Slack tokens, API keys (you fill these in)
- Confluence/Jira credentials
- LLM API endpoints

**📄 `slack-app/deployment.yaml`** - Bot pod specification
- Always-running Slack bot container
- Resource limits and health checks
- Environment variables from configs/secrets

**📄 `sync-job/cronjob.yaml`** - Scheduled sync job
- Runs every night at 2 AM UTC
- One-time job pods for data ingestion
- Failure handling and history limits

### **Build & Deployment Scripts**
```
├── Makefile            # Build/deploy commands
├── deploy.sh           # Automated deployment script
├── docker-compose.yaml # Local development stack
└── README.md           # Documentation
```

**📄 `Makefile`** - Convenient commands
- `make build` - Build Docker images
- `make deploy-all` - Deploy everything to K8s
- `make logs-app` - View Slack bot logs
- `make run-sync-now` - Trigger manual sync

**📄 `deploy.sh`** - Full deployment automation
- Builds and pushes Docker images
- Deploys all Kubernetes resources
- Waits for readiness and verifies health
- Shows next steps and useful commands

**📄 `docker-compose.yaml`** - Local development
- Runs ChromaDB, Slack bot locally
- Useful for testing before K8s deployment
- Includes volume mounts for persistence

## 🔄 **How They Work Together**

### **Runtime Flow:**
1. **User mentions bot** → `slack-app/app.py` receives event
2. **Query processing** → `rag-module/rag_client.py` searches ChromaDB  
3. **Context retrieval** → `rag-module/embeddings.py` generates query embedding
4. **LLM enhancement** → Context injected into LLM prompt
5. **Response delivery** → Enhanced answer posted to Slack

### **Sync Flow:**
1. **CronJob triggers** → `sync-job/sync_data.py` starts
2. **Confluence fetch** → `confluence_client.py` gets updated pages
3. **Content processing** → `data_processor.py` cleans and chunks text
4. **Vector storage** → `rag-module/rag_client.py` adds to ChromaDB
5. **Completion** → Job reports success/failure stats

### **Deployment Flow:**
1. **Build images** → `Dockerfile`s create containers
2. **Push to registry** → Images available to Kubernetes
3. **Deploy manifests** → `kubernetes/` files create resources
4. **Health checks** → `health.py` confirms everything running
5. **Ready to serve** → Bot responds with RAG-enhanced answers

## 📋 **File Dependencies**

### **Import Relationships:**
```
slack-app/app.py
  ├── imports config.py
  ├── imports health.py  
  └── imports rag-module/
      ├── rag_client.py
      ├── embeddings.py
      └── utils.py

sync-job/sync_data.py
  ├── imports confluence_client.py
  ├── imports jira_client.py
  ├── imports data_processor.py
  └── imports rag-module/
      ├── rag_client.py
      ├── embeddings.py
      └── utils.py
```

### **Configuration Flow:**
```
kubernetes/secrets.yaml → Environment Variables → config.py → app.py
kubernetes/configmaps.yaml → Environment Variables → config.py → app.py
```

## 🎯 **Key Design Principles**

### **Separation of Concerns**
- Each file has a single, clear responsibility
- Business logic separated from infrastructure concerns
- Reusable components (rag-module) shared between services

### **Configuration Management**
- All secrets in Kubernetes secrets
- All config in ConfigMaps or environment variables
- No hardcoded values in application code

### **Error Handling**
- Graceful degradation when RAG is unavailable
- Comprehensive logging for debugging
- Health checks for monitoring

### **Scalability**
- Modular design allows independent scaling
- Stateless applications for easy horizontal scaling
- Efficient batch processing for data ingestion

## 🚀 **Getting Started Checklist**

### **Before Deployment:**
- [ ] Update registry URLs in Makefile and deploy.sh
- [ ] Create kubernetes/secrets.yaml from template
- [ ] Verify ChromaDB is accessible at specified endpoint
- [ ] Test Confluence/Jira API credentials

### **After Deployment:**
- [ ] Check pod status: `kubectl get pods -n bot-infra`
- [ ] Verify health: `make health`
- [ ] Monitor logs: `make logs-app`
- [ ] Test bot in Slack
- [ ] Trigger manual sync: `make run-sync-now`

## 🔧 **Customization Points**

### **To Modify Sync Behavior:**
- Edit `sync-job/sync_data.py` for sync logic
- Update `kubernetes/configmaps.yaml` for schedules/settings
- Modify `sync-job/confluence_client.py` for different data sources

### **To Change Bot Behavior:**
- Edit `slack-app/app.py` for message handling
- Update `rag-module/rag_client.py` for search logic
- Modify `slack-app/config.py` for new settings

### **To Add New Features:**
- Create new modules following existing patterns
- Update Dockerfiles to include new dependencies
- Add corresponding Kubernetes manifests

---

Each file has a single, clear responsibility, making the system maintainable and scalable for your team! 🚀
