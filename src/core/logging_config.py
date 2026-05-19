import sys
from loguru import logger
import os
from src.core.config import settings

def setup_logging():
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    
    # Remove default logger
    logger.remove()
    
    # Add stdout logger
    logger.add(sys.stdout, format="{time} {level} {message}", level="INFO")
    
    # Add structured JSON logger
    logger.add(
        os.path.join(settings.LOG_DIR, "app.log.json"),
        serialize=True,
        level="INFO",
        rotation="10 MB"
    )

setup_logging()
