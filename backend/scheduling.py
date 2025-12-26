from __future__ import annotations

import logging
from abc import ABC, abstractmethod


class SchedulingStrategy(ABC):
    """Abstract base class for scheduling strategies."""

    @abstractmethod
    def calculate_target_hours(self, prices: list[tuple[int, float]], config: dict) -> list[int]:
        """Calculate target hours to turn on the plug.

        Args:
            prices: List of (hour, price) tuples for the day
            config: Strategy-specific configuration

        Returns:
            List of hours (0-23) when plug should be turned ON
        """
        pass


class PeriodStrategy(SchedulingStrategy):
    """Period-based strategy (existing behavior).

    Finds the cheapest hour(s) within each defined period.
    """

    def calculate_target_hours(self, prices: list[tuple[int, float]], config: dict) -> list[int]:
        """Calculate cheapest hours within configured periods.

        Config format:
        {
            'periods': [
                {'start_hour': 0, 'end_hour': 8, 'runtime_hours': 2},
                {'start_hour': 20, 'end_hour': 23, 'runtime_hours': 2}
            ]
        }
        """
        periods = config.get('periods', [])
        target_hours = []

        for period in periods:
            start_hour = period['start_hour']
            end_hour = period['end_hour']
            runtime_hours = period.get('runtime_hours', 1)

            # Filter prices within this period
            period_prices = [(h, p) for h, p in prices if start_hour <= h <= end_hour]

            if not period_prices:
                continue

            # Sort by price and take cheapest N hours
            sorted_prices = sorted(period_prices, key=lambda x: x[1])
            cheapest = sorted_prices[:runtime_hours]

            # Add hours to target list (sorted by hour for readability)
            target_hours.extend(sorted([h for h, p in cheapest]))

        return target_hours


