#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY=${REGISTRY:-"your-registry"}
TAG=${TAG:-"latest"}
NAMESPACE="bot-infra"

print_step() {
    echo -e "${BLUE}==== $1 ====${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

check_prerequisites() {
    print_step "Checking prerequisites"
    
    # Check if required tools are installed
    command -v docker >/dev/null 2>&1 || print_error "Docker is required but not installed"
    command -v kubectl >/dev/null 2>&1 || print_error "kubectl is required but not installed"
    command -v jq >/dev/null 2>&1 || print_warning "jq not found - some features will be limited"
    
    # Check if kubectl is configured
    kubectl cluster-info >/dev/null 2>&1 || print_error "kubectl is not configured or cluster is not accessible"
    
    # Check if secrets file exists
    if [ ! -f kubernetes/secrets.yaml ]; then
        print_error "kubernetes/secrets.yaml not found. Please create it from kubernetes/secrets.yaml.template"
    fi
    
    print_success "Prerequisites check passed"
}

build_images() {
    print_step "Building Docker images"
    
    echo "Building Slack app image..."
    docker build -t ${REGISTRY}/slack-app:${TAG} slack-app/
    
    echo "Building sync job image..."
    docker build -t ${REGISTRY}/sync-job:${TAG} sync-job/
    
    print_success "Docker images built successfully"
}

push_images() {
    print_step "Pushing Docker images"
    
    echo "Pushing ${REGISTRY}/slack-app:${TAG}..."
    docker push ${REGISTRY}/slack-app:${TAG}
    
    echo "Pushing ${REGISTRY}/sync-job:${TAG}..."
    docker push ${REGISTRY}/sync-job:${TAG}
    
    print_success "Docker images pushed successfully"
}

deploy_kubernetes() {
    print_step "Deploying to Kubernetes"
    
    # Create namespace
    echo "Creating namespace..."
    kubectl apply -f kubernetes/namespace.yaml
    
    # Deploy RBAC
    echo "Deploying RBAC resources..."
    kubectl apply -f kubernetes/rbac/
    
    # Deploy ConfigMaps
    echo "Deploying ConfigMaps..."
    kubectl apply -f kubernetes/configmaps.yaml
    
    # Deploy Secrets
    echo "Deploying secrets..."
    kubectl apply -f kubernetes/secrets.yaml
    
    # Update image references and deploy Slack app
    echo "Deploying Slack app..."
    sed "s|your-registry/slack-app:latest|${REGISTRY}/slack-app:${TAG}|g" kubernetes/slack-app/deployment.yaml > /tmp/slack-app-deployment.yaml
    kubectl apply -f kubernetes/slack-app/service.yaml
    kubectl apply -f kubernetes/slack-app/hpa.yaml
    kubectl apply -f /tmp/slack-app-deployment.yaml
    rm /tmp/slack-app-deployment.yaml
    
    # Update image references and deploy sync job
    echo "Deploying sync job..."
    sed "s|your-registry/sync-job:latest|${REGISTRY}/sync-job:${TAG}|g" kubernetes/sync-job/cronjob.yaml > /tmp/sync-job-cronjob.yaml
    kubectl apply -f /tmp/sync-job-cronjob.yaml
    rm /tmp/sync-job-cronjob.yaml
    
    print_success "Kubernetes deployment completed"
}

wait_for_deployment() {
    print_step "Waiting for deployment to be ready"
    
    echo "Waiting for Slack app deployment..."
    kubectl wait --for=condition=available --timeout=300s deployment/slack-app -n ${NAMESPACE}
    
    print_success "Deployment is ready"
}

verify_deployment() {
    print_step "Verifying deployment"
    
    echo "Checking pod status..."
    kubectl get pods -n ${NAMESPACE}
    
    echo -e "\nChecking services..."
    kubectl get services -n ${NAMESPACE}
    
    echo -e "\nChecking cronjobs..."
    kubectl get cronjobs -n ${NAMESPACE}
    
    # Test health endpoint
    echo -e "\nTesting health endpoint..."
    kubectl port-forward service/slack-app-service 8080:8080 -n ${NAMESPACE} >/dev/null 2>&1 &
    PORT_FORWARD_PID=$!
    sleep 5
    
    if curl -f -s http://localhost:8080/health >/dev/null 2>&1; then
        print_success "Health check passed"
    else
        print_warning "Health check failed - this might be normal if the app is still starting"
    fi
    
    # Clean up port forward
    kill $PORT_FORWARD_PID 2>/dev/null || true
}

show_next_steps() {
    print_step "Next Steps"
    
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📋 What happens next:"
    echo "1. Your Slack bot should be running and responsive"
    echo "2. The sync job will run nightly at 2 AM UTC"
    echo "3. You can manually trigger a sync with: kubectl create job --from=cronjob/confluence-sync-job manual-sync-\$(date +%Y%m%d-%H%M%S) -n ${NAMESPACE}"
    echo ""
    echo "🔧 Useful commands:"
    echo "  View app logs:     kubectl logs -f deployment/slack-app -n ${NAMESPACE}"
    echo "  View sync logs:    kubectl logs -f job/\$(kubectl get jobs -n ${NAMESPACE} --sort-by=.metadata.creationTimestamp -o name | tail -1 | cut -d/ -f2) -n ${NAMESPACE}"
    echo "  Check status:      kubectl get all -n ${NAMESPACE}"
    echo "  Port forward:      kubectl port-forward service/slack-app-service 8080:8080 -n ${NAMESPACE}"
    echo "  Scale app:         kubectl scale deployment slack-app --replicas=1 -n ${NAMESPACE}"
    echo ""
    echo "🔍 Monitoring:"
    echo "  Health endpoint:   http://localhost:8080/health (when port-forwarded)"
    echo "  Readiness:         http://localhost:8080/ready (when port-forwarded)"
    echo ""
}

main() {
    echo -e "${GREEN}"
    echo "🚀 Slack Bot RAG Deployment Script"
    echo "=================================="
    echo -e "${NC}"
    
    # Parse command line arguments
    SKIP_BUILD=false
    SKIP_PUSH=false
    SKIP_DEPLOY=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-push)
                SKIP_PUSH=true
                shift
                ;;
            --skip-deploy)
                SKIP_DEPLOY=true
                shift
                ;;
            --registry)
                REGISTRY="$2"
                shift 2
                ;;
            --tag)
                TAG="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --skip-build     Skip Docker image building"
                echo "  --skip-push      Skip Docker image pushing"  
                echo "  --skip-deploy    Skip Kubernetes deployment"
                echo "  --registry       Docker registry (default: your-registry)"
                echo "  --tag            Image tag (default: latest)"
                echo "  -h, --help       Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                ;;
        esac
    done
    
    echo "Configuration:"
    echo "  Registry: ${REGISTRY}"
    echo "  Tag: ${TAG}"
    echo "  Namespace: ${NAMESPACE}"
    echo ""
    
    # Run deployment steps
    check_prerequisites
    
    if [ "$SKIP_BUILD" = false ]; then
        build_images
    else
        print_warning "Skipping image build"
    fi
    
    if [ "$SKIP_PUSH" = false ]; then
        push_images
    else
        print_warning "Skipping image push"
    fi
    
    if [ "$SKIP_DEPLOY" = false ]; then
        deploy_kubernetes
        wait_for_deployment
        verify_deployment
        show_next_steps
    else
        print_warning "Skipping Kubernetes deployment"
    fi
}

# Run main function
main "$@"
