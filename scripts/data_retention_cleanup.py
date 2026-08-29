"""
Data Retention Cleanup Task

This script can be executed via cron or a scheduler to enforce data retention policies globally.
"""
import os
import sys
import logging

# Ensure the parent directory is in the PYTHONPATH so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.data_retention_engine import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting Data Retention Cleanup Task...")
    engine.run_cleanup()
    logger.info("Data Retention Cleanup Task Completed.")
