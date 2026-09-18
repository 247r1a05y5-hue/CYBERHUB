"""RQ Worker runner script."""
from __future__ import annotations

import logging
import sys

import redis
from rq import Queue, Worker

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("worker")

settings = get_settings()
listen = ["analyses", "reports", "default"]


def main() -> None:
    logger.info("Initializing Cyber Platform RQ Worker...")
    conn = redis.from_url(settings.REDIS_URL)
    worker = Worker(listen, connection=conn)
    logger.info(f"Worker listening on queues: {listen}")
    worker.work(with_scheduler=True)



if __name__ == "__main__":
    main()
