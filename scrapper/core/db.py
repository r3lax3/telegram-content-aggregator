from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

import time
import os

from core.domain.entities import Base
from core.logger import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.environ["SCRAPPER_DATABASE_URL"]

RETRY_SECONDS = 3
MAX_RETRIES = 20

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

for i in range(MAX_RETRIES):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database is available")
        break
    except Exception as e:
        logger.warning(f"DB not ready ({e}), retrying in {RETRY_SECONDS}s")
        time.sleep(RETRY_SECONDS)
else:
    raise RuntimeError("Database never became available")

Base.metadata.create_all(bind=engine)
logger.info("Database tables created")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)
