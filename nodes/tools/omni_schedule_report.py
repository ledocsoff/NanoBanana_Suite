import os
import json
import html as html_module
import time
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter


class Omni_ScheduleReport:
    """Generate a professional HTML dashboard from GeeLark scheduling events."""

    CATEGORY = "Omni/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("report_path",)
    FUNCTION = "generate_report"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "events_json": ("STRING", {
                    "forceInput": True,
                    "tooltip": "JSON des évènements provenant de l'Omni_GeeLarkScheduler",
                }),
                "save_directory": ("STRING", {
                    "default": "/Users/quentin/Desktop/Omni_Reports",
                    "tooltip": "Chemin du dossier où le rapport HTML sera sauvegardé",
                }),
            }
        }

    def generate_report(self, events_json: str, save_directory: str):
        if not events_json or not events_json.strip():
            raise RuntimeError("[Omni_ScheduleReport] Le events_json fourni est vide.")

        try:
            data = json.loads(events_json)
            # Support for both old list format and new dict format with metadata
            if isinstance(data, dict) and "events" in data:
                events_raw = data["events"]
                metadata = data.get("metadata", {})
            else:
                events_raw = data
                metadata = {}
        except json.JSONDecodeError as e:
            raise RuntimeError(f"[Omni_ScheduleReport] JSON invalide : {e}")

        if not isinstance(events_raw, list):
            raise RuntimeError("[Omni_ScheduleReport] Le JSON doit être une liste d'événements (ou un objet contenant 'events').")

        # Parse dates/times back from serialized strings
        events = []
        for ev in events_raw:
            d = date.fromisoformat(ev["date"])
            parts = ev["time"].split(":")
            t = datetime.strptime(ev["time"], "%H:%M").time()
            events.append({
                "date": d,
                "time": t,
                "account": ev.get("account", ""),
                "caption": ev.get("caption", ""),
                "color": ev.get("color", "#888"),
            })

        events.sort(key=lambda e: datetime.combine(e["date"], e["time"]))

        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%Hh%Mm%S")
        file_name = f"schedule_{timestamp_str}.html"

        os.makedirs(save_directory, exist_ok=True)
        file_path = os.path.join(save_directory, file_name)

        html_content = self._build_html(events, now, metadata)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[Omni_ScheduleReport] ✅ Rapport généré : {file_path}")
        return (file_path,)

    # ------------------------------------------------------------------

    def _build_html(self, events: list, gen_date: datetime, metadata: dict) -> str:
        date_str = gen_date.strftime("%d/%m/%Y à %H:%M:%S")
        total = len(events)
        
        # --- Task Type Styling ---
        task_type = metadata.get("template_type", "post_video/carousel")
        type_labels = {
            "account_warmup": "🔥 Warm-up / Maintenance",
            "edit_profile": "👤 Edition de Profil",
            "post_video/carousel": "🎬 Reels & Carrousels",
            "full_automation": "🤖 Automation Complète"
        }
        type_colors = {
            "account_warmup": "#fbbf24", # Orange/Yellow
            "edit_profile": "#c084fc",   # Purple
            "post_video/carousel": "#5e6ad2" # Omni Blue
        }
        type_label = type_labels.get(task_type, task_type.upper())
        type_color = type_colors.get(task_type, "#5e6ad2")
        # -------------------------

        all_accounts = sorted(set(ev["account"] for ev in events))
        color_map = {ev["account"]: ev["color"] for ev in events}
        acc_counts = Counter(ev["account"] for ev in events)

        by_date = defaultdict(list)
        for ev in events:
            by_date[ev["date"]].append(ev)
        days_active = len(by_date)

        if by_date:
            min_date = min(by_date.keys())
            max_date = max(by_date.keys())
            total_calendar_days = (max_date - min_date).days + 1
        else:
            min_date = gen_date.date()
            total_calendar_days = 0

        # ── Calendar grid ──
        calendar_html = ""
        for day_offset in range(total_calendar_days):
            d = min_date + timedelta(days=day_offset)
            day_events = by_date.get(d, [])
            day_name = d.strftime("%A")
            date_label = d.strftime("%d %b")
            empty_cls = " empty" if not day_events else ""
            badge = f'<span class="count-badge">{len(day_events)}</span>' if day_events else ""

            events_cards = ""
            for ev in day_events:
                safe_acc = html_module.escape(ev["account"])
                cap = ev["caption"][:55] + "…" if len(ev["caption"]) > 55 else ev["caption"]
                cap = cap.replace("\n", " ")
                safe_cap = html_module.escape(cap)
                events_cards += f"""
                <div class="cal-event" style="border-left:3px solid {ev['color']}; background:{ev['color']}15;">
                    <div class="cal-time">{ev['time'].strftime('%H:%M')}</div>
                    <div class="cal-acc" style="color:{ev['color']}">{safe_acc}</div>
                    <div class="cal-cap">{safe_cap}</div>
                </div>"""

            no_post = '<span class="no-post">—</span>' if not events_cards else ""
            calendar_html += f"""
            <div class="cal-day{empty_cls}">
                <div class="cal-day-header">
                    <span class="cal-day-name">{day_name}</span>
                    <span class="cal-day-date">{date_label}</span>
                    {badge}
                </div>
                <div class="cal-day-body">{events_cards}{no_post}</div>
            </div>"""

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Omni Schedule Report</title>
<style>
:root {{
    --bg: #0b0d10;
    --surface: #14171e;
    --surface-alt: #191d27;
    --border: #252a35;
    --text: #e8eaed;
    --text-dim: #8b919a;
    --accent: #5e6ad2;
    --accent-glow: rgba(94,106,210,0.15);
    --green: #34d399;
}}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.5;
}}
.wrap {{ max-width:1440px; margin:0 auto; padding:32px 24px; }}

