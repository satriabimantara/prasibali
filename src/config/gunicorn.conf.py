"""Gunicorn settings for production (docker/Dockerfile CMD). See docs/deploy.md for how the worker count was measured.

- sync workers: balinese-nlp feature extractors keep state on the instance and are not thread-safe.
- preload_app: config.wsgi loads the default models once in the master (ANALYSIS_WARM_ON_START=true); the forked
  workers share those pages copy-on-write.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # src/, for config.jsonlog

from config.jsonlog import logging_config

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")  # only Caddy reaches it (internal compose network)
worker_class = "sync"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
preload_app = True
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))  # a long satua with a TF5 model stays well below this
graceful_timeout = 30
keepalive = 5
# Recycle workers now and then; with preload the new worker forks from the warm master.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "500"))
max_requests_jitter = 50
forwarded_allow_ips = "*"  # Caddy on the compose network sets X-Forwarded-*
worker_tmp_dir = "/dev/shm"  # noqa: S108 - heartbeat files in memory, standard Gunicorn-in-Docker practice

accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms'
logconfig_dict = logging_config(os.environ.get("DJANGO_LOG_LEVEL", "INFO"))
