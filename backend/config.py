from __future__ import annotations

import configparser
import logging

from providers import PROVIDERS

# File paths
CONFIG_FILE_PATH = "config/config.properties"
CHART_FILE_NAME = "prices_chart.png"
SCHEDULED_FILE_PATH = "data/schedules.json"
PLUG_STATES_FILE_PATH = "data/plug_states.json"

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global config instance
config = configparser.ConfigParser()


def get_provider():
    config.read(CONFIG_FILE_PATH)
    return PROVIDERS[config.get('settings', 'provider')]
