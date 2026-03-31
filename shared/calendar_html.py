"""
GeeLark Calendar HTML Builder
==============================
Generates a standalone HTML calendar from scheduling events.
Extracted from Omni_GeeLarkScheduler for maintainability.
"""

import html
from datetime import datetime, timedelta
from collections import defaultdict, Counter


def generate_account_colors(n: int) -> list[str]:
    """Generate N visually distinct colors using HSL rotation."""
    colors = []
    for i in range(n):
        hue = int(i * 360 / max(n, 1)) % 360
        colors.append(f"hsl({hue}, 72%, 62%)")
    return colors


def build_color_map(accounts: list[str]) -> dict[str, str]:
    """Create a {account_name: color} mapping with dynamic HSL colors."""
    sorted_acc = sorted(accounts)
    colors = generate_account_colors(len(sorted_acc))
    return {acc: colors[i] for i, acc in enumerate(sorted_acc)}


def build_calendar_html(events: list[dict], base_date, days_spread: int) -> str:
    """Build a complete HTML calendar page from event dicts.

    Each event dict: {"date": date, "time": time, "account": str, "caption": str, "color": str}
    """
    # Sort events by datetime
    events_sorted = sorted(events, key=lambda e: datetime.combine(e["date"], e["time"]))

    # Group by date
    by_date = defaultdict(list)
    for ev in events_sorted:
        by_date[ev["date"]].append(ev)

    all_accounts = sorted(set(ev["account"] for ev in events))
    color_map = {ev["account"]: ev["color"] for ev in events}

    total = len(events)
    days_with_posts = len(by_date)
    
    # 🌙 Cosmetic fix: if posts span more calendar days than requested, it's an overnight block
    if days_with_posts > days_spread and days_spread > 0:
        active_label = f"<strong>{days_spread}</strong> nuits actives <span style='font-size:0.85em; opacity:0.75; font-weight:normal;'>({days_with_posts} j. calendaires)</span>"
    else:
        active_label = f"<strong>{days_with_posts}</strong> jours actifs / <strong>{days_spread}</strong>"

    # Legend HTML
    legend_html = "".join(
        f'<span class="legend-item"><span class="legend-dot" style="background:{color_map[acc]}"></span>{html.escape(acc)}</span>'
        for acc in all_accounts
    )

    # Stats per account
    acc_counts = Counter(ev["account"] for ev in events)
    stats_rows = "".join(
        f'<tr><td><span class="dot" style="background:{color_map[acc]}"></span>{html.escape(acc)}</td>'
        f'<td>{cnt}</td><td>{round(cnt/max(1, days_spread), 1) if days_spread > 0 else cnt}/nuit</td></tr>'
        if days_with_posts > days_spread else
        f'<tr><td><span class="dot" style="background:{color_map[acc]}"></span>{html.escape(acc)}</td>'
        f'<td>{cnt}</td><td>{round(cnt/days_with_posts, 1) if days_with_posts else 0}/jour</td></tr>'
        for acc, cnt in sorted(acc_counts.items())
    )

    # Day columns — derive range from actual event dates
    if by_date:
        min_date = min(by_date.keys())
        max_date = max(by_date.keys())
        total_days = (max_date - min_date).days + 1
    else:
        min_date = base_date
        total_days = days_spread

    days_html = ""
    for day_offset in range(total_days):
        d = min_date + timedelta(days=day_offset)
        day_events = by_date.get(d, [])
        day_name = d.strftime("%A")
        date_str = d.strftime("%d %b")

        events_html = ""
        for ev in day_events:
            caption_short = (ev["caption"][:55] + "…") if ev["caption"] and len(ev["caption"]) > 55 else (ev["caption"] or "")
            caption_short = caption_short.replace("\n", " ")
            safe_account = html.escape(ev['account'])
            safe_caption = html.escape(caption_short)
            events_html += f"""
            <div class="event" style="border-left: 3px solid {ev['color']}; background: {ev['color']}18;">
                <div class="event-time">{ev['time'].strftime('%H:%M')}</div>
                <div class="event-account" style="color:{ev['color']}">{safe_account}</div>
                <div class="event-caption">{safe_caption}</div>
            </div>"""

        empty_class = " empty" if not day_events else ""
        count_badge = f'<span class="count-badge">{len(day_events)}</span>' if day_events else ""
        days_html += f"""
        <div class="day{empty_class}">
            <div class="day-header">
                <span class="day-name">{day_name}</span>
                <span class="day-date">{date_str}</span>
                {count_badge}
            </div>
            <div class="day-events">{events_html if events_html else '<span class="no-post">—</span>'}</div>
        </div>"""

    generated_at = datetime.now().strftime("%d/%m/%Y à %H:%M")

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GeeLark Planning</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  *,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #0d0f17;
    --surface: #161925;
    --surface2: #1e2233;
    --border: #2a2f47;
    --text: #e8eaf0;
    --muted: #6b7094;
    --accent: #4f8ef7;
    --radius: 12px;
  }}

  body {{
    font-family: 'Inter', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 24px;
  }}

  .header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
    flex-wrap: wrap;
    gap: 16px;
  }}

  .title {{
    font-size: 22px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .subtitle {{
    color: var(--muted);
    font-size: 13px;
    margin-top: 4px;
    font-weight: 400;
  }}

  .meta {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }}

  .stat-pill {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 13px;
    color: var(--muted);
  }}

  .stat-pill strong {{
    color: var(--text);
  }}

  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 20px;
  }}

  .legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 5px 12px;
  }}

  .legend-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }}

  .stats-table {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 20px;
    margin-bottom: 24px;
  }}

  .stats-table h3 {{
    font-size: 13px;
    font-weight: 600;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .05em;
    margin-bottom: 12px;
  }}

  .stats-table table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}

  .stats-table td {{
    padding: 6px 0;
    color: var(--text);
    border-bottom: 1px solid var(--border);
  }}

  .stats-table tr:last-child td {{
    border-bottom: none;
  }}

  .stats-table td:not(:first-child) {{
    color: var(--muted);
    text-align: right;
  }}

  .dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 7px;
  }}

  .calendar {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 14px;
  }}

  .day {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    transition: border-color .2s;
  }}

  .day:hover {{ border-color: #3a4060; }}

  .day.empty {{
    opacity: .45;
  }}

  .day-header {{
    padding: 10px 14px;
    background: var(--surface2);
    display: flex;
    align-items: center;
    gap: 6px;
    border-bottom: 1px solid var(--border);
  }}

  .day-name {{
    font-size: 12px;
    font-weight: 600;
    text-transform: capitalize;
    color: var(--muted);
  }}

  .day-date {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    margin-left: 2px;
  }}

  .count-badge {{
    margin-left: auto;
    background: var(--accent);
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    border-radius: 999px;
    padding: 1px 7px;
  }}

  .day-events {{
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}

  .event {{
    border-radius: 8px;
    padding: 8px 10px;
  }}

  .event-time {{
    font-size: 11px;
    font-weight: 700;
    color: var(--muted);
    margin-bottom: 2px;
    letter-spacing: .04em;
  }}

  .event-account {{
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 3px;
  }}

  .event-caption {{
    font-size: 11px;
    color: var(--muted);
    line-height: 1.4;
    word-break: break-word;
  }}

  .no-post {{
    color: var(--border);
    font-size: 20px;
    display: block;
    text-align: center;
    padding: 10px 0;
  }}

  .footer {{
    margin-top: 28px;
    text-align: center;
    color: var(--border);
    font-size: 12px;
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="title">GeeLark Planning</div>
    <div class="subtitle">Généré le {generated_at}</div>
  </div>
  <div class="meta">
    <div class="stat-pill"><strong>{total}</strong> publications</div>
    <div class="stat-pill">{active_label}</div>
    <div class="stat-pill"><strong>{len(all_accounts)}</strong> comptes</div>
  </div>
</div>

<div class="legend">{legend_html}</div>

<div class="stats-table">
  <h3>Répartition par compte</h3>
  <table>{stats_rows}</table>
</div>

<div class="calendar">
{days_html}
</div>

<div class="footer">Omni Suite · GeeLark Scheduler V4</div>
</body>
</html>"""
