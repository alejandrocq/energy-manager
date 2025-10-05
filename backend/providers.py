import time
import requests
import logging
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from functools import wraps


def cached_prices(func):
    """Decorator to cache price results by date"""

    @wraps(func)
    def wrapper(self, target_date: datetime, *args, **kwargs):
        cache_key = f"{target_date.strftime('%Y%m%d')}"

        if not hasattr(self, '_prices_cache'):
            self._prices_cache = {}

        if cache_key in self._prices_cache:
            logging.info(f"Cache hit for {cache_key}")
            return self._prices_cache[cache_key]

        result = func(self, target_date, *args, **kwargs)

        self._prices_cache[cache_key] = result

        return result

    return wrapper


class PricesProvider(ABC):
    @abstractmethod
    def unavailable(self) -> bool:
        pass

    @abstractmethod
    def get_prices(self, target_date: datetime) -> list[tuple[int, float]]:
        pass


class OmieProvider(PricesProvider):
    BASE_URL = "https://www.omie.es/es/file-download?parents=marginalpdbc&filename=marginalpdbc_{date}.1"
    MAX_RETRIES = 3
    RETRY_TIME_SECONDS = 5

    def __init__(self):
        self.unavailable_until = None

    def unavailable(self):
        return self.unavailable_until and datetime.now() < self.unavailable_until

    @cached_prices
    def get_prices(self, target_date: datetime) -> list[tuple[int, float]]:
        if self.unavailable():
            return []
        else:
            self.unavailable_until = None

        target_date_string = target_date.strftime("%Y%m%d")
        hourly_prices = []
        retries = 0

        # Retry loop: keep trying every 15s until we fetch and parse successfully
        while True:
            try:
                response = requests.get(self.BASE_URL.format(date=target_date_string), timeout=10)
                response.raise_for_status()
                file_content = response.text

                for line in file_content.splitlines():
                    if line.startswith(target_date.strftime("%Y;%m;%d")):
                        parts = line.split(";")
                        hour = int(parts[3]) - 1
                        price = round(float(parts[5]) / 1000, 3)
                        hourly_prices.append((hour, price))

                if not hourly_prices:
                    raise ValueError("No hourly prices found")

                return hourly_prices
            except Exception as e:
                logging.error(f"Failed to fetch/parse prices: {e}. Retrying in {self.RETRY_TIME_SECONDS}s…")
                retries += 1
                if retries >= self.MAX_RETRIES:
                    break
                time.sleep(self.RETRY_TIME_SECONDS)

        self.unavailable_until = datetime.now() + timedelta(minutes=15)
        logging.error(f"Failed to fetch prices after {self.MAX_RETRIES} retries. Unavailable until {self.unavailable_until}.")
        return []


PROVIDERS = {
    "omie": OmieProvider(),
}
