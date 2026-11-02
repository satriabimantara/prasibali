# PrasiBali.ai web image (Python 3.11). Single stage for now; session 7 makes it multi-stage.
FROM python:3.11-slim

ARG INSTALL_DEV=false
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# libgomp1: OpenMP runtime used by scikit-learn and torch CPU wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
# torch first from the CPU index so no CUDA wheels are pulled in; the AI/NLP pins stay untouched.
RUN pip install --index-url "${TORCH_INDEX}" torch==2.3.0 \
    && pip install --extra-index-url "${TORCH_INDEX}" -r requirements.txt \
    && if [ "${INSTALL_DEV}" = "true" ]; then pip install --extra-index-url "${TORCH_INDEX}" -r requirements-dev.txt; fi

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/.cache/huggingface /app/var /app/models \
    && chown -R app:app /app

COPY --chown=app:app pyproject.toml ./
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app tests ./tests
COPY --chown=app:app src ./src

USER app
WORKDIR /app/src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
