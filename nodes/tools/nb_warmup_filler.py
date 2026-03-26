"""
NB_AccountWarmupFiller — GeeLark "Instagram AI account warmup" filler
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
TIME_BLOCKS = _xlsx_utils.TIME_BLOCKS
TIME_BLOCK_CHOICES = _xlsx_utils.TIME_BLOCK_CHOICES
BLOCK_KEYS = _xlsx_utils.BLOCK_KEYS
merge_time_blocks = _xlsx_utils.merge_time_blocks
merged_duration_minutes = _xlsx_utils.merged_duration_minutes
format_paris_time = _xlsx_utils.format_paris_time
MIN_SEQUENTIAL_DELAY = _xlsx_utils.MIN_SEQUENTIAL_DELAY
block_duration_minutes = _xlsx_utils.block_duration_minutes
load_template = _xlsx_utils.load_template
save_template = _xlsx_utils.save_template


class NB_AccountWarmupFiller:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_file",)
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
                "block_matin": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "☀️ Matin (04h-16h) — Warmup"
                }),
                "block_apresmidi": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "🌆 Après-midi (16h-22h) — Maintenance"
                }),
                "block_soir": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "🌙 Soir (22h-04h) — Prime Time US"
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

    def fill_warmup(self, template_file, block_matin, block_apresmidi, block_soir,
                    keywords_pool, min_scroll_videos, max_scroll_videos, start_days_from_now):
        wb, rows = load_template(template_file)
        schema = GEELARK_SCHEMAS.get("account_warmup")

        # Build merged time ranges from active toggles
        active_keys = []
        if block_matin:
            active_keys.append(BLOCK_KEYS["block_matin"])
        if block_apresmidi:
            active_keys.append(BLOCK_KEYS["block_apresmidi"])
        if block_soir:
            active_keys.append(BLOCK_KEYS["block_soir"])

        merged_ranges = merge_time_blocks(active_keys)
        total_block_dur = merged_duration_minutes(merged_ranges)

        # Auto-generate output filename
        base_name = os.path.splitext(template_file.strip().strip("'\""))[0]
        output_file = f"{base_name}_scheduled.xlsx"

        if not schema:
            raise Exception("[NB_AccountWarmupFiller] Erreur: schéma 'account_warmup' introuvable dans xlsx_utils.py")

        if not rows:
            print("[NB_AccountWarmupFiller] ⚠ Fichier vide.")
            out_path = save_template(wb, output_file)
            return (out_path,)

        if min_scroll_videos > max_scroll_videos:
            min_scroll_videos, max_scroll_videos = max_scroll_videos, min_scroll_videos

        keywords_list = [k.strip() for k in keywords_pool.split('\n') if k.strip()]
        if not keywords_list:
            keywords_list = ["aesthetic"]

        # Calculate optimal delay: spread accounts evenly across the total block duration
        nb_accounts = len(rows)
        ideal_delay = total_block_dur / max(nb_accounts, 1)

        # Apply guard-rail: never go below MIN_SEQUENTIAL_DELAY
        if ideal_delay < MIN_SEQUENTIAL_DELAY:
            print(f"🍌 [NB_AccountWarmupFiller] ⚠️ {nb_accounts} comptes dans {total_block_dur} min = "
                  f"{ideal_delay:.0f} min/compte. Minimum appliqué: {MIN_SEQUENTIAL_DELAY} min.")
            print(f"🍌 [NB_AccountWarmupFiller] ⚠️ Les tâches vont déborder sur les jours suivants.")
            ideal_delay = MIN_SEQUENTIAL_DELAY

        # Variation range: ±15% of ideal delay, clamped to ±5 min max, guaranteed at least 1 min
        variation = min(max(1, int(ideal_delay * 0.15)), 5)

        # Build start datetime — first merged range start hour
        base_date = datetime.now().date() + timedelta(days=start_days_from_now)
        current_dt = datetime.combine(base_date, datetime.min.time()).replace(
            hour=merged_ranges[0]["start_hour"], minute=random.randint(0, 10)
        )

        # Protection: Prevent scheduling in the past if running for "today"
        safe_now = datetime.now() + timedelta(minutes=15)
        if current_dt < safe_now:
            current_dt = safe_now

        block_labels = [k for k, v in BLOCK_KEYS.items() if v in active_keys]
        print(f"🍌 [NB_AccountWarmupFiller] ⏳ {nb_accounts} comptes | Blocs: {', '.join(block_labels)} ({total_block_dur} min)")
        print(f"🍌 [NB_AccountWarmupFiller] 📐 Délai calculé: ~{ideal_delay:.0f} min/compte (±{variation} min)")

        for i, row in enumerate(rows):
            # If current time is outside all active ranges, jump to next range start
            if not self._is_time_in_ranges(current_dt, merged_ranges):
                current_dt = self._next_block_start(current_dt, merged_ranges)

            # 1. Write Release Time (Paris time, direct)
            row[schema["release_time"] - 1].value = format_paris_time(current_dt)

            # 2. Write random Video Scroll Count
            row[schema["number_of_videos"] - 1].value = random.randint(min_scroll_videos, max_scroll_videos)

            # 3. Write random Search Keyword
            row[schema["search_keyword"] - 1].value = random.choice(keywords_list)

            # Advance time for the NEXT account
            if i < len(rows) - 1:
                delay = int(ideal_delay) + random.randint(-variation, variation)
                delay = max(delay, MIN_SEQUENTIAL_DELAY)
                current_dt += timedelta(minutes=delay)

        output_path = save_template(wb, output_file)

        # Show the actual local times for user reference
        first_local = rows[0][schema["release_time"] - 1].value
        last_local = rows[-1][schema["release_time"] - 1].value
        print(f"🍌 [NB_AccountWarmupFiller] ✅ Fichier prêt: {output_path}")
        print(f"🍌 [NB_AccountWarmupFiller] 🕐 {first_local} → {last_local} (heure GeeLark/Paris)")

        return (output_path,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
