# Slack Bot with RAG Integration

A modular Slack bot that uses Retrieval-Augmented Generation (RAG) to answer questions based on your Confluence and Jira knowledge base.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Slack App     │───▶│   RAG Module    │───▶│   ChromaDB      │
│   (Always On)   │    │   (Library)     │    │   (Vector DB)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        ▲
                                                        │
                                               ┌─────────────────┐
                                               │   Sync Job      │
                                               │   (CronJob)     │
                                               └─────────────────┘
```

## Components

- **slack-app/**: Main Slack bot application (always running)
- **rag-module/**: Reusable RAG library for vector operations
- **sync-job/**: Nightly sync job for Confluence/Jira data
- **kubernetes/**: K8s manifests for deployment

## Quick Start

### 1. Prerequisites

- Docker and kubectl installed
- Access to an EKS cluster
- Slack app tokens
- Confluence/Jira API tokens
- ChromaDB running at `chromadb-service.bot-infra.svc.cluster.local:8000`

### 2. Setup

1. **Clone and configure:**
   ```bash
   git clone <your-repo>
   cd slack-bot-rag
   ```

2. **Create secrets:**
   ```bash
   cp kubernetes/secrets.yaml.template kubernetes/secrets.yaml
   # Edit and base64 encode your secrets
   ```

3. **Update registry:**
   ```bash
   export REGISTRY=your-docker-registry.com
   export TAG=v1.0.0
   ```

### 3. Deploy

```bash
# Deploy everything
make deploy-all REGISTRY=${REGISTRY} TAG=${TAG}

# Or use the deploy script
./deploy.sh --registry ${REGISTRY} --tag ${TAG}
```

### 4. Verify

```bash
# Check status
make status

# View logs
make logs-app

# Test health
make health

# Trigger manual sync
make run-sync-now
```

## Local Development

```bash
# Create .env file with your credentials
cp .env.example .env

# Start local stack
docker-compose up -d chromadb
docker-compose up slack-app

# Run sync manually
docker-compose run --rm sync-job
```

## Configuration

### Environment Variables

**Slack App:**
- `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`: Slack credentials
- `LLM_API_ENDPOINT`, `LLM_API_KEY`: LLM API credentials
- `RAG_ENABLED`: Enable/disable RAG (default: true)
- `CHROMADB_HOST`, `CHROMADB_PORT`: ChromaDB connection

**Sync Job:**
- `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN`: Confluence API
- `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`: Jira API  
- `SYNC_CONFLUENCE`, `SYNC_JIRA`: Enable/disable sync
- `CONFLUENCE_SPACES`: Comma-separated list of spaces (empty = all)
- `INCREMENTAL_SYNC`: Only sync recent changes (default: true)
- `SYNC_DAYS`: Days to look back for incremental sync (default: 7)

## Monitoring

- **Health Check**: `GET /health` - Overall system health
- **Readiness Check**: `GET /ready` - Application readiness
- **Logs**: Use `kubectl logs` to monitor application logs
- **Metrics**: CronJob success/failure rates in Kubernetes

## Troubleshooting

**Common Issues:**

1. **Bot not responding**: Check Slack app logs and health endpoint
2. **RAG not working**: Verify ChromaDB connection and sync job success
3. **Sync job failing**: Check Confluence/Jira credentials and API limits
4. **Out of memory**: Increase resource limits in deployment YAML

**Debug Commands:**

```bash
# Check all resources
kubectl get all -n bot-infra

# Describe problematic pods
kubectl describe pod <pod-name> -n bot-infra

# Check recent sync jobs
kubectl get jobs -n bot-infra --sort-by=.metadata.creationTimestamp

# Manual sync for testing
kubectl create job --from=cronjob/confluence-sync-job test-sync -n bot-infra
```

## Scaling

- **Slack App**: Keep at 1 replica (socket mode limitation)
- **Sync Job**: Runs as CronJob, adjust schedule as needed
- **ChromaDB**: Single instance (no clustering support)
- **Resources**: Adjust CPU/memory limits based on usage patterns

## Security

- All secrets stored in Kubernetes secrets
- RBAC configured with minimal permissions
- Network policies restrict ChromaDB access
- Non-root containers
- Resource limits prevent resource exhaustion
