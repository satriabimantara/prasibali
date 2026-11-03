# syntax=docker/dockerfile:1
# PrasiBali.ai web image (Python 3.11), multi-stage:
#   css      builds src/static/css/app.css with the Tailwind standalone CLI (no Node.js)
#   deps     installs the Python packages into /opt/venv (torch from the CPU index, no CUDA)
#   runtime  slim image: venv + source + built CSS, collectstatic, non-root user, entrypoint
# Local development (docker-compose.yml) builds the same runtime stage with INSTALL_DEV=true.

ARG PYTHON_IMAGE=python:3.11-slim

# --------------------------------------------------------------------------- css
FROM ${PYTHON_IMAGE} AS css
WORKDIR /build
COPY scripts/tailwind.py scripts/tailwind.py
COPY src/static/src src/static/src
COPY src/templates src/templates
# Downloads the pinned Tailwind binary (scripts/tailwind.py: TAILWIND_VERSION) and writes a minified app.css.
# .tools is a BuildKit cache, so later builds reuse the downloaded binary.
RUN --mount=type=cache,target=/build/.tools python scripts/tailwind.py build && test -s src/static/css/app.css

# --------------------------------------------------------------------------- deps
FROM ${PYTHON_IMAGE} AS deps
ARG INSTALL_DEV=false
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
# Slow or unstable links: long timeouts, retries, and a BuildKit pip cache so downloaded wheels survive a failed
# build (the cache lives outside the image, so the venv stays lean).
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_RETRIES=10
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
# torch first, in its own layer, from the CPU index so no CUDA wheels are pulled in.
RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${TORCH_INDEX}" torch==2.3.0
COPY requirements.txt requirements-dev.txt ./
# The AI/NLP pins in requirements.txt stay untouched.
RUN --mount=type=cache,target=/root/.cache/pip pip install --extra-index-url "${TORCH_INDEX}" -r requirements.txt \
    && if [ "${INSTALL_DEV}" = "true" ]; then pip install --extra-index-url "${TORCH_INDEX}" -r requirements-dev.txt; fi

# --------------------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    HF_HOME=/app/.cache/huggingface \
    BALINESE_NLP_WORK_DIR=/app/var \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# libgomp1: OpenMP runtime used by scikit-learn and torch CPU wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /app/.cache/huggingface /app/var /app/models /app/staticfiles \
    && chown -R app:app /app

COPY --from=deps /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app tests ./tests
COPY --chown=app:app src ./src
COPY --from=css --chown=app:app /build/src/static/css/app.css ./src/static/css/app.css
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh
# Guard against CRLF line endings from a Windows checkout.
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh

USER app
WORKDIR /app/src

# Static files are collected at build time. The values below exist only for this command (prod settings require
# them); they are not secrets and do not end up in the image environment.
RUN DJANGO_SECRET_KEY=collectstatic-only DJANGO_ALLOWED_HOSTS=localhost CSRF_TRUSTED_ORIGINS=https://localhost \
    DATABASE_URL=sqlite:////tmp/collectstatic.sqlite3 \
    python manage.py collectstatic --noinput --verbosity 0 --ignore src  # static/src = Tailwind sources, not served

EXPOSE 8000

# Long start period: migrations and the model warm-up (SatuaNER, classifier, FastText) run before Gunicorn.
HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["gunicorn", "--config", "config/gunicorn.conf.py", "config.wsgi:application"]
