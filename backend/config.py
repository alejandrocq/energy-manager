from __future__ import annotations

import configparser
import logging
import sys

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


def get_provider():
    config.read(CONFIG_FILE_PATH)
    return PROVIDERS[config.get('settings', 'provider')]
