from __future__ import annotations

import configparser
import logging
from zoneinfo import ZoneInfo
from providers import PROVIDERS

# File paths
CONFIG_FILE_PATH = "config/config.properties"
SCHEDULED_FILE_PATH = "data/schedules.json"
PLUG_STATES_FILE_PATH = "data/plug_states.json"

# Schedule retry configuration
RETRY_BASE_DELAY_SECONDS = 30
RETRY_MAX_DELAY_SECONDS = 1800  # 30 minutes cap
RETRY_WINDOW_HOURS = 10

# Global config instance
config = configparser.ConfigParser()

# Read and validate timezone configuration
timezone_name = 'Europe/Madrid'
try:
    config.read(CONFIG_FILE_PATH)
    timezone_name = config.get('settings', 'timezone', fallback='Europe/Madrid')
except Exception as e:
    logging.getLogger("uvicorn.error").warning(f"Failed to read timezone from config, using default: {e}")

# Validate timezone by creating ZoneInfo
try:
    TIMEZONE = ZoneInfo(timezone_name)
    logging.getLogger("uvicorn.error").info(f"Using configured timezone: {timezone_name}")
except Exception as e:
    logging.getLogger("uvicorn.error").error(f"Invalid timezone '{timezone_name}', falling back to UTC: {e}")
    TIMEZONE = ZoneInfo('UTC')


def get_provider():
    return PROVIDERS[config.get('settings', 'provider')]
