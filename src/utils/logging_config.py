import logging
from config.settings import LOG_DIR

def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=[logging.FileHandler(LOG_DIR / "tenantease.log"), logging.StreamHandler()])
