#!/bin/sh
# Container entrypoint. For Gunicorn (the production CMD): migrate, create the cache table, warm the AI models
# (downloading the FastText embedding once if it is neither in PRETRAINED_MODELS_DIR nor in the HF_HOME cache), then
# switch Hugging Face to offline mode and start the server. Any other command (manage.py, sh, runserver) runs as is.
set -eu

log() {
    # One JSON line, like the application logs.
    printf '{"time":"%s","level":"%s","logger":"entrypoint","message":"%s"}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2"
}

if [ "${1:-}" = "gunicorn" ]; then
    log INFO "Applying database migrations"
    python manage.py migrate --noinput
    python manage.py createcachetable

    if [ "${SKIP_WARM_MODELS:-false}" = "true" ]; then
        log WARNING "SKIP_WARM_MODELS=true: models load in the Gunicorn master only"
    elif python manage.py warm_models; then
        # The embedding is now local or in the cache: never reach Hugging Face from the workers.
        export HF_HUB_OFFLINE=1
        log INFO "Models warmed; HF_HUB_OFFLINE=1"
    else
        # The app still starts; the analysis view reports the unavailable stage (CLAUDE.md).
        log ERROR "Model warm-up failed; starting without HF_HUB_OFFLINE so a later load can still download"
    fi
fi

exec "$@"
