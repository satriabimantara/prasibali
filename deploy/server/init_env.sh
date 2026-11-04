#!/usr/bin/env bash
# Create ~/prasibali/.env once (run as the deploy user on the server, after the first `git push prod master`):
#
#   bash ~/prasibali/deploy/server/init_env.sh
#
# Random secrets (Django secret key, Postgres password) are generated here and never printed. The three values only
# the developer knows stay empty: EMAIL_HOST_PASSWORD, DEMO_USER_EMAIL, DEMO_USER_PASSWORD -> fill them with
# `nano ~/prasibali/.env` (docs/deploy_hostinger.md, step D). An existing .env is never overwritten.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${APP_DIR}/.env"
DOMAIN="${DOMAIN:-prasibali.tech}"
MAILBOX="${MAILBOX:-noreply@${DOMAIN}}"

if [ -e "${ENV_FILE}" ]; then
    echo "${ENV_FILE} already exists; not overwritten. Edit it with: nano ${ENV_FILE}" >&2
    exit 1
fi

# Hex only: safe inside DATABASE_URL and in docker compose interpolation.
SECRET_KEY="$(openssl rand -hex 32)"
DB_PASSWORD="$(openssl rand -hex 20)"

umask 077
cat > "${ENV_FILE}" <<EOF
# PrasiBali production settings (created by deploy/server/init_env.sh). Never commit this file.

# --- Django -------------------------------------------------------------------------------------
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
DJANGO_LOG_LEVEL=INFO

# --- Caddy (HTTPS) ------------------------------------------------------------------------------
SITE_DOMAIN=${DOMAIN}
ACME_EMAIL=${MAILBOX}

# --- PostgreSQL (the password is used when the database volume is first created) --------------
POSTGRES_DB=prasibali
POSTGRES_USER=prasibali
POSTGRES_PASSWORD=${DB_PASSWORD}

# --- Email: Hostinger Email SMTP (smtp.hostinger.com:587 STARTTLS is the app default) ----------
# EMAIL_HOST_PASSWORD = password of the ${MAILBOX} mailbox (hPanel -> Emails -> Email accounts).
EMAIL_HOST_USER=${MAILBOX}
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL="PrasiBali <${MAILBOX}>"

# --- Judges' demo account (python manage.py create_demo_user) -----------------------------------
DEMO_USER_EMAIL=
DEMO_USER_PASSWORD=

# --- Hostinger KVM 1 (1 vCPU, 4 GB): measured in docs/deploy.md ---------------------------------
GUNICORN_WORKERS=2
WEB_MEM_LIMIT=3500m
ANALYSIS_CLASSIFIER_CACHE_SIZE=2
ANALYSIS_DAILY_QUOTA=10

# --- Backups (docker/backup.sh) -----------------------------------------------------------------
BACKUP_KEEP_DAYS=14
BACKUP_AT=02:00
EOF
chmod 600 "${ENV_FILE}"
echo "Created ${ENV_FILE} (mode 600). Now fill EMAIL_HOST_PASSWORD, DEMO_USER_EMAIL and DEMO_USER_PASSWORD:"
echo "  nano ${ENV_FILE}"
