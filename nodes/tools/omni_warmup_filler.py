"""
Omni_AccountWarmupFiller — GeeLark "Instagram AI account warmup" filler
======================================================================
Fills the warmup template with sequential timing, random scroll counts
and random search keywords. Supports Time Block presets with direct
Paris hours for GeeLark execution.
"""

import os
import random
import importlib.util
from datetime import datetime, timedelta

# Import utils directly to avoid pulling in heavier modules
_xlsx_utils_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "shared", "xlsx_utils.py"
)
_spec = importlib.util.spec_from_file_location("xlsx_utils", _xlsx_utils_path)
_xlsx_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_xlsx_utils)

GEELARK_SCHEMAS = _xlsx_utils.GEELARK_SCHEMAS
range_duration_minutes = _xlsx_utils.range_duration_minutes
validate_schedule_capacity = _xlsx_utils.validate_schedule_capacity
format_paris_time = _xlsx_utils.format_paris_time
MIN_SEQUENTIAL_DELAY = _xlsx_utils.MIN_SEQUENTIAL_DELAY
load_template = _xlsx_utils.load_template
save_template = _xlsx_utils.save_template
get_account_names = _xlsx_utils.get_account_names

# Import calendar_html for visual planning output
_calendar_html_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "shared", "calendar_html.py"
)
_spec2 = importlib.util.spec_from_file_location("calendar_html", _calendar_html_path)
_calendar_html = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_calendar_html)
build_calendar_html = _calendar_html.build_calendar_html
build_color_map = _calendar_html.build_color_map


