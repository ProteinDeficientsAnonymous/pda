import os
import random
import signal
import threading
import time

bind = "0.0.0.0:8000"
worker_class = "uvicorn.workers.UvicornWorker"
# Sized above observed production bursts (~1900 req/hour); max-age bounds RSS.
max_requests = 2000
max_requests_jitter = 200
# SSE notification stream (notifications/sse.py) needs time to close on recycle.
graceful_timeout = 35


def worker_max_age_seconds() -> int:
    return int(os.environ.get("PDA_WORKER_MAX_AGE", "1800"))


def worker_max_age_jitter_seconds() -> int:
    return int(os.environ.get("PDA_WORKER_MAX_AGE_JITTER", "300"))


def post_fork(server, _worker):
    max_age = worker_max_age_seconds()
    if max_age <= 0:
        return
    delay = max_age + random.randint(0, worker_max_age_jitter_seconds())

    def retire():
        time.sleep(delay)
        server.log.info("worker max age reached (%ss), recycling pid=%s", delay, os.getpid())
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=retire, daemon=True, name="pda-worker-max-age").start()
