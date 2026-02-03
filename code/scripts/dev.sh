#!/bin/bash
# FILAMENT Development Environment Manager
# Usage: ./scripts/dev.sh [command]

set -e

COMPOSE_FILE="podman-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check if podman-compose is available
check_deps() {
    command -v podman >/dev/null 2>&1 || error "podman is not installed"
    command -v podman-compose >/dev/null 2>&1 || error "podman-compose is not installed"
}

# Start all services
up() {
    info "Starting FILAMENT development environment..."
    podman-compose -f "$COMPOSE_FILE" up -d
    info "Waiting for services to be healthy..."
    sleep 5
    status
}

# Stop all services
down() {
    info "Stopping FILAMENT development environment..."
    podman-compose -f "$COMPOSE_FILE" down
}

# Show service status
status() {
    info "Service Status:"
    podman-compose -f "$COMPOSE_FILE" ps
}

# View logs
logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        podman-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        podman-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# Enter app container shell
shell() {
    info "Entering filament-app container..."
    podman exec -it filament-app /bin/bash
}

# Run Python command in container
run() {
    podman exec -it filament-app python "$@"
}

# Pull Ollama models
pull_models() {
    info "Pulling LLM models..."
    podman exec filament-ollama ollama pull llama3
    podman exec filament-ollama ollama pull mistral
    info "Models pulled successfully!"
}

# Test database connection
test_db() {
    info "Testing PostgreSQL connection..."
    podman exec filament-postgres psql -U filament -d filament -c "SELECT 'PostgreSQL OK' AS status;"
    
    info "Testing pgvector extension..."
    podman exec filament-postgres psql -U filament -d filament -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
    
    info "Testing Neo4j connection..."
    curl -s http://localhost:7474 >/dev/null && echo "Neo4j OK" || warn "Neo4j not responding"
}

# Clean up everything
clean() {
    warn "This will remove all containers and volumes!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        podman-compose -f "$COMPOSE_FILE" down -v
        info "Cleanup complete"
    fi
}

# Rebuild containers
rebuild() {
    info "Rebuilding containers..."
    podman-compose -f "$COMPOSE_FILE" build --no-cache
    info "Rebuild complete"
}

# Help message
help() {
    cat << EOF
FILAMENT Development Environment Manager

Usage: ./scripts/dev.sh [command]

Commands:
    up          Start all services
    down        Stop all services
    status      Show service status
    logs [svc]  View logs (optionally for specific service)
    shell       Enter app container shell
    run <cmd>   Run Python command in container
    pull_models Pull Ollama LLM models
    test_db     Test database connections
    rebuild     Rebuild containers
    clean       Remove all containers and volumes
    help        Show this help message

Examples:
    ./scripts/dev.sh up
    ./scripts/dev.sh logs postgres
    ./scripts/dev.sh run -m code.scrapers.bccs
EOF
}

# Main
check_deps

case "${1:-help}" in
    up)         up ;;
    down)       down ;;
    status)     status ;;
    logs)       logs "$2" ;;
    shell)      shell ;;
    run)        shift; run "$@" ;;
    pull_models) pull_models ;;
    test_db)    test_db ;;
    rebuild)    rebuild ;;
    clean)      clean ;;
    help|*)     help ;;
esac
