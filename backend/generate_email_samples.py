#!/usr/bin/env python3
"""Generate sample HTML files for all email types for testing."""

from datetime import datetime
from email_templates import render_daily_summary_email, render_schedule_execution_email

# Sample data for daily summary email
sample_prices = [
    (0, 0.15234), (1, 0.14567), (2, 0.13890), (3, 0.13456), (4, 0.13123), (5, 0.13890),
    (6, 0.15678), (7, 0.18234), (8, 0.21567), (9, 0.23890), (10, 0.25234), (11, 0.24567),
    (12, 0.22890), (13, 0.21234), (14, 0.20567), (15, 0.19890), (16, 0.21234), (17, 0.23567),
    (18, 0.26890), (19, 0.28234), (20, 0.27567), (21, 0.25890), (22, 0.22234), (23, 0.18567)
]

sample_plugs_period = [
    {
        'name': 'Water Heater',
        'strategy_name': 'Period Strategy',
        'strategy_type': 'period',
        'periods': [
            {
                'period_name': 'Period 1 (0h - 6h)',
                'target_hour': 3,
                'target_price': 0.13456,
                'runtime_human': '2h'
            },
            {
                'period_name': 'Period 2 (18h - 23h)',
                'target_hour': 22,
                'target_price': 0.22234,
                'runtime_human': '1h'
            }
        ],
        'valley_info': {}
    }
]

sample_plugs_valley = [
    {
        'name': 'Radiator',
        'strategy_name': 'Valley Detection',
        'strategy_type': 'valley',
        'periods': [],
        'valley_info': {
            'target_hours': [2, 3, 4, 5],
            'avg_price': 0.13365,
            'runtime_human': '1h 30m',
            'runtime_seconds': 5400,
            'device_profile': 'water_heater'
        }
    }
]

sample_plugs_mixed = sample_plugs_period + sample_plugs_valley + [
    {
        'name': 'Home Server',
        'strategy_name': 'Period Strategy',
        'strategy_type': 'period',
        'periods': [
            {
                'period_name': 'Period 1 (0h - 23h)',
                'target_hour': 3,
                'target_price': 0.13456,
                'runtime_human': '20h'
            }
        ],
        'valley_info': {}
    }
]

# Generate daily summary emails
print("Generating daily summary email samples...")

# 1. Daily summary with period strategy
with open('/tmp/email_daily_period.html', 'w') as f:
    html = render_daily_summary_email('2025-12-29', sample_prices, sample_plugs_period)
    f.write(html)
print("✓ Generated: /tmp/email_daily_period.html")

# 2. Daily summary with valley detection
with open('/tmp/email_daily_valley.html', 'w') as f:
    html = render_daily_summary_email('2025-12-29', sample_prices, sample_plugs_valley)
    f.write(html)
print("✓ Generated: /tmp/email_daily_valley.html")

# 3. Daily summary with mixed strategies
with open('/tmp/email_daily_mixed.html', 'w') as f:
    html = render_daily_summary_email('2025-12-29', sample_prices, sample_plugs_mixed)
    f.write(html)
print("✓ Generated: /tmp/email_daily_mixed.html")

# Generate schedule execution emails
print("\nGenerating schedule execution email samples...")

# 4. Automatic schedule - OFF to ON with duration
with open('/tmp/email_schedule_auto_on.html', 'w') as f:
    html = render_schedule_execution_email(
        plug_name='Water Heater',
        event_type='automatic',
        from_state=False,
        to_state=True,
        timestamp='Dec 29, 03:00',
        duration_info='Will turn OFF in 2h'
    )
    f.write(html)
print("✓ Generated: /tmp/email_schedule_auto_on.html")

# 5. Automatic schedule - ON to OFF
with open('/tmp/email_schedule_auto_off.html', 'w') as f:
    html = render_schedule_execution_email(
        plug_name='Water Heater',
        event_type='automatic',
        from_state=True,
        to_state=False,
        timestamp='Dec 29, 05:00',
        duration_info=''
    )
    f.write(html)
print("✓ Generated: /tmp/email_schedule_auto_off.html")

# 6. Manual schedule - OFF to ON
with open('/tmp/email_schedule_manual_on.html', 'w') as f:
    html = render_schedule_execution_email(
        plug_name='Multipurpose',
        event_type='manual',
        from_state=False,
        to_state=True,
        timestamp='Dec 29, 14:30',
        duration_info='Will turn OFF in 30m'
    )
    f.write(html)
print("✓ Generated: /tmp/email_schedule_manual_on.html")

# 7. Manual schedule - ON to OFF
with open('/tmp/email_schedule_manual_off.html', 'w') as f:
    html = render_schedule_execution_email(
        plug_name='Home Server',
        event_type='manual',
        from_state=True,
        to_state=False,
        timestamp='Dec 29, 22:15',
        duration_info=''
    )
    f.write(html)
print("✓ Generated: /tmp/email_schedule_manual_off.html")

# 8. Repeating schedule - OFF to ON with duration
with open('/tmp/email_schedule_repeating_on.html', 'w') as f:
    html = render_schedule_execution_email(
        plug_name='Coffee Machine',
        event_type='repeating',
        from_state=False,
        to_state=True,
        timestamp='Dec 29, 07:00',
        duration_info='Will turn OFF in 15m'
    )
    f.write(html)
print("✓ Generated: /tmp/email_schedule_repeating_on.html")

# 9. Repeating schedule - ON to OFF
with open('/tmp/email_schedule_repeating_off.html', 'w') as f:
    html = render_schedule_execution_email(
        plug_name='Living Room Lamp',
        event_type='repeating',
        from_state=True,
        to_state=False,
        timestamp='Dec 29, 23:30',
        duration_info=''
    )
    f.write(html)
print("✓ Generated: /tmp/email_schedule_repeating_off.html")

print("\n✅ All email samples generated successfully!")
print("\nFiles created:")
print("  - /tmp/email_daily_period.html")
print("  - /tmp/email_daily_valley.html")
print("  - /tmp/email_daily_mixed.html")
print("  - /tmp/email_schedule_auto_on.html")
print("  - /tmp/email_schedule_auto_off.html")
print("  - /tmp/email_schedule_manual_on.html")
print("  - /tmp/email_schedule_manual_off.html")
print("  - /tmp/email_schedule_repeating_on.html")
print("  - /tmp/email_schedule_repeating_off.html")
