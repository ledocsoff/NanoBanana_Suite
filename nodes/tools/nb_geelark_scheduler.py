"""
NB_GeeLarkScheduler V3 — Template-only GeeLark schedule filler
===============================================================
Reads a GeeLark-exported .xlsx template, injects randomized scheduling
dates and captions (from NB_GeminiCaptioner or defaults), and outputs:
  1. A ready-to-reimport .xlsx file
  2. An HTML calendar report (open in browser) for visual planning

No more "from scratch" mode. This node ONLY modifies existing templates.
"""

import random
import os
from datetime import datetime, timedelta


ACCOUNT_COLORS = [
    "#4f8ef7", "#f7774f", "#4ff7a0", "#f7d44f",
    "#c44ff7", "#f74fb1", "#4ff7e8", "#f74f4f",
    "#7af74f", "#f79b4f",
]


class NB_GeeLarkScheduler:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("output_file", "calendar_html",)
    FUNCTION = "schedule"
    OUTPUT_NODE = True

    DESCRIPTION = (
        "Reads a GeeLark template .xlsx, fills in scheduling dates and captions, "
        "and outputs a ready-to-import file + an HTML calendar for visual planning. "
        "Connect captions from NB_GeminiCaptioner."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template_file": ("STRING", {
                    "default": "",
                    "tooltip": "Chemin du fichier .xlsx exporté depuis GeeLark (Edit Table → Export)"
                }),
                "output_file": ("STRING", {
                    "default": "./geelark_filled.xlsx",
                    "tooltip": "Chemin du fichier Excel de sortie"
                }),
                "start_days_from_now": ("INT", {
                    "default": 1,
                    "min": 0,
                    "max": 30,
                    "tooltip": "Début dans X jours (0 = aujourd'hui, 1 = demain)"
                }),
                "days_spread": ("INT", {
                    "default": 7,
                    "min": 1,
                    "max": 60,
                    "tooltip": "Nombre de jours sur lesquels étaler les publications"
                }),
                "min_gap_minutes": ("INT", {
                    "default": 30,
                    "min": 10,
                    "max": 180,
                    "tooltip": "Espacement minimum en minutes entre deux publications"
                }),
            },
            "optional": {
                "captions": ("STRING", {
                    "default": "",
                    "forceInput": True,
                    "tooltip": "Captions générées par NB_GeminiCaptioner. Si vide, des emojis par défaut sont utilisés."
                }),
            }
        }

    def schedule(self, template_file, output_file, start_days_from_now, days_spread, min_gap_minutes, captions=""):
        template_file = template_file.strip().strip("'\"") if template_file else ""
        output_file = output_file.strip().strip("'\"") if output_file else ""

        if not template_file or not os.path.exists(template_file):
            raise Exception(f"Template file introuvable: '{template_file}'. Exporte-le depuis GeeLark (Edit Table → Export).")

        if not template_file.lower().endswith('.xlsx'):
            raise Exception(f"Le fichier template doit être un fichier .xlsx. Chemin fourni: '{template_file}'")

        if not output_file.lower().endswith('.xlsx'):
            output_file += '.xlsx'

        base_date = datetime.now().date() + timedelta(days=start_days_from_now)

        caption_list = self._parse_captions(captions)

        # Fill template and collect scheduled events for the calendar
        events = self._fill_template(template_file, output_file, base_date, days_spread, min_gap_minutes, caption_list)

        # Generate HTML calendar
        html_path = output_file.replace(".xlsx", "_calendar.html")
        html_content = self._build_calendar_html(events, base_date, days_spread)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[NB_GeeLarkScheduler] ✅ Fichier prêt: {output_file}")
        print(f"[NB_GeeLarkScheduler] 📅 Calendrier: {html_path}")
        return (output_file, html_path)

    # ─────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────

    def _parse_captions(self, captions_text):
        if not captions_text or not captions_text.strip():
            return []
        parts = [c.strip() for c in captions_text.split("---") if c.strip()]
        if parts:
            return parts
        return [c.strip() for c in captions_text.split("\n") if c.strip()]

    def _get_default_captions(self, count):
        base = [
            "✨", "💫", "🔥", "Mood", "Vibes only", "That energy",
            "Living the moment", "Just me", "Feeling it", "No caption needed",
            "Main character energy", "Unapologetic", "Different breed",
            "In my element", "Plot twist", "Stay golden", "Unbothered",
            "Level up", "This is it", "Verified vibes",
        ]
        default_tags = ["#lifestyle", "#vibes", "#aesthetic", "#mood", "#style", "#beauty", "#fashion", "#confidence"]
        return [
            f"{random.choice(base)}\n\n{' '.join(random.sample(default_tags, random.randint(3, 6)))}"
            for _ in range(count)
        ]

    def _generate_times_for_day(self, count, min_gap_minutes, min_time=None, existing_times=None):
        from datetime import time as dtime
        
        if existing_times is None:
            existing_times = []

        time_windows = [
            (7, 10, 25),
            (11, 14, 20),
            (16, 18, 15),
            (19, 23, 35),
            (23, 1,   5),
        ]
        total_weight = sum(w[2] for w in time_windows)
        times = []
        attempts = 0

        while len(times) < count and attempts < 1000:
            attempts += 1
            r = random.uniform(0, total_weight)
            cumulative = 0
            chosen = time_windows[0]
            for window in time_windows:
                cumulative += window[2]
                if r <= cumulative:
                    chosen = window
                    break

            start_h, end_h, _ = chosen
            if end_h <= start_h:
                hour = random.choice([start_h, 0])
                minute = random.randint(0, 59)
            else:
                total_min = (end_h - start_h) * 60
                rand_min = random.randint(0, total_min)
                hour = start_h + rand_min // 60
                minute = rand_min % 60

            candidate = dtime(hour=min(hour, 23), minute=minute)
            
            # Prevent scheduling in the past on the current day
            if min_time and candidate < min_time:
                safe_hour = random.randint(min_time.hour, 23)
                safe_min = random.randint(0, 59) if safe_hour > min_time.hour else random.randint(min_time.minute, 59)
                candidate = dtime(hour=min(safe_hour, 23), minute=min(safe_min, 59))

            all_times = times + existing_times
            too_close = any(
                abs((candidate.hour * 60 + candidate.minute) - (ex.hour * 60 + ex.minute)) < min_gap_minutes
                for ex in all_times
            )
            if not too_close:
                times.append(candidate)

        times.sort()
        return times

    def _fill_template(self, template_file, output_file, base_date, days_spread, min_gap_minutes, caption_list):
        import openpyxl
        from collections import defaultdict

        wb = openpyxl.load_workbook(template_file)
        ws = wb.active

        data_rows = list(ws.iter_rows(min_row=2))
        if not data_rows:
            print("[NB_GeeLarkScheduler] ⚠ Template vide, rien à remplir.")
            wb.save(output_file)
            return []

        total_tasks = len(data_rows)

        if caption_list:
            used_captions = list(caption_list)
            while len(used_captions) < total_tasks:
                used_captions.extend(caption_list)
            random.shuffle(used_captions)
            used_captions = used_captions[:total_tasks]
        else:
            used_captions = self._get_default_captions(total_tasks)

        account_rows = defaultdict(list)
        for row in data_rows:
            acc = str(row[1].value) if row[1].value else "unknown"
            account_rows[acc].append(row)

        all_accounts = sorted(account_rows.keys())
        color_map = {acc: ACCOUNT_COLORS[i % len(ACCOUNT_COLORS)] for i, acc in enumerate(all_accounts)}

        cap_idx = 0
        events = []  # For HTML calendar: list of {date, time, account, caption, color}
        global_times_by_day = defaultdict(list)

        for acc, rows in account_rows.items():
            random.shuffle(rows)
            row_idx = 0
            day_offset = 0

            while row_idx < len(rows):
                current_date = base_date + timedelta(days=day_offset)
                remaining = len(rows) - row_idx
                remaining_days = days_spread - day_offset
                posts_today = max(1, remaining // remaining_days) if remaining_days > 0 else remaining

                if remaining_days > 1:
                    posts_today = min(remaining, posts_today + random.randint(-1, 1))
                    posts_today = max(1, posts_today)
                else:
                    posts_today = remaining  # Last day: publish everything left

                min_time_arg = None
                if current_date == datetime.now().date():
                    # Add 30 minutes safety margin
                    safe_now = datetime.now() + timedelta(minutes=30)
                    min_time_arg = safe_now.time()

                today_times = self._generate_times_for_day(
                    posts_today, 
                    min_gap_minutes, 
                    min_time=min_time_arg,
                    existing_times=global_times_by_day[current_date]
                )
                
                global_times_by_day[current_date].extend(today_times)

                for pub_time in today_times:
                    if row_idx >= len(rows):
                        break

                    pub_datetime = datetime.combine(current_date, pub_time)
                    row = rows[row_idx]
                    row[3].value = pub_datetime.strftime("%Y-%m-%d %H:%M")

                    caption = used_captions[cap_idx] if cap_idx < len(used_captions) else ""
                    if caption:
                        row[4].value = caption

                    events.append({
                        "date": current_date,
                        "time": pub_time,
                        "account": acc,
                        "caption": caption,
                        "color": color_map.get(acc, "#888"),
                    })

                    cap_idx += 1
                    row_idx += 1
                    
                day_offset += 1

            print(f"[NB_GeeLarkScheduler] 📅 {acc}: {row_idx} tâches planifiées sur {day_offset} jours")

        wb.save(output_file)
        print(f"[NB_GeeLarkScheduler] 📄 Fichier sauvegardé: {output_file}")
        return events

    # ─────────────────────────────────────────────────────────────────
    # HTML Calendar Builder
    # ─────────────────────────────────────────────────────────────────

    def _build_calendar_html(self, events, base_date, days_spread):
        from collections import defaultdict

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

        # Legend HTML
        legend_html = "".join(
            f'<span class="legend-item"><span class="legend-dot" style="background:{color_map[acc]}"></span>{acc}</span>'
            for acc in all_accounts
        )

        # Stats per account
        from collections import Counter
        acc_counts = Counter(ev["account"] for ev in events)
        stats_rows = "".join(
            f'<tr><td><span class="dot" style="background:{color_map[acc]}"></span>{acc}</td>'
            f'<td>{cnt}</td><td>{round(cnt/days_with_posts, 1) if days_with_posts else 0}/jour</td></tr>'
            for acc, cnt in sorted(acc_counts.items())
        )

        # Day columns
        days_html = ""
        for day_offset in range(days_spread):
            d = base_date + timedelta(days=day_offset)
            day_events = by_date.get(d, [])
            day_name = d.strftime("%A")
            date_str = d.strftime("%d %b")

            events_html = ""
            for ev in day_events:
                caption_short = (ev["caption"][:55] + "…") if ev["caption"] and len(ev["caption"]) > 55 else (ev["caption"] or "")
                caption_short = caption_short.replace("\n", " ")
                events_html += f"""
                <div class="event" style="border-left: 3px solid {ev['color']}; background: {ev['color']}18;">
                    <div class="event-time">{ev['time'].strftime('%H:%M')}</div>
                    <div class="event-account" style="color:{ev['color']}">{ev['account']}</div>
                    <div class="event-caption">{caption_short}</div>
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
<title>🍌 GeeLark Planning</title>
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
    <div class="title">🍌 GeeLark Planning</div>
    <div class="subtitle">Généré le {generated_at}</div>
  </div>
  <div class="meta">
    <div class="stat-pill"><strong>{total}</strong> publications</div>
    <div class="stat-pill"><strong>{days_with_posts}</strong> jours actifs / <strong>{days_spread}</strong></div>
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

<div class="footer">NanaBanana Suite · GeeLark Scheduler V3</div>
</body>
</html>"""

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
