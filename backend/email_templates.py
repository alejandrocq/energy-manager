from __future__ import annotations

# SVG Icon Functions (inline, from Font Awesome 6 and Material Design)
# All icons now accept width and color parameters for flexibility

def icon_energy_leaf(width: int = 36, color: str = "#15803d") -> str:
    """Energy leaf icon (Material Design)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 24 24" fill="{color}" style="vertical-align: middle; display: inline-block;"><path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C7 8 17 8 17 8z"/></svg>'

def icon_plug(width: int = 24, color: str = "#6366f1") -> str:
    """Plug icon (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 384 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M96 0C78.3 0 64 14.3 64 32v96h64V32c0-17.7-14.3-32-32-32zM288 0c-17.7 0-32 14.3-32 32v96h64V32c0-17.7-14.3-32-32-32zM32 160c-17.7 0-32 14.3-32 32s14.3 32 32 32v32c0 77.4 55 142 128 156.8V480c0 17.7 14.3 32 32 32s32-14.3 32-32V412.8C297 398 352 333.4 352 256V224c17.7 0 32-14.3 32-32s-14.3-32-32-32H32z"/></svg>'

def icon_clock(width: int = 24, color: str = "#6b7280") -> str:
    """Clock icon (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 512 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M256 0a256 256 0 1 1 0 512A256 256 0 1 1 256 0zM232 120V256c0 8 4 15.5 10.7 20l96 64c11 7.4 25.9 4.4 33.3-6.7s4.4-25.9-6.7-33.3L280 243.2V120c0-13.3-10.7-24-24-24s-24 10.7-24 24z"/></svg>'

def icon_calendar(width: int = 24, color: str = "#14b8a6") -> str:
    """Calendar icon (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 448 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M128 0c13.3 0 24 10.7 24 24V64H296V24c0-13.3 10.7-24 24-24s24 10.7 24 24V64h40c35.3 0 64 28.7 64 64v16 48V448c0 35.3-28.7 64-64 64H64c-35.3 0-64-28.7-64-64V192 144 128C0 92.7 28.7 64 64 64h40V24c0-13.3 10.7-24 24-24zM400 192H48V448c0 8.8 7.2 16 16 16H384c8.8 0 16-7.2 16-16V192z"/></svg>'

def icon_power(width: int = 24, color: str = "#6b7280") -> str:
    """Power icon (Material Design)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 24 24" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z"/></svg>'

def icon_chart(width: int = 24, color: str = "#6366f1") -> str:
    """Chart bar icon (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 512 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M32 32c17.7 0 32 14.3 32 32V400c0 8.8 7.2 16 16 16H480c17.7 0 32 14.3 32 32s-14.3 32-32 32H80c-44.2 0-80-35.8-80-80V64C0 46.3 14.3 32 32 32zM160 224c17.7 0 32 14.3 32 32v64c0 17.7-14.3 32-32 32s-32-14.3-32-32V256c0-17.7 14.3-32 32-32zm128-64c0-17.7 14.3-32 32-32s32 14.3 32 32V320c0 17.7-14.3 32-32 32s-32-14.3-32-32V160zm128-32c17.7 0 32 14.3 32 32V320c0 17.7-14.3 32-32 32s-32-14.3-32-32V160c0-17.7 14.3-32 32-32z"/></svg>'

def icon_euro(width: int = 20, color: str = "#6b7280") -> str:
    """Euro icon (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 320 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M48.1 240c-.1 2.7-.1 5.3-.1 8v16c0 2.7 0 5.3 .1 8H32c-17.7 0-32 14.3-32 32s14.3 32 32 32H60.3C89.9 419.9 170 480 264 480h24c17.7 0 32-14.3 32-32s-14.3-32-32-32H264c-57.9 0-108.2-32.4-133.9-80H256c17.7 0 32-14.3 32-32s-14.3-32-32-32H112.2c-.1-2.6-.2-5.3-.2-8V248c0-2.7 .1-5.4 .2-8H256c17.7 0 32-14.3 32-32s-14.3-32-32-32H130.1c25.7-47.6 76-80 133.9-80h24c17.7 0 32-14.3 32-32s-14.3-32-32-32H264C170 32 89.9 92.1 60.3 176H32c-17.7 0-32 14.3-32 32s14.3 32 32 32H48.1z"/></svg>'

def icon_arrow_down(width: int = 20, color: str = "#6b7280") -> str:
    """Arrow down/valley icon (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 384 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M169.4 470.6c12.5 12.5 32.8 12.5 45.3 0l160-160c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L224 370.8 224 64c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 306.7L54.6 265.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l160 160z"/></svg>'

def icon_chart_pie(width: int = 20, color: str = "#6b7280") -> str:
    """Chart pie icon for profile (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 576 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M304 16V304H592C592 155.1 456.9 16 304 16zM32 304C32 458.2 154.2 576 304 576C450.5 576 570.4 462.2 576 320H320V48C171.2 53.6 32 173.5 32 304z"/></svg>'

def icon_arrow_right(width: int = 32, color: str = "#6366f1") -> str:
    """Arrow right icon."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 24 24" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/></svg>'


def icon_tag(width: int = 20, color: str = "#6b7280") -> str:
    """Tag/label icon (Font Awesome 6)."""
    return f'<svg width="{width}" height="{width}" viewBox="0 0 448 512" fill="{color}" style="vertical-align: middle; display: inline-block; flex-shrink: 0;"><path d="M0 80V229.5c0 17 6.7 33.3 18.7 45.3l176 176c25 25 65.5 25 90.5 0L418.7 317.3c25-25 25-65.5 0-90.5l-176-176c-12-12-28.3-18.7-45.3-18.7H48C21.5 32 0 53.5 0 80zm112 32a32 32 0 1 1 0 64 32 32 0 1 1 0-64z"/></svg>'


def render_badge(text: str, bg_color: str, text_color: str) -> str:
    """Render a status badge."""
    return f'''<span style="display: inline-flex; align-items: center; padding: 2px 8px; font-size: 11px; font-weight: 600;
                 color: {text_color}; background-color: {bg_color}; border-radius: 4px; flex-shrink: 0;">{text}</span>'''


def render_state_badge(state: bool, large: bool = False) -> str:
    """Render ON/OFF state badge with appropriate colors."""
    if large:
        # Large badges for state transitions
        padding = "12px 28px"
        font_size = "15px"
        border_radius = "8px"
    else:
        # Small badges for inline use
        padding = "2px 8px"
        font_size = "11px"
        border_radius = "4px"

    if state:
        bg_color, text_color = "#d1fae5", "#065f46"  # green-100, green-900
        text = "ON"
    else:
        bg_color, text_color = "#fee2e2", "#991b1b"  # red-100, red-900
        text = "OFF"

    return f'''<span style="display: inline-flex; align-items: center; padding: {padding}; font-size: {font_size}; font-weight: 700;
                 color: {text_color}; background-color: {bg_color}; border-radius: {border_radius}; flex-shrink: 0;">{text}</span>'''


def render_type_badge(event_type: str) -> str:
    """Render Auto/Manual/Repeating badge."""
    if event_type == "automatic":
        return render_badge("Auto", "#dbeafe", "#1e40af")  # blue-100, blue-800
    elif event_type == "repeating":
        return render_badge("Repeating", "#ccfbf1", "#0f766e")  # teal-100, teal-700
    else:
        return render_badge("Manual", "#e9d5ff", "#6b21a8")  # purple-100, purple-800


def render_mode_badge(automatic: bool) -> str:
    """Render Auto/Manual mode badge for plugs."""
    if automatic:
        return render_badge("Auto", "#dbeafe", "#1e40af")  # blue-100, blue-800
    else:
        return render_badge("Manual", "#fef3c7", "#92400e")  # amber-100, amber-800


def render_pending_schedules(schedules: list[dict]) -> str:
    """Render pending schedules list for a plug."""
    if not schedules:
        return '<div style="font-size: 12px; color: #9ca3af; font-style: italic;">No pending schedules</div>'

    html = '<div style="display: flex; flex-direction: column; gap: 4px; margin-top: 8px;">'
    html += '<div style="font-size: 12px; font-weight: 600; color: #6b7280;">Pending Schedules:</div>'

    for schedule in schedules:
        type_badge = render_type_badge(schedule['type'])
        state_badge = render_state_badge(schedule['desired_state'])
        time_str = schedule['target_datetime']
        duration = schedule.get('duration_human', '')
        recurrence_pattern = schedule.get('recurrence_pattern', '')

        duration_html = f'<span style="color: #9ca3af;">({duration})</span>' if duration else ''
        recurrence_html = f'<div style="font-size: 11px; color: #6b7280; margin-left: 20px;">{recurrence_pattern}</div>' if recurrence_pattern else ''

        html += f'''
        <div style="display: flex; flex-direction: column; gap: 2px;">
            <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #374151; padding: 4px 0;">
                {type_badge}
                {icon_clock(14)}
                <span>{time_str}</span>
                {icon_arrow_right(14)}
                {state_badge}
                {duration_html}
            </div>
            {recurrence_html}
        </div>
        '''

    html += '</div>'
    return html


def render_header() -> str:
    """Render email header with Energy Manager branding."""
    return f'''
    <div style="display: flex; justify-content: center; background-color: #f9f9f9; padding: 20px 0; border-bottom: 3px solid #6366f1;">
        <div style="display: flex; align-items: center; gap: 8px; width: 600px; max-width: 100%;
                    font-family: Arial, sans-serif; font-size: 28px; font-weight: bold; color: #111827;">
            {icon_energy_leaf()}
            <span>Energy Manager</span>
        </div>
    </div>
    '''


def render_card(content: str, title: str = "") -> str:
    """Render a card container matching UI style."""
    title_html = ""
    if title:
        title_html = f'<div style="font-size: 16px; font-weight: 600; color: #111827; margin-bottom: 12px;">{title}</div>'

    return f'''
    <div style="display: flex; flex-direction: column; background-color: white; border: 1px solid #e5e7eb;
                border-radius: 8px; margin-bottom: 16px; padding: 16px;
                font-family: Arial, sans-serif; font-size: 14px; color: #374151;">
        {title_html}
        {content}
    </div>
    '''


def render_state_transition(from_state: bool, to_state: bool) -> str:
    """Render state transition with arrow."""
    from_badge = render_state_badge(from_state, large=True)
    to_badge = render_state_badge(to_state, large=True)

    return f'''
    <div style="display: flex; align-items: center; justify-content: center; font-size: 20px; margin: 32px 0; gap: 5px;">
        {from_badge}
        {icon_arrow_right(48, "#6366f1")}
        {to_badge}
    </div>
    '''


def get_price_color(price: float, min_price: float, max_price: float) -> str:
    """Calculate color for a price based on min/max range (green = cheap, red = expensive)."""
    if max_price == min_price:
        return "#10b981"  # emerald-500

    # Normalize price to 0-1 range
    normalized = (price - min_price) / (max_price - min_price)

    # Color gradient: green (cheap) -> yellow -> red (expensive)
    if normalized < 0.33:
        return "#10b981"  # emerald-500 (green)
    elif normalized < 0.67:
        return "#f59e0b"  # amber-500 (yellow)
    else:
        return "#ef4444"  # red-500 (red)


def render_inline_chart(prices: list[tuple[int, float]], target_hours: list[int] = None) -> str:
    """Render HTML/CSS bar chart for electricity prices."""
    if not prices:
        return "<p>No price data available</p>"

    min_price = min(p for _, p in prices)
    max_price = max(p for _, p in prices)
    price_range = max_price - min_price if max_price > min_price else 1

    target_hours = target_hours or []

    chart_rows = ""
    for hour, price in prices:
        # Calculate bar width (percentage of max price)
        width_pct = ((price - min_price) / price_range * 100) if price_range > 0 else 50

        # Get color for this price
        bar_color = get_price_color(price, min_price, max_price)

        # Highlight target hours with badge
        target_badge = f'''<span style="display: inline-flex; align-items: center; padding: 2px 6px; font-size: 10px;
                                       font-weight: 600; color: #1e40af; background-color: #dbeafe; border-radius: 3px;">Target</span>''' if hour in target_hours else ""

        chart_rows += f'''
        <div style="display: flex; align-items: center; gap: 8px; padding: 2px 0;">
            <div style="font-family: Arial, sans-serif; font-size: 12px; color: #6b7280; text-align: right;
                        width: 32px; flex-shrink: 0;">{hour}h</div>
            <div style="flex: 1; min-width: 0;">
                <div style="background-color: {bar_color}; height: 20px; width: {width_pct}%;
                            border-radius: 4px;"></div>
            </div>
            <div style="display: flex; align-items: center; gap: 6px; font-family: Arial, sans-serif;
                        font-size: 12px; color: #374151; flex-shrink: 0;">
                <span>{price:.4f} €/kWh</span>
                {target_badge}
            </div>
        </div>
        '''

    return f'''
    <div style="display: flex; flex-direction: column; gap: 2px; margin: 16px 0;">
        <div style="display: flex; align-items: center; gap: 8px; font-family: Arial, sans-serif;
                    font-size: 14px; font-weight: 600; color: #111827; padding-bottom: 12px;">
            {icon_chart()}
            <span>Hourly Electricity Prices</span>
        </div>
        {chart_rows}
    </div>
    '''


def render_daily_summary_email(date: str, prices: list[tuple[int, float]], plugs_info: list[dict]) -> str:
    """
    Render the daily price summary email.

    Args:
        date: Date string (e.g., "2025-01-15")
        prices: List of (hour, price) tuples
        plugs_info: List of dicts with plug information:
            {
                'name': str,
                'strategy_name': str | None,  # None if no strategy configured
                'strategy_type': 'period' | 'valley' | None,
                'automatic_mode': bool,  # True = automatic, False = manual
                'current_status': bool | None,  # True = ON, False = OFF, None = unknown
                'periods': [  # For period strategy
                    {
                        'period_name': str,
                        'target_hour': int,
                        'target_price': float,
                        'runtime_human': str
                    }
                ],
                'valley_info': {  # For valley strategy
                    'target_hours': list[int],
                    'avg_price': float,
                    'runtime_human': str,
                    'runtime_seconds': int,
                    'device_profile': str
                },
                'pending_schedules': [  # All pending schedules for this plug
                    {
                        'type': 'automatic' | 'manual' | 'repeating',
                        'target_datetime': str,  # Local time formatted
                        'desired_state': bool,
                        'duration_human': str | None
                    }
                ]
            }
    """
    # Collect all target hours for chart highlighting
    all_target_hours = []
    for plug_info in plugs_info:
        if plug_info['strategy_type'] == 'period':
            for period in plug_info.get('periods', []):
                if period.get('target_hour') is not None:
                    all_target_hours.append(period['target_hour'])
        elif plug_info['strategy_type'] == 'valley':
            valley_info = plug_info.get('valley_info', {})
            all_target_hours.extend(valley_info.get('target_hours', []))

    # Render price chart
    chart_html = render_inline_chart(prices, all_target_hours)

    # Render plugs
    plugs_html = ""
    for plug_info in plugs_info:
        # Get mode and status
        automatic_mode = plug_info.get('automatic_mode', True)
        current_status = plug_info.get('current_status')
        pending_schedules = plug_info.get('pending_schedules', [])

        # Status badge or "Unknown" if status couldn't be fetched
        if current_status is not None:
            status_html = render_state_badge(current_status)
        else:
            status_html = '<span style="font-size: 11px; color: #9ca3af; font-style: italic;">Unknown</span>'

        plug_content = f'''
        <div style="display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: #111827;">
                    {icon_plug()}
                    <span>{plug_info['name']}</span>
                </div>
                {render_mode_badge(automatic_mode)}
            </div>
            <div style="display: flex; align-items: center; gap: 6px; font-size: 13px; color: #6b7280;">
                {icon_power(16)}
                <span>Status:</span>
                {status_html}
            </div>
        '''

        # Strategy section (only if strategy is configured)
        if plug_info.get('strategy_name'):
            plug_content += f'''
            <div style="font-size: 13px; color: #6b7280;">
                Strategy: {plug_info['strategy_name']}
            </div>
            '''

            if plug_info['strategy_type'] == 'period':
                for period in plug_info.get('periods', []):
                    if period.get('target_hour') is None:
                        continue

                    plug_content += f'''
                    <div style="display: flex; flex-direction: column; gap: 4px; background-color: #f0fdf4;
                                padding: 8px; border-radius: 4px; border-left: 3px solid #10b981;">
                        <div style="font-size: 12px; color: #065f46;">
                            <strong>{period['period_name']}</strong>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #374151;">
                            {icon_calendar(16)}
                            <span>Scheduled: <strong>{period['target_hour']}h</strong></span>
                            {icon_arrow_right(16)}
                            {render_state_badge(True)}
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #374151;">
                            {icon_euro(16, "#059669")}
                            <span>Price: <strong>{period['target_price']:.4f} €/kWh</strong></span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #374151;">
                            {icon_clock(16, "#a855f7")}
                            <span>Duration: <strong>{period['runtime_human']}</strong></span>
                        </div>
                    </div>
                    '''

            elif plug_info['strategy_type'] == 'valley':
                valley_info = plug_info.get('valley_info', {})
                hours_str = ', '.join(f"{h}h" for h in valley_info.get('target_hours', []))

                plug_content += f'''
                <div style="display: flex; flex-direction: column; gap: 4px; background-color: #eff6ff;
                            padding: 8px; border-radius: 4px; border-left: 3px solid #3b82f6;">
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #1e40af;">
                        {icon_tag(16, "#3b82f6")}
                        <span>Profile: <strong>{valley_info.get('device_profile', 'Unknown')}</strong></span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #374151;">
                        {icon_arrow_down(16, "#3b82f6")}
                        <span>Valley hours: <strong>{hours_str}</strong></span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #374151;">
                        {icon_euro(16, "#3b82f6")}
                        <span>Average price: <strong>{valley_info.get('avg_price', 0):.4f} €/kWh</strong></span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #374151;">
                        {icon_clock(16, "#a855f7")}
                        <span>Total runtime: <strong>{valley_info.get('runtime_human', 'N/A')}</strong> ({valley_info.get('runtime_seconds', 0)} seconds)</span>
                    </div>
                </div>
                '''

        # Pending schedules section
        plug_content += render_pending_schedules(pending_schedules)

        plug_content += '</div>'
        plugs_html += render_card(plug_content)

    # Build complete email
    email_html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: Arial, sans-serif;">
        {render_header()}

        <div style="display: flex; justify-content: center; background-color: #f3f4f6; padding: 20px 0;">
            <div style="display: flex; flex-direction: column; width: 600px; max-width: 100%; padding: 20px 0;">
                <h2 style="font-family: Arial, sans-serif; font-size: 20px; color: #111827; margin: 0 0 16px 0;">
                    Daily Price Summary - {date}
                </h2>

                {render_card(chart_html)}

                <h3 style="display: flex; align-items: center; gap: 8px; font-family: Arial, sans-serif;
                           font-size: 18px; color: #111827; margin: 24px 0 12px 0;">
                    {icon_plug()}
                    <span>Plugs</span>
                </h3>

                {plugs_html}
            </div>
        </div>

        <div style="display: flex; justify-content: center; background-color: #e5e7eb; padding: 16px 0;">
            <div style="width: 600px; max-width: 100%; text-align: center; padding: 0 16px;">
                <p style="font-family: Arial, sans-serif; font-size: 12px; color: #6b7280; margin: 0;">
                    Energy Manager - Automated electricity price tracking
                </p>
            </div>
        </div>
    </body>
    </html>
    '''

    return email_html


def render_schedule_execution_email(plug_name: str, event_type: str, from_state: bool,
                                    to_state: bool, timestamp: str, duration_info: str = "") -> str:
    """
    Render the schedule execution notification email.

    Args:
        plug_name: Name of the plug
        event_type: "automatic" or "manual"
        from_state: Previous state (True=ON, False=OFF)
        to_state: New state (True=ON, False=OFF)
        timestamp: Execution timestamp (formatted)
        duration_info: Optional duration text (e.g., "Will turn OFF in 2h")
    """
    state_str = "ON" if to_state else "OFF"

    card_content = f'''
    <div>
        <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px; gap: 8px;">
            {render_type_badge(event_type)}
            <span style="font-size: 16px; color: #374151;">Scheduled action completed at {timestamp}</span>
        </div>

        <div style="display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: #111827; margin: 24px 0; gap: 12px;">
            {icon_plug(32, "#6366f1")}
            <span>{plug_name}</span>
        </div>

        {render_state_transition(from_state, to_state)}
    '''

    if duration_info:
        card_content += f'''
        <div style="background-color: #fef3c7; padding: 16px; border-radius: 8px; margin-top: 24px; border-left: 4px solid #f59e0b;">
            <div style="display: flex; align-items: center; justify-content: center; font-size: 16px; color: #92400e; gap: 8px;">
                {icon_clock(24, "#d97706")}
                <span>{duration_info}</span>
            </div>
        </div>
        '''

    card_content += '</div>'

    email_html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: Arial, sans-serif;">
        {render_header()}

        <div style="display: flex; justify-content: center; background-color: #f3f4f6; padding: 20px 0;">
            <div style="display: flex; flex-direction: column; width: 600px; max-width: 100%; padding: 20px 0;">
                <h2 style="font-family: Arial, sans-serif; font-size: 20px; color: #111827; margin: 0 0 16px 0;">
                    Schedule Executed
                </h2>

                {render_card(card_content, "")}
            </div>
        </div>

        <div style="display: flex; justify-content: center; background-color: #e5e7eb; padding: 16px 0;">
            <div style="width: 600px; max-width: 100%; text-align: center; padding: 0 16px;">
                <p style="font-family: Arial, sans-serif; font-size: 12px; color: #6b7280; margin: 0;">
                    Energy Manager - Automated electricity price tracking
                </p>
            </div>
        </div>
    </body>
    </html>
    '''

    return email_html
