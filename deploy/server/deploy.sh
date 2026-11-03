#!/usr/bin/env bash
# Build and start PrasiBali.ai from the checked-out commit (started by the post-receive hook after `git push prod
# master`; can also be run by hand: `bash ~/prasibali/deploy/server/deploy.sh`).
#
# The new image is built first; the running containers are replaced only when the build succeeds, so a failed
# build leaves the previous version online. Output goes to ~/prasibali/deploy.log (when started by the hook).
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_DIR="${REPO_DIR:-$(dirname "${APP_DIR}")/prasibali.git}"
REVISION="${1:-$(git --git-dir="${REPO_DIR}" rev-parse master 2>/dev/null || echo unknown)}"
COMPOSE=(docker compose -f docker-compose.prod.yml)
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-600}"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$*"; }
fail() { log "DEPLOY FAILED: $*"; exit 1; }

cd "${APP_DIR}"
exec 9> "${APP_DIR}/.deploy.lock"
if ! flock -n 9; then
    log "Another deploy is running; waiting for it to finish."
    flock 9
fi

log "=== Deploy ${REVISION:0:7} started"

# Prerequisites that are not in git.
[ -f .env ] || fail ".env is missing. Run: bash ${APP_DIR}/deploy/server/init_env.sh"
[ -f models/SHA256SUMS ] || fail "models/ is empty. Upload dist/prasibali-models-v1.0.tar.gz (docs/deploy_hostinger.md)."
(cd models && sha256sum --quiet --check SHA256SUMS) || fail "model files are missing or damaged (sha256sum)."
for name in EMAIL_HOST_PASSWORD DEMO_USER_EMAIL DEMO_USER_PASSWORD; do
    grep -Eq "^${name}=.+" .env || log "WARNING: ${name} is empty in .env (see docs/deploy_hostinger.md, step D)."
done

if [ "${DEPLOY_DRY_RUN:-0}" = "1" ]; then
    log "DEPLOY_DRY_RUN=1: prerequisites OK, skipping docker compose."
    exit 0
fi

log "Building the web image (first build: 20-40 minutes on 1 vCPU)"
"${COMPOSE[@]}" build web || fail "image build failed; the previous version keeps running."

log "Starting containers"
"${COMPOSE[@]}" up -d --remove-orphans || fail "docker compose up failed."

log "Waiting for the web container to become healthy (model warm-up takes about 2 minutes)"
container="$("${COMPOSE[@]}" ps -q web)"
waited=0
while :; do
    status="$(docker inspect -f '{{.State.Health.Status}}' "${container}" 2>/dev/null || echo missing)"
    [ "${status}" = "healthy" ] && break
    if [ "${status}" = "unhealthy" ] || [ "${waited}" -ge "${HEALTH_TIMEOUT}" ]; then
        "${COMPOSE[@]}" logs --tail 60 web || true
        fail "web is ${status} after ${waited}s (logs above)."
    fi
    sleep 10
    waited=$((waited + 10))
done

docker image prune -f >/dev/null
echo "${REVISION}" > REVISION
log "=== Deploy ${REVISION:0:7} finished: web is healthy (${waited}s)."
"${COMPOSE[@]}" ps
