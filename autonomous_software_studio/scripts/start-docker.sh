#!/bin/bash
# =============================================================================
# Autonomous Software Studio - Docker Startup Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE} Autonomous Software Studio - Docker Setup${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if docker compose is available
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif docker-compose --version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}Error: Docker Compose is not available.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from template...${NC}"
    cp .env.template .env
    echo -e "${YELLOW}Please edit .env file with your API keys before continuing.${NC}"
    echo ""
fi

# Parse command line arguments
COMMAND=${1:-"up"}
PROFILE=""

case "$COMMAND" in
    "up"|"start")
        echo -e "${GREEN}Starting Autonomous Software Studio...${NC}"
        echo ""

        # Create necessary directories
        mkdir -p data logs reports projects docs

        # Start services
        $COMPOSE_CMD up -d

        echo ""
        echo -e "${GREEN}Services started successfully!${NC}"
        echo ""
        echo -e "Access the dashboard at: ${BLUE}http://localhost:8501${NC}"
        echo -e "Orchestrator API at: ${BLUE}http://localhost:8000${NC}"
        echo ""
        echo -e "To view logs: ${YELLOW}$COMPOSE_CMD logs -f${NC}"
        ;;

    "up-monitoring"|"start-monitoring")
        echo -e "${GREEN}Starting with monitoring stack (Prometheus + Grafana)...${NC}"
        echo ""

        mkdir -p data logs reports projects docs

        $COMPOSE_CMD --profile monitoring up -d

        echo ""
        echo -e "${GREEN}Services started with monitoring!${NC}"
        echo ""
        echo -e "Dashboard: ${BLUE}http://localhost:8501${NC}"
        echo -e "Orchestrator API: ${BLUE}http://localhost:8000${NC}"
        echo -e "Prometheus: ${BLUE}http://localhost:9090${NC}"
        echo -e "Grafana: ${BLUE}http://localhost:3000${NC} (admin/admin)"
        ;;

    "down"|"stop")
        echo -e "${YELLOW}Stopping all services...${NC}"
        $COMPOSE_CMD --profile monitoring down
        echo -e "${GREEN}All services stopped.${NC}"
        ;;

    "restart")
        echo -e "${YELLOW}Restarting services...${NC}"
        $COMPOSE_CMD restart
        echo -e "${GREEN}Services restarted.${NC}"
        ;;

    "logs")
        SERVICE=${2:-""}
        if [ -n "$SERVICE" ]; then
            $COMPOSE_CMD logs -f "$SERVICE"
        else
            $COMPOSE_CMD logs -f
        fi
        ;;

    "build")
        echo -e "${BLUE}Building Docker images...${NC}"
        $COMPOSE_CMD build --no-cache
        echo -e "${GREEN}Build complete.${NC}"
        ;;

    "ps"|"status")
        $COMPOSE_CMD ps
        ;;

    "clean")
        echo -e "${RED}WARNING: This will remove all containers, volumes, and images.${NC}"
        read -p "Are you sure? (y/N) " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            $COMPOSE_CMD --profile monitoring down -v --rmi all
            echo -e "${GREEN}Cleanup complete.${NC}"
        else
            echo "Cancelled."
        fi
        ;;

    "db-shell")
        echo -e "${BLUE}Connecting to PostgreSQL...${NC}"
        $COMPOSE_CMD exec postgres psql -U softwarestudio -d softwarestudio
        ;;

    "help"|*)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  up, start           Start all services (default)"
        echo "  up-monitoring       Start with Prometheus + Grafana"
        echo "  down, stop          Stop all services"
        echo "  restart             Restart services"
        echo "  logs [service]      View logs (optionally for specific service)"
        echo "  build               Rebuild Docker images"
        echo "  ps, status          Show running containers"
        echo "  clean               Remove all containers, volumes, and images"
        echo "  db-shell            Connect to PostgreSQL shell"
        echo "  help                Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 up               # Start the application"
        echo "  $0 logs dashboard   # View dashboard logs"
        echo "  $0 down             # Stop everything"
        ;;
esac
