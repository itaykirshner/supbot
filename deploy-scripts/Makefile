.PHONY: build push deploy clean test help

# Configuration
REGISTRY ?= your-registry
TAG ?= latest
SLACK_APP_IMAGE = $(REGISTRY)/slack-app:$(TAG)
SYNC_JOB_IMAGE = $(REGISTRY)/sync-job:$(TAG)
NAMESPACE = bot-infra

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	@echo "Building Docker images..."
	docker build -t $(SLACK_APP_IMAGE) slack-app/
	docker build -t $(SYNC_JOB_IMAGE) sync-job/

push: build ## Build and push Docker images
	@echo "Pushing Docker images..."
	docker push $(SLACK_APP_IMAGE)
	docker push $(SYNC_JOB_IMAGE)

deploy-namespace: ## Create namespace
	kubectl apply -f kubernetes/namespace.yaml

deploy-rbac: ## Deploy RBAC resources
	kubectl apply -f kubernetes/rbac/

deploy-config: ## Deploy ConfigMaps
	kubectl apply -f kubernetes/configmaps.yaml

deploy-secrets: ## Deploy secrets (make sure secrets.yaml exists)
	@if [ ! -f kubernetes/secrets.yaml ]; then \
		echo "❌ kubernetes/secrets.yaml not found!"; \
		echo "Please create it from kubernetes/secrets.yaml.template"; \
		exit 1; \
	fi
	kubectl apply -f kubernetes/secrets.yaml

deploy-app: ## Deploy Slack app
	@echo "Updating image references..."
	sed -i.bak 's|your-registry/slack-app:latest|$(SLACK_APP_IMAGE)|g' kubernetes/slack-app/deployment.yaml
	kubectl apply -f kubernetes/slack-app/
	@echo "Restoring original files..."
	mv kubernetes/slack-app/deployment.yaml.bak kubernetes/slack-app/deployment.yaml

deploy-sync: ## Deploy sync job
	@echo "Updating image references..."
	sed -i.bak 's|your-registry/sync-job:latest|$(SYNC_JOB_IMAGE)|g' kubernetes/sync-job/cronjob.yaml
	kubectl apply -f kubernetes/sync-job/
	@echo "Restoring original files..."
	mv kubernetes/sync-job/cronjob.yaml.bak kubernetes/sync-job/cronjob.yaml

deploy-all: deploy-namespace deploy-rbac deploy-config deploy-secrets deploy-app deploy-sync ## Deploy everything

test-local: ## Test locally with docker-compose
	docker-compose up --build

clean: ## Clean up resources
	kubectl delete namespace $(NAMESPACE) --ignore-not-found=true

logs-app: ## View Slack app logs
	kubectl logs -f deployment/slack-app -n $(NAMESPACE)

logs-sync: ## View latest sync job logs
	kubectl logs -f job/$$(kubectl get jobs -n $(NAMESPACE) --sort-by=.metadata.creationTimestamp -o name | tail -1 | cut -d/ -f2) -n $(NAMESPACE)

status: ## Check deployment status
	@echo "=== Namespace ==="
	kubectl get namespace $(NAMESPACE) 2>/dev/null || echo "Namespace not found"
	@echo "\n=== Deployments ==="
	kubectl get deployments -n $(NAMESPACE) 2>/dev/null || echo "No deployments found"
	@echo "\n=== Services ==="
	kubectl get services -n $(NAMESPACE) 2>/dev/null || echo "No services found"
	@echo "\n=== CronJobs ==="
	kubectl get cronjobs -n $(NAMESPACE) 2>/dev/null || echo "No cronjobs found"
	@echo "\n=== Recent Jobs ==="
	kubectl get jobs -n $(NAMESPACE) --sort-by=.metadata.creationTimestamp 2>/dev/null || echo "No jobs found"

health: ## Check application health
	@echo "Checking Slack app health..."
	kubectl port-forward service/slack-app-service 8080:8080 -n $(NAMESPACE) &
	sleep 3
	curl -s http://localhost:8080/health | jq . || echo "Health check failed"
	pkill -f "kubectl port-forward" || true

run-sync-now: ## Manually trigger sync job
	kubectl create job --from=cronjob/confluence-sync-job manual-sync-$$(date +%Y%m%d-%H%M%S) -n $(NAMESPACE)

