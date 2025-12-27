from __future__ import annotations

import configparser
import logging
import sys

from zoneinfo import ZoneInfo
from providers import PROVIDERS

# File paths
CONFIG_FILE_PATH = "config/config.properties"
CHART_FILE_NAME = "prices_chart.png"
SCHEDULED_FILE_PATH = "data/schedules.json"
PLUG_STATES_FILE_PATH = "data/plug_states.json"

# Centralized logger configuration
# Create a named logger that works with uvicorn's logging setup
logger = logging.getLogger("energy_manager")
logger.setLevel(logging.INFO)

# Only add handler if not already configured (avoid duplicate handlers)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Prevent propagation to root logger to avoid duplicate logs with uvicorn
logger.propagate = False

# Global config instance
config = configparser.ConfigParser()

# Read and validate timezone configuration
timezone_name = 'Europe/Madrid'
try:
    config.read(CONFIG_FILE_PATH)
    timezone_name = config.get('settings', 'timezone', fallback='Europe/Madrid')
except Exception as e:
    logger.warning(f"Failed to read timezone from config, using default: {e}")

# Validate timezone by creating ZoneInfo
try:
    TIMEZONE = ZoneInfo(timezone_name)
    logger.info(f"Using configured timezone: {timezone_name}")
except Exception as e:
    logger.error(f"Invalid timezone '{timezone_name}', falling back to UTC: {e}")
    TIMEZONE = ZoneInfo('UTC')


def get_provider():
    return PROVIDERS[config.get('settings', 'provider')]
