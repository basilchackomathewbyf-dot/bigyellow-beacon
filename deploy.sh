#!/bin/bash
# ==============================================================================
# BigYellow Beacon – Reusable One-Command Deployment Script (GCP Single VM)
# ==============================================================================
# Usage:
#   ./deploy.sh                # Full pull, build, restart & health check
#   ./deploy.sh --no-pull      # Skip git pull (build & restart current local code)
#   ./deploy.sh --quick        # Skip builds (just restart services & check health)
#   ./deploy.sh --frontends    # Only rebuild and restart frontend apps
#   ./deploy.sh --backends     # Only update dependencies and restart backend APIs
# ==============================================================================

set -e

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DO_PULL=true
DO_BACKENDS=true
DO_FRONTENDS=true

# Parse flags
for arg in "$@"; do
    case "$arg" in
        --no-pull)
            DO_PULL=false
            ;;
        --quick|--restart-only)
            DO_PULL=false
            DO_BACKENDS=false
            DO_FRONTENDS=false
            ;;
        --frontends|--frontend-only)
            DO_BACKENDS=false
            ;;
        --backends|--backend-only)
            DO_FRONTENDS=false
            ;;
        --help|-h)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo "  --no-pull     Skip git pull"
            echo "  --quick       Skip builds, only restart services"
            echo "  --frontends   Only build frontends and restart"
            echo "  --backends    Only update backends and restart"
            exit 0
            ;;
    esac
done

echo -e "${BLUE}=================================================================${NC}"
echo -e "${CYAN}⚓ BigYellow Beacon – Automated Deployment${NC}"
echo -e "${BLUE}=================================================================${NC}"

# 1. GIT PULL
if [ "$DO_PULL" = true ]; then
    echo -e "\n${YELLOW}📥 [1/4] Pulling latest changes from Git...${NC}"
    CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")"
    if git pull origin "$CURRENT_BRANCH"; then
        echo -e "${GREEN}✓ Git branch '$CURRENT_BRANCH' up to date.${NC}"
    else
        echo -e "${RED}⚠️  Warning: Git pull failed or has merge conflicts. Continuing with local files...${NC}"
    fi
else
    echo -e "\n${YELLOW}⏩ [1/4] Skipping Git pull (--no-pull specified)${NC}"
fi

# 2. BACKEND BUILD / DEPENDENCIES
if [ "$DO_BACKENDS" = true ]; then
    echo -e "\n${YELLOW}🐍 [2/4] Updating Python Backends...${NC}"

    # Shore Server
    if [ -d "$ROOT_DIR/server/shore" ]; then
        echo -e "  ⚙️  Configuring Shore Server..."
        cd "$ROOT_DIR/server/shore"
        if [ ! -d ".venv" ]; then
            python3 -m venv .venv
        fi
        source .venv/bin/activate
        pip install -r requirements.txt --quiet --upgrade
        deactivate
        echo -e "${GREEN}  ✓ Shore Server dependencies updated.${NC}"
    fi

    # Edge Server
    if [ -d "$ROOT_DIR/server/edge" ]; then
        echo -e "  ⚙️  Configuring Edge Server..."
        cd "$ROOT_DIR/server/edge"
        if [ ! -d ".venv" ]; then
            python3 -m venv .venv
        fi
        source .venv/bin/activate
        pip install -r requirements.txt --quiet --upgrade
        deactivate
        echo -e "${GREEN}  ✓ Edge Server dependencies updated.${NC}"
    fi
else
    echo -e "\n${YELLOW}⏩ [2/4] Skipping Backend dependency updates${NC}"
fi

# 3. FRONTEND PRODUCTION BUILDS
if [ "$DO_FRONTENDS" = true ]; then
    echo -e "\n${YELLOW}⚛️  [3/4] Building Frontend Production Bundles (Vite)...${NC}"

    # Crew App Build
    if [ -d "$ROOT_DIR/client/crew-app" ]; then
        echo -e "  📦 Building Crew App (Nitro Node Server)..."
        cd "$ROOT_DIR/client/crew-app"
        pnpm install --quiet
        NITRO_PRESET=node-server pnpm build
        echo -e "${GREEN}  ✓ Crew App built successfully.${NC}"
    fi

    # Shore Dashboard Build
    if [ -d "$ROOT_DIR/client/dashboard" ]; then
        echo -e "  📦 Building Shore Dashboard (Nitro Node Server)..."
        cd "$ROOT_DIR/client/dashboard"
        pnpm install --quiet
        NITRO_PRESET=node-server pnpm build
        echo -e "${GREEN}  ✓ Shore Dashboard built successfully.${NC}"
    fi
else
    echo -e "\n${YELLOW}⏩ [3/4] Skipping Frontend builds${NC}"
fi

# 4. RESTART SERVICES & NGINX
echo -e "\n${YELLOW}🔄 [4/4] Restarting Systemd Services and Nginx...${NC}"
cd "$ROOT_DIR"

if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl daemon-reload
    sudo systemctl restart beacon-shore beacon-edge beacon-crew beacon-dashboard
    sudo nginx -t && sudo systemctl reload nginx
    echo -e "${GREEN}✓ All services restarted.${NC}"
else
    echo -e "${RED}⚠️ systemctl not found; skipping service restart.${NC}"
fi

# 5. AUTOMATED HEALTH CHECKS
echo -e "\n${BLUE}=================================================================${NC}"
echo -e "${CYAN}🩺 Running Post-Deployment Health Checks...${NC}"
echo -e "${BLUE}=================================================================${NC}"

sleep 2

check_health() {
    local name="$1"
    local url="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "FAIL")
    if [ "$status" = "200" ] || [ "$status" = "301" ] || [ "$status" = "302" ] || [ "$status" = "307" ]; then
        echo -e "  ${GREEN}● ${name}${NC} ($url) ➔ ${GREEN}ONLINE (HTTP $status)${NC}"
    else
        echo -e "  ${RED}● ${name}${NC} ($url) ➔ ${RED}FAILED (HTTP $status)${NC}"
    fi
}

check_health "Edge Server API  " "http://127.0.0.1:8000/healthz"
check_health "Shore Server API " "http://127.0.0.1:8001/healthz"
check_health "Crew App Frontend" "http://127.0.0.1:3000/login"
check_health "Dashboard Frontend" "http://127.0.0.1:3001/dashboard/login"

EXT_IP="$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_VM_IP")"

echo -e "\n${GREEN}=================================================================${NC}"
echo -e "${GREEN}🚀 BigYellow Beacon Successfully Deployed & Live!${NC}"
echo -e "${GREEN}=================================================================${NC}"
echo -e "  📱 ${CYAN}Crew App (Seafarer PWA):${NC}  http://${EXT_IP}/login"
echo -e "  🏢 ${CYAN}Shore Fleet Dashboard:${NC}    http://${EXT_IP}/dashboard"
echo -e "  📄 ${CYAN}Edge Swagger API Docs:${NC}    http://${EXT_IP}/api/edge/docs"
echo -e "  📄 ${CYAN}Shore Swagger API Docs:${NC}   http://${EXT_IP}/api/shore/docs"
echo -e "${GREEN}=================================================================${NC}"
