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
    RETURN_NAMES = ("output_file", "calendar_html",)
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

    def _is_time_in_ranges(self, dt, merged_ranges):
        """Check if a datetime's hour falls within any of the merged ranges."""
        h = dt.hour
        for rng in merged_ranges:
            s, e = rng["start_hour"], rng["end_hour"]
            if e <= s:  # overnight
                if h >= s or h < e:
                    return True
            else:
                if s <= h < e:
                    return True
        return False

    def _next_block_start(self, dt, merged_ranges):
        """Find the exact next valid block start from the given datetime."""
        candidates = []
        for day_offset in range(0, 3):
            check_date = dt.date() + timedelta(days=day_offset)
            for rng in merged_ranges:
                candidate = datetime.combine(check_date, datetime.min.time()).replace(
                    hour=rng["start_hour"], minute=random.randint(0, 10)
                )
                if candidate > dt:
                    candidates.append(candidate)
                    
        if candidates:
            return min(candidates)

        # Absolute Fallback: next day, first range
        next_day = dt.date() + timedelta(days=1)
        return datetime.combine(next_day, datetime.min.time()).replace(
            hour=merged_ranges[0]["start_hour"], minute=random.randint(0, 10)
        )

    def fill_warmup(self, template_file, start_hour, end_hour,
                    keywords_pool, min_scroll_videos, max_scroll_videos, start_days_from_now):
        wb, rows = load_template(template_file)
        schema = GEELARK_SCHEMAS.get("account_warmup")

        # Single time range — overnight handled natively
        merged_ranges = [{"start_hour": start_hour, "end_hour": end_hour}]
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

        # Tight packing: use minimum delay + small anti-pattern jitter
        omni_accounts = len(rows)
        base_delay = MIN_SEQUENTIAL_DELAY  # 15 min minimum between accounts
        max_jitter = 8  # 0-8 min random bonus to break pattern

        estimated_total = omni_accounts * (base_delay + max_jitter // 2)

        # Build start datetime — start_hour
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
        print(f"[Omni_AccountWarmupFiller] ⏳ {omni_accounts} comptes | Fenêtre: {range_label} ({total_block_dur} min dispo)")
        print(f"[Omni_AccountWarmupFiller] 📐 Packing serré: {base_delay}-{base_delay + max_jitter} min/compte (~{estimated_total} min total estimé)")

        # Collect events for calendar + build color map
        accounts = get_account_names(rows)
        color_map = build_color_map(accounts)
        events = []

        # Shuffler l'ordre des comptes pour casser le pattern séquentiel (anti-fingerprint)
        random.shuffle(rows)
        
        # Burst control variables for organic pacing
        burst_size = random.randint(3, 7)
        current_burst_count = 0

        for i, row in enumerate(rows):
            # If current time is outside all active ranges, jump to next range start
            if not self._is_time_in_ranges(current_dt, merged_ranges):
                current_dt = self._next_block_start(current_dt, merged_ranges)

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
                current_burst_count += 1
                if current_burst_count >= burst_size:
                    # Organic silence gap between bursts
                    delay = random.randint(90, 180)  # 1.5 to 3 hours pause
                    print(f"[Omni_AccountWarmupFiller] 🌊 Fin de vague : Pause organique de {delay} min avant le prochain flot.")
                    burst_size = random.randint(3, 7)
                    current_burst_count = 0
                else:
                    # Tight packing delay within a burst
                    delay = base_delay + random.randint(0, max_jitter)
                
                current_dt += timedelta(minutes=delay)

        output_path = save_template(wb, output_file)

        # Generate HTML calendar
        html_path = output_file.replace(".xlsx", "_calendar.html")
        html_content = build_calendar_html(events, base_date, 1)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Show the actual local times for user reference
        first_local = rows[0][schema["release_time"] - 1].value
        last_local = rows[-1][schema["release_time"] - 1].value
        print(f"[Omni_AccountWarmupFiller] ✅ Fichier prêt: {output_path}")
        print(f"[Omni_AccountWarmupFiller] 📅 Calendrier: {html_path}")
        print(f"[Omni_AccountWarmupFiller] 🕐 {first_local} → {last_local} (heure GeeLark/Paris)")

        return (output_path, html_path)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
