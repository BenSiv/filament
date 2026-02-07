#!/bin/bash
# FILAMENT Development Environment Manager
# Usage: ./scripts/dev.sh [command]

set -e

# Determine project root and compose file location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/code/devenv/podman-compose.yml"

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
    podman-compose -f "$COMPOSE_FILE" logs -f
}

# Enter app container shell
shell() {
    info "Entering filament-app container..."
    podman exec -it filament-app /bin/bash
}

# Run command in container
run() {
    podman exec -it filament-app "$@"
}

# Pull Ollama models
pull_models() {
    info "Pulling Deepseek-R1 model..."
    podman exec filament-app ollama pull deepseek-r1:1.5b
    info "Model pulled successfully!"
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
    info "Rebuilding container..."
    podman-compose -f "$COMPOSE_FILE" build --no-cache
    info "Rebuild complete"
}

# Run the full pipeline (setup + analysis)
pipeline() {
    info "Starting full pipeline..."
    up
    
    info "Step 1: Building Database"
    run python code/scripts/build_sqlite_db.py
    
    info "Step 2: Running Core Analysis"
    run python -m core
    
    info "Pipeline complete!"
}

# Help message
help() {
    cat << EOF
FILAMENT Development Environment Manager

Usage: ./code/scripts/dev.sh [command]

Commands:
    up          Start the container environment
    down        Stop the container environment
    status      Show container status
    logs        View container logs
    shell       Enter app container shell
    run <cmd>   Run a command in the container (e.g., ./dev.sh run python -m core)
    pull_models Pull the default Deepseek model
    pipeline    Run the full workflow (Start -> Build DB -> Analyze)
    rebuild     Rebuild the container
    clean       Remove all containers and volumes
    help        Show this help message

Examples:
    ./code/scripts/dev.sh up
    ./code/scripts/dev.sh pipeline
EOF
}

# Main
check_deps

case "${1:-help}" in
    up)         up ;;
    down)       down ;;
    status)     status ;;
    logs)       logs ;;
    shell)      shell ;;
    run)        shift; run "$@" ;;
    pull_models) pull_models ;;
    pipeline)   pipeline ;;
    rebuild)    rebuild ;;
    clean)      clean ;;
    help|*)     help ;;
esac
