import time
import requests
import logging
from datetime import datetime, timedelta, timezone
from abc import ABC, abstractmethod
from functools import wraps

logger = logging.getLogger("uvicorn.error")


def cached_prices(func):
    """Decorator to cache price results by date"""

    @wraps(func)
    def wrapper(self, target_date: datetime, *args, **kwargs):
        cache_key = f"{target_date.strftime('%Y%m%d')}"

        if not hasattr(self, '_prices_cache'):
            self._prices_cache = {}

        if cache_key in self._prices_cache:
            logger.info(f"Cache hit [key={cache_key}]")
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
        return self.unavailable_until is not None and datetime.now(timezone.utc) < self.unavailable_until

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

                quarter_prices = []
                for line in file_content.splitlines():
                    if line.startswith(target_date.strftime("%Y;%m;%d")):
                        parts = line.split(";")
                        quarter = int(parts[3]) - 1  # Convert 1-based quarter to 0-based (1->0, 2->1, 3->2, 4->3, etc.)
                        price = round(float(parts[5]) / 1000, 3)
                        quarter_prices.append((quarter, price))

                if not quarter_prices:
                    raise ValueError("No quarter prices found")

                # Normalize to 24 hours: take first quarter of each hour
                for hour in range(24):
                    first_quarter_of_hour = hour * 4  # Each hour has 4 quarters
                    # Find the price for the first quarter of this hour
                    for quarter, price in quarter_prices:
                        if quarter == first_quarter_of_hour:
                            hourly_prices.append((hour, price))
                            break

                if not hourly_prices:
                    raise ValueError("No hourly prices found after normalization")

                return hourly_prices
            except Exception as e:
                logger.error(f"Failed to fetch/parse prices, retrying [error={e}, retry_in_seconds={self.RETRY_TIME_SECONDS}]")
                retries += 1
                if retries >= self.MAX_RETRIES:
                    break
                time.sleep(self.RETRY_TIME_SECONDS)

        self.unavailable_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        logger.error(f"Failed to fetch prices after retries [max_retries={self.MAX_RETRIES}, unavailable_until={self.unavailable_until}]")
        return []


PROVIDERS = {
    "omie": OmieProvider(),
}
