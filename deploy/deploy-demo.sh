#!/usr/bin/env bash
# Runs on the GPU VM (fed over ssh by .github/workflows/deploy.yml): check out the given
# commit and rebuild the demo stack. Only services whose image changed are recreated.
#
# Usage: deploy-demo.sh <commit-sha>
set -euo pipefail

REF="${1:?commit sha required}"
APP_DIR="${APP_DIR:-/opt/ecosystem-ai-services}"
COMPOSE=(docker compose -f docker-compose.demo.yml --profile gpu-workers)

cd "$APP_DIR"
git fetch --quiet --tags origin
git checkout --quiet --detach "$REF"
echo "Checked out $(git log -1 --format='%h %s')"

# Run from deploy/ so the compose project stays "deploy" (containers deploy-*, volumes deploy_*).
cd deploy
"${COMPOSE[@]}" up -d --build
"${COMPOSE[@]}" ps

curl -fsS --retry 20 --retry-delay 3 --retry-all-errors http://localhost:8000/health
echo