class Omni_AccountWarmupFiller:
    CATEGORY = "Omni/Tools"
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("output_file", "events_json",)
    FUNCTION = "fill_warmup"
    OUTPUT_NODE = True

    DESCRIPTION = (
        "Fills the GeeLark 'Instagram AI account warmup' template. "
        "Distributes tasks sequentially within a Time Block (Paris hours), with "
        "random scroll counts and search keywords."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template_file": ("STRING", {
                    "default": "",
                    "tooltip": "Fichier modèle exporté de GeeLark (Instagram AI account warmup)"
                }),
                "start_hour": ("INT", {
                    "default": 8, "min": 0, "max": 23, "step": 1,
                    "tooltip": "Heure de début (Paris). Ex: 8 = 08h00"
                }),
                "end_hour": ("INT", {
                    "default": 20, "min": 0, "max": 23, "step": 1,
                    "tooltip": "Heure de fin (Paris). Ex: 20 = 20h00. Si < début → overnight"
                }),
                "keywords_pool": ("STRING", {
                    "default": "egirl makeup\ngym girl routine\ngrwm routine\nsoft girl aesthetic\noutfit check\nstorytime makeup\nnight routine skincare\nshein haul aesthetic\nzara haul",
                    "multiline": True,
                    "tooltip": "Pool de mots-clés de recherche (un par ligne)."
                }),
                "min_scroll_videos": ("INT", {
                    "default": 7,
                    "min": 1,
                    "max": 50,
                    "tooltip": "Nombre minimum de vidéos à scroller."
                }),
                "max_scroll_videos": ("INT", {
                    "default": 10,
                    "min": 1,
                    "max": 100,
                    "tooltip": "Nombre maximum de vidéos à scroller."
                }),
                "start_days_from_now": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 30,
                    "tooltip": "Début dans X jours (0 = aujourd'hui)"
                }),
            }
        }

    def fill_warmup(self, template_file, start_hour, end_hour,
                    keywords_pool, min_scroll_videos, max_scroll_videos, start_days_from_now):
        wb, rows = load_template(template_file)
        schema = GEELARK_SCHEMAS.get("account_warmup")

        total_block_dur = range_duration_minutes(start_hour, end_hour)

        # Auto-generate output filename
        base_name = os.path.splitext(template_file.strip().strip("'\""))[0]
        output_file = f"{base_name}_scheduled.xlsx"

        if not schema:
            raise Exception("[Omni_AccountWarmupFiller] Erreur: schéma 'account_warmup' introuvable dans xlsx_utils.py")

        if not rows:
            print("[Omni_AccountWarmupFiller] ⚠ Fichier vide.")
            out_path = save_template(wb, output_file)
            return (out_path, "")

        if min_scroll_videos > max_scroll_videos:
            min_scroll_videos, max_scroll_videos = max_scroll_videos, min_scroll_videos

        keywords_list = [k.strip() for k in keywords_pool.split('\n') if k.strip()]
        if not keywords_list:
            keywords_list = ["aesthetic"]

        omni_accounts = len(rows)
        base_delay = MIN_SEQUENTIAL_DELAY  # 15 min minimum between accounts

        # Build start datetime
        base_date = datetime.now().date() + timedelta(days=start_days_from_now)
        current_dt = datetime.combine(base_date, datetime.min.time()).replace(
            hour=start_hour, minute=random.randint(0, 10)
        )

        # Protection: Prevent scheduling in the past if running for "today"
        safe_now = datetime.now() + timedelta(minutes=15)
        if current_dt < safe_now:
            current_dt = safe_now

        is_overnight = end_hour < start_hour or start_hour == end_hour
        range_label = f"{start_hour}h→{end_hour}h" + (" (overnight)" if is_overnight else "")

        # Calculate available minutes from current_dt to block end
        if is_overnight:
            block_end_dt = datetime.combine(
                current_dt.date() + timedelta(days=1),
                datetime.min.time()
            ).replace(hour=end_hour)
        else:
            block_end_dt = datetime.combine(
                current_dt.date(),
                datetime.min.time()
            ).replace(hour=end_hour)
        available_minutes = (block_end_dt - current_dt).total_seconds() / 60

        # Decide pacing strategy based on available space
        intervals = max(omni_accounts - 1, 1)
        ideal_spacing = available_minutes / intervals

        if ideal_spacing >= 60 and omni_accounts >= 6:
            # Plenty of room → use burst waves with organic pauses
            mode = "burst"
            burst_size = random.randint(3, min(5, omni_accounts - 1))
            # Reserve pause time: ~30% of total for burst gaps
            num_pauses = max(1, (omni_accounts - 1) // burst_size)
            pause_budget = available_minutes * 0.30
            per_pause = pause_budget / num_pauses
            active_budget = available_minutes - pause_budget
            active_intervals = intervals - num_pauses
            if active_intervals > 0:
                active_spacing = active_budget / active_intervals
            else:
                active_spacing = base_delay
            print(f"[Omni_AccountWarmupFiller] ⏳ {omni_accounts} comptes | Fenêtre: {range_label} ({int(available_minutes)} min dispo)")
            print(f"[Omni_AccountWarmupFiller] 🌊 Mode vagues: ~{burst_size} comptes/vague, pause ~{int(per_pause)} min entre vagues")
        else:
            # Tight window → distribute evenly with jitter
            mode = "even"
            even_spacing = max(base_delay, available_minutes / intervals)
            # Jitter = ±25% of spacing, capped to keep within window
            max_jitter = min(8, int(even_spacing * 0.25))
            print(f"[Omni_AccountWarmupFiller] ⏳ {omni_accounts} comptes | Fenêtre: {range_label} ({int(available_minutes)} min dispo)")
            print(f"[Omni_AccountWarmupFiller] 📐 Distribution uniforme: ~{int(even_spacing)} min/compte (±{max_jitter} min jitter)")

        # Collect events for calendar + build color map
        accounts = get_account_names(rows)
        color_map = build_color_map(accounts)
        events = []

        # Shuffle account order for anti-fingerprint
        random.shuffle(rows)

        current_burst_count = 0

        for i, row in enumerate(rows):
            # 1. Write Release Time (Paris time, direct)
            row[schema["release_time"] - 1].value = format_paris_time(current_dt)

            # 2. Write random Video Scroll Count
            row[schema["number_of_videos"] - 1].value = random.randint(min_scroll_videos, max_scroll_videos)

            # 3. Write random Search Keyword
            keyword = random.choice(keywords_list)
            row[schema["search_keyword"] - 1].value = keyword

            # Collect event for HTML calendar
            acc_name = str(row[1].value) if row[1].value else f"account_{i}"
            events.append({
                "date": current_dt.date(),
                "time": current_dt.time(),
                "account": acc_name,
                "caption": f"scroll {row[schema['number_of_videos'] - 1].value} vidéos | {keyword}",
                "color": color_map.get(acc_name, "#888"),
            })

            # Advance time for the NEXT account
            if i < len(rows) - 1:
                if mode == "burst":
                    current_burst_count += 1
                    if current_burst_count >= burst_size:
                        delay = per_pause + random.randint(-5, 5)
                        print(f"[Omni_AccountWarmupFiller] 🌊 Fin de vague : pause de {int(delay)} min")
                        burst_size = random.randint(3, min(5, len(rows) - 1 - i))
                        current_burst_count = 0
                    else:
                        delay = active_spacing + random.randint(-3, 3)
                else:
                    delay = even_spacing + random.randint(-max_jitter, max_jitter)

                # Hard floor: never less than base_delay
                delay = max(base_delay, delay)

                # Hard ceiling: never go past block end
                remaining = (block_end_dt - current_dt).total_seconds() / 60
                remaining_accounts = len(rows) - 1 - i
                max_allowed = remaining - (remaining_accounts - 1) * base_delay
                delay = min(delay, max(base_delay, max_allowed))

                current_dt += timedelta(minutes=int(delay))

        output_path = save_template(wb, output_file)

        # Serialize events to JSON for the dedicated report node
        events_serializable = []
        for ev in events:
            events_serializable.append({
                "date": ev["date"].isoformat(),
                "time": ev["time"].strftime("%H:%M"),
                "account": ev["account"],
                "caption": ev.get("caption", ""),
                "color": ev.get("color", "#888"),
            })
        
        import json
        output_data = {
            "metadata": {
                "template_type": "account_warmup",
                "generated_at": datetime.now().isoformat()
            },
            "events": events_serializable
        }
        events_json = json.dumps(output_data, ensure_ascii=False, indent=2)

        # Show the actual local times for user reference
        first_local = rows[0][schema["release_time"] - 1].value
        last_local = rows[-1][schema["release_time"] - 1].value
        print(f"[Omni_AccountWarmupFiller] ✅ Fichier prêt: {output_path}")
        print(f"[Omni_AccountWarmupFiller] 📊 {len(events)} événements prêts pour le rapport HTML.")
        print(f"[Omni_AccountWarmupFiller] 🕐 {first_local} → {last_local} (heure GeeLark/Paris)")

        return (output_path, events_json)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
