from __future__ import annotations

import logging
import os
import time
from datetime import datetime

# Set matplotlib backend to non-GUI before importing pyplot
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import CONFIG_FILE_PATH, CHART_FILE_NAME, PLUG_STATES_FILE_PATH, config, get_provider
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
    last_states_mtime = None
    target_date = None

    manager_from_email = None
    manager_to_email = None
    provider = None

    should_continue = lambda: True if stop_event is None else not stop_event.is_set()

    while should_continue():
        current_config_mtime = os.path.getmtime(CONFIG_FILE_PATH)

        # Check if plug_states.json exists and get its mtime
        try:
            current_states_mtime = os.path.getmtime(PLUG_STATES_FILE_PATH)
        except FileNotFoundError:
            current_states_mtime = None

        # Reload if config or plug states have changed
        config_changed = current_config_mtime != last_config_mtime
        states_changed = current_states_mtime != last_states_mtime

        if config_changed or states_changed:
            if config_changed:
                logging.info(f"Config file changed, recalculating prices [path={CONFIG_FILE_PATH}]")
                last_config_mtime = current_config_mtime
                config.read(CONFIG_FILE_PATH)
                manager_from_email = config.get('email', 'from_email')
                manager_to_email = config.get('email', 'to_email')
                provider = get_provider()
                target_date = None  # Force reloading prices

            if states_changed:
                logging.info(f"Plug states file changed, reloading plugs [path={PLUG_STATES_FILE_PATH}]")
                last_states_mtime = current_states_mtime

            # Always reload shared plugs when either file changes
            plug_manager.reload_plugs(enabled_only=False)

        if provider and (target_date is None or target_date.date() != datetime.now().date()) and not provider.unavailable():
            target_date = datetime.now()
            current_date = target_date.strftime("%Y%m%d")
            current_date_on_file = target_date.strftime("%Y;%m;%d")

            logging.info(f"Loading prices data [date={target_date.date()}]")

            hourly_prices = provider.get_prices(target_date)
            if not hourly_prices:
                logging.warning(f"No prices data available, skipping email [date={target_date.date()}]")
                continue

            email_message = f"<p>💶🔋 Electricity prices for {target_date.date()}:</p>"
            for hour, price in hourly_prices:
                email_message += f"⏱️💶 {hour}h: {price} €/kWh<br>"

            # Get shared plugs for daily email and schedule generation
            plugs = get_plugs(enabled_only=False)
            for plug in plugs:
                plug.calculate_target_hours(hourly_prices)

                email_message += "<p>"
                email_message += f"🔌 {plug.name} ({plug.strategy_name}):<br>"

                if isinstance(plug.strategy_data, ValleyDetectionStrategyData):
                    # Valley detection: show all target hours
                    target_hours = plug.strategy_data.target_hours
                    if target_hours:
                        avg_price = plug.strategy_data.get_average_price()
                        rt_h = plug.strategy_data.runtime_human
                        rt_s = plug.strategy_data.runtime_seconds

                        email_message += f"⬇️💶 Valley hours: {', '.join(f'{h}h' for h in target_hours)}<br>"
                        email_message += f"💶 Average price: {avg_price:.4f} €/kWh<br>"
                        email_message += f"⏱️ Total runtime: {rt_h} ({rt_s} seconds)<br>"
                        email_message += f"📊 Profile: {plug.strategy_data.device_profile}<br>"

                elif isinstance(plug.strategy_data, PeriodStrategyData):
                    # Period strategy: show each period
                    for period in plug.strategy_data.periods:
                        if period.target_hour is None:
                            continue

                        email_message += (
                            f"⬇️💶 Cheapest hour within period ({period.start_hour}h - {period.end_hour}h): "
                            f"{period.target_hour}h - {period.target_price:.4f} €/kWh<br>"
                        )
                        email_message += (
                            f"⏱️ Plug will run for {period.runtime_human} "
                            f"({period.runtime_seconds} seconds) in this period.<br>"
                        )

                email_message += "</p>"

            try:
                os.remove(CHART_FILE_NAME)
            except OSError:
                pass

            fig, ax = plt.subplots()
            ax.bar([h for h, p in hourly_prices], [p for h, p in hourly_prices])
            ax.set_title(f"Electricity prices for {target_date.date()}")
            ax.set_xlabel("Hour")
            ax.set_ylabel("Price (€/kWh)")
            fig.savefig(CHART_FILE_NAME)

            send_email(
                f'💶🔋 Electricity prices for {target_date.date()}',
                email_message,
                manager_from_email,
                manager_to_email,
                True
            )
            logging.info(f"Downloaded prices data and sent email [date={target_date.date()}]")

            # Generate automatic schedules for enabled plugs
            generate_automatic_schedules(plugs, hourly_prices, target_date)

        # Process scheduled events (uses shared plug manager)
        if manager_from_email and manager_to_email:
            process_scheduled_events(manager_from_email, manager_to_email)

        # Sleep for 30 seconds, checking stop_event every second if provided
        if stop_event is None:
            try:
                time.sleep(30)
            except KeyboardInterrupt:
                logging.info("Exiting")
                break
        else:
            for _ in range(30):
                if stop_event.is_set():
                    break
                stop_event.wait(1)


if __name__ == '__main__':
    run_manager_main()