/* ── Header ── */
header {{ text-align:center; margin-bottom:32px; }}
h1 {{
    font-size:2rem; font-weight:800; letter-spacing:-0.5px;
    background: linear-gradient(135deg, #fff 0%, #888 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.meta {{ color:var(--text-dim); margin-top:6px; font-size:0.9rem; }}

/* ── KPIs ── */
.kpis {{
    display:grid; grid-template-columns:repeat(3,1fr); gap:16px;
    margin-bottom:24px;
}}
.kpi {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:12px; padding:20px; text-align:center;
}}
.kpi .num {{ font-size:1.75rem; font-weight:800; color:#fff; }}
.kpi .lbl {{ font-size:0.75rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:1px; margin-top:4px; }}

/* ── Calendar View ── */
.cal-grid {{
    display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr));
    gap:14px;
}}
.cal-day {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:12px; overflow:hidden; transition:border-color 0.2s;
}}
.cal-day:hover {{ border-color:#3a4060; }}
.cal-day.empty {{ opacity:0.4; }}
.cal-day-header {{
    padding:10px 14px; background:var(--surface-alt);
    display:flex; align-items:center; gap:6px;
    border-bottom:1px solid var(--border);
}}
.cal-day-name {{ font-size:0.75rem; font-weight:600; text-transform:capitalize; color:var(--text-dim); }}
.cal-day-date {{ font-size:0.85rem; font-weight:600; color:var(--text); margin-left:2px; }}
.count-badge {{
    margin-left:auto; background:var(--accent); color:#fff;
    font-size:0.7rem; font-weight:700; border-radius:999px; padding:1px 7px;
}}
.cal-day-body {{ padding:10px; display:flex; flex-direction:column; gap:8px; }}
.cal-event {{ border-radius:8px; padding:8px 10px; }}
.cal-time {{ font-size:0.7rem; font-weight:700; color:var(--text-dim); margin-bottom:2px; letter-spacing:0.04em; }}
.cal-acc {{ font-size:0.8rem; font-weight:600; margin-bottom:3px; }}
.cal-cap {{ font-size:0.7rem; color:var(--text-dim); line-height:1.4; word-break:break-word; }}
.no-post {{ color:var(--border); font-size:20px; display:block; text-align:center; padding:10px 0; }}

.footer {{
    margin-top:28px; text-align:center;
    color:rgba(255,255,255,0.15); font-size:0.75rem;
}}

@media (max-width:768px) {{
    .kpis {{ grid-template-columns:1fr; }}
    .wrap {{ padding:16px 12px; }}
}}
</style>
</head>
<body>
<div class="wrap">
    <header>
        <div style="display:inline-block; padding:4px 12px; border-radius:999px; background: {type_color}20; color:{type_color}; border:1px solid {type_color}40; font-size:10px; font-weight:700; text-transform:uppercase; margin-bottom:12px; letter-spacing:1px;">
            {type_label}
        </div>
        <h1>Omni Schedule Report</h1>
        <div class="meta">Généré le {date_str} • {total} publications planifiées</div>
    </header>

    <div class="kpis">
        <div class="kpi"><div class="num">{total}</div><div class="lbl">Publications</div></div>
        <div class="kpi"><div class="num">{len(all_accounts)}</div><div class="lbl">Comptes Actifs</div></div>
        <div class="kpi"><div class="num">{days_active}</div><div class="lbl">Jours Actifs</div></div>
    </div>

    <div class="calendar-container">
        <div class="cal-grid">
            {calendar_html}
        </div>
    </div>

    <div class="footer">Omni Suite · Schedule Report</div>
</div>

</body>
</html>"""

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()


NODE_CLASS_MAPPINGS = {
    "Omni_ScheduleReport": Omni_ScheduleReport,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Omni_ScheduleReport": "Schedule HTML Report",
}