class ValleyDetectionStrategy(SchedulingStrategy):
    """Valley detection strategy with device profiles.

    Automatically finds price valleys and selects best ones based on device profile.
    """

    DEVICE_PROFILES = {
        'water_heater': {
            'windows': [
                {'name': 'morning', 'start': 2, 'end': 7},
                {'name': 'evening', 'start': 18, 'end': 22}
            ],
            'cycles': 2  # Split runtime into 2 equal cycles
        },
        'radiator': {
            'windows': [
                {'name': 'full_day', 'start': 0, 'end': 23}
            ],
            'cycles': 3,  # Distribute runtime across 3 valleys
            'max_valley_hours': 2  # Max hours per valley
        },
        'generic': {
            'windows': [
                {'name': 'full_day', 'start': 0, 'end': 23}
            ],
            'cycles': 1  # Single cheapest valley
        }
    }

    def calculate_target_hours(self, prices: list[tuple[int, float]], config: dict) -> list[int]:
        """Calculate target hours using valley detection.

        Config format:
        {
            'device_profile': 'water_heater',  # or 'radiator', 'generic'
            'runtime_hours': 4,
            'time_constraints': '22:00-08:00',  # optional, overrides profile windows
            'morning_window': '04:00-10:00',  # optional, for water_heater profile
            'evening_window': '16:00-20:00'   # optional, for water_heater profile
        }
        """
        device_profile = config.get('device_profile', 'generic')
        runtime_hours = config.get('runtime_hours', 1)
        time_constraints = config.get('time_constraints')
        morning_window = config.get('morning_window')
        evening_window = config.get('evening_window')

        profile = self.DEVICE_PROFILES.get(device_profile)
        if not profile:
            logging.warning(f"Unknown device profile, using generic [profile={device_profile}]")
            profile = self.DEVICE_PROFILES['generic']

        # Determine windows to use
        if time_constraints:
            # Override all windows with single constraint
            windows = self._parse_time_constraints(time_constraints)
        elif device_profile == 'water_heater' and (morning_window or evening_window):
            # Custom morning/evening windows for water_heater
            windows = []
            if morning_window:
                parsed = self._parse_time_constraints(morning_window)
                if parsed:
                    windows.append({'name': 'morning', 'start': parsed[0]['start'], 'end': parsed[0]['end']})
            else:
                # Use default morning window
                windows.append({'name': 'morning', 'start': 2, 'end': 7})

            if evening_window:
                parsed = self._parse_time_constraints(evening_window)
                if parsed:
                    windows.append({'name': 'evening', 'start': parsed[0]['start'], 'end': parsed[0]['end']})
            else:
                # Use default evening window
                windows.append({'name': 'evening', 'start': 18, 'end': 22})
        else:
            # Use profile defaults
            windows = profile['windows']

        cycles = profile['cycles']
        hours_per_cycle = runtime_hours / cycles
        max_valley_hours = profile.get('max_valley_hours', hours_per_cycle)

        target_hours = []

        # For water_heater: split runtime equally across windows
        if device_profile == 'water_heater' and len(windows) == 2:
            for window in windows:
                window_prices = [(h, p) for h, p in prices if window['start'] <= h <= window['end']]
                if window_prices:
                    valley_hours = self._find_cheapest_contiguous_block(
                        window_prices,
                        int(hours_per_cycle)
                    )
                    target_hours.extend(valley_hours)
                    logging.info(f"Water heater {window['name']} valley [hours={valley_hours}]")

        # For radiator: find N valleys distributed across day
        elif device_profile == 'radiator':
            window = windows[0]  # Use full day window
            window_prices = [(h, p) for h, p in prices if window['start'] <= h <= window['end']]

            for i in range(cycles):
                if not window_prices:
                    break

                valley_hours = self._find_cheapest_contiguous_block(
                    window_prices,
                    min(int(max_valley_hours), int(hours_per_cycle))
                )
                target_hours.extend(valley_hours)

                # Remove used hours to find next valley
                window_prices = [(h, p) for h, p in window_prices if h not in valley_hours]

                # Also remove adjacent hours to ensure distribution
                window_prices = [(h, p) for h, p in window_prices
                                if not any(abs(h - used_h) <= 1 for used_h in valley_hours)]

        # For generic: single cheapest valley
        else:
            window = windows[0]
            window_prices = [(h, p) for h, p in prices if window['start'] <= h <= window['end']]
            if window_prices:
                valley_hours = self._find_cheapest_contiguous_block(
                    window_prices,
                    int(runtime_hours)
                )
                target_hours.extend(valley_hours)

        return sorted(target_hours)

    def _find_cheapest_contiguous_block(self, prices: list[tuple[int, float]], block_size: int) -> list[int]:
        """Find the cheapest contiguous block of hours.

        Args:
            prices: List of (hour, price) tuples
            block_size: Number of contiguous hours needed

        Returns:
            List of hours forming the cheapest block
        """
        if not prices or block_size <= 0:
            return []

        # Sort prices by hour to ensure contiguity
        sorted_prices = sorted(prices, key=lambda x: x[0])

        best_block = []
        best_avg_price = float('inf')

        # Try all possible contiguous blocks
        for i in range(len(sorted_prices) - block_size + 1):
            # Check if hours are contiguous
            block = sorted_prices[i:i + block_size]
            hours = [h for h, p in block]

            # Verify contiguity
            if hours[-1] - hours[0] == block_size - 1:
                avg_price = sum(p for h, p in block) / block_size
                if avg_price < best_avg_price:
                    best_avg_price = avg_price
                    best_block = hours

        # If no contiguous block found, fall back to cheapest N hours
        if not best_block:
            sorted_by_price = sorted(sorted_prices, key=lambda x: x[1])
            best_block = sorted([h for h, p in sorted_by_price[:block_size]])
            logging.warning(f"No contiguous block found, using cheapest hours [hours={best_block}]")

        return best_block

    def _parse_time_constraints(self, constraints: str) -> list[dict]:
        """Parse time constraints string into window dictionaries.

        Args:
            constraints: String like "22:00-08:00" or "00:00-23:59"

        Returns:
            List of window dicts with start/end hours
        """
        try:
            start_str, end_str = constraints.split('-')
            start_hour = int(start_str.split(':')[0])
            end_hour = int(end_str.split(':')[0])

            return [{'name': 'custom', 'start': start_hour, 'end': end_hour}]
        except Exception as e:
            logging.error(f"Failed to parse time constraints [constraints={constraints}, error={e}]")
            return [{'name': 'full_day', 'start': 0, 'end': 23}]


def create_strategy(strategy_name: str) -> SchedulingStrategy:
    """Factory function to create scheduling strategy instances.

    Args:
        strategy_name: Name of strategy ('period', 'valley_detection')

    Returns:
        Instance of SchedulingStrategy
    """
    strategies = {
        'period': PeriodStrategy,
        'valley_detection': ValleyDetectionStrategy
    }

    strategy_class = strategies.get(strategy_name)
    if not strategy_class:
        logging.warning(f"Unknown strategy, defaulting to period [strategy={strategy_name}]")
        strategy_class = PeriodStrategy

    return strategy_class()
