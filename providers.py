import time
import requests
import logging
from datetime import datetime
from abc import ABC, abstractmethod

class PricesProvider(ABC):
    @abstractmethod
    def get_prices(self, target_date: datetime) -> list[tuple[int, float]]:
        pass

class OmieProvider(PricesProvider):
    BASE_URL = "https://www.omie.es/es/file-download?parents=marginalpdbc&filename=marginalpdbc_{date}.1"

    def get_prices(self, target_date: datetime) -> list[tuple[int, float]]:
        current_date = target_date.strftime("%Y%m%d")
        hourly_prices = []

        # Retry loop: keep trying every 15s until we fetch and parse successfully
        while True:
            try:
                response = requests.get(self.BASE_URL.format(date=current_date), timeout=10)
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
                logging.error(f"Failed to fetch/parse prices: {e}. Retrying in 15s…")
                time.sleep(15)

PROVIDERS = {
    "omie": OmieProvider,
}
