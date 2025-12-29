from __future__ import annotations

import logging
import os
import time
from datetime import datetime

from config import CONFIG_FILE_PATH, config, get_provider, TIMEZONE

logger = logging.getLogger("uvicorn.error")
from email_templates import render_daily_summary_email
from notifications import send_email
from plugs import get_plugs, plug_manager
from schedules import generate_automatic_schedules, process_scheduled_events
from scheduling import PeriodStrategyData, ValleyDetectionStrategyData


def run_manager_main(stop_event=None):
    """Run the manager main loop.

    Args:
        stop_event: Optional threading.Event to signal graceful shutdown.
                   If None, runs indefinitely (for standalone execution).
                   If provided, checks stop_event.is_set() for shutdown.
    """
    last_config_mtime = None
    target_date = None

    manager_from_email = None
    manager_to_email = None
    provider = None

    should_continue = lambda: True if stop_event is None else not stop_event.is_set()

    while should_continue():
        current_config_mtime = os.path.getmtime(CONFIG_FILE_PATH)
        config_changed = current_config_mtime != last_config_mtime

        if config_changed:
            logger.info(f"Config file changed, recalculating prices [path={CONFIG_FILE_PATH}]")
            last_config_mtime = current_config_mtime
            config.read(CONFIG_FILE_PATH)
            manager_from_email = config.get('email', 'from_email')
            manager_to_email = config.get('email', 'to_email')
            provider = get_provider()
            target_date = None  # Force reloading prices

            # Reload shared plugs when config changes
            plug_manager.reload_plugs()

        if provider and (target_date is None or target_date.date() != datetime.now(TIMEZONE).date()) and not provider.unavailable():
            target_date = datetime.now(TIMEZONE)

            logger.info(f"Loading prices data [date={target_date.date()}]")

            hourly_prices = provider.get_prices(target_date)
            if not hourly_prices:
                logger.warning(f"No prices data available, skipping email [date={target_date.date()}]")
                continue

            # Get shared plugs for daily email and schedule generation
            plugs = get_plugs(automatic_only=False)

            # Build plug info for email template
            plugs_info = []
            for plug in plugs:
                plug.calculate_target_hours(hourly_prices)

                plug_data = {
                    'name': plug.name,
                    'strategy_name': plug.strategy_name,
                    'strategy_type': '',
                    'periods': [],
                    'valley_info': {}
                }

                if isinstance(plug.strategy_data, ValleyDetectionStrategyData):
                    plug_data['strategy_type'] = 'valley'
                    target_hours = plug.strategy_data.target_hours
                    if target_hours:
                        plug_data['valley_info'] = {
                            'target_hours': target_hours,
                            'avg_price': plug.strategy_data.get_average_price(),
                            'runtime_human': plug.strategy_data.runtime_human,
                            'runtime_seconds': plug.strategy_data.runtime_seconds,
                            'device_profile': plug.strategy_data.device_profile
                        }

                elif isinstance(plug.strategy_data, PeriodStrategyData):
                    plug_data['strategy_type'] = 'period'
                    for idx, period in enumerate(plug.strategy_data.periods):
                        if period.target_hour is not None:
                            plug_data['periods'].append({
                                'period_name': f"Period {idx + 1} ({period.start_hour}h - {period.end_hour}h)",
                                'target_hour': period.target_hour,
                                'target_price': period.target_price,
                                'runtime_human': period.runtime_human
                            })

                plugs_info.append(plug_data)

            # Render email using new template
            email_html = render_daily_summary_email(
                str(target_date.date()),
                hourly_prices,
                plugs_info
            )

            send_email(
                f'💶🔋 Electricity prices for {target_date.date()}',
                email_html,
                manager_from_email,
                manager_to_email,
                attach_chart=False
            )
            logger.info(f"Downloaded prices data and sent email [date={target_date.date()}]")

            # Generate automatic schedules for automatic plugs
            generate_automatic_schedules(plugs, hourly_prices, target_date)

        # Process scheduled events (uses shared plug manager)
        if manager_from_email and manager_to_email:
            process_scheduled_events(manager_from_email, manager_to_email)

        # Sleep for 30 seconds, checking stop_event every second if provided
        if stop_event is None:
            try:
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Exiting")
                break
        else:
            for _ in range(30):
                if stop_event.is_set():
                    break
                stop_event.wait(1)


if __name__ == '__main__':
    run_manager_main()
