"""
Omni_AccountWarmupFiller — GeeLark "Instagram AI account warmup" filler
======================================================================
Fills the warmup template with advanced multidimensional parallel scheduling,
random scroll counts and random search keywords.
"""

import os
import random
import importlib.util
from datetime import datetime, timedelta

# Import utils directly to avoid pulling in heavier modules
_shared_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "shared"
)

_spec = importlib.util.spec_from_file_location("xlsx_utils", os.path.join(_shared_dir, "xlsx_utils.py"))
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
_spec2 = importlib.util.spec_from_file_location("calendar_html", os.path.join(_shared_dir, "calendar_html.py"))
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
        "Fills the GeeLark 'Instagram AI account warmup' template using the advanced "
        "multidimensional scheduling engine (days_spread, max_simultaneous)."
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
            },
            "optional": {
                "days_spread": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 60,
                    "tooltip": "Nombre de jours sur lesquels étaler la session de chauffe (défaut: 1)"
                }),
                "min_gap_minutes": ("INT", {
                    "default": 15,
                    "min": 1,
                    "max": 120,
                    "tooltip": "Écart minimal en minutes entre deux actions ou groupes d'actions."
                }),
                "max_simultaneous": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 10,
                    "tooltip": "Jusqu'à N profils autorisés à scroller en même temps (dans une même plage de min_gap_minutes)."
                }),
            }
        }

    def _generate_times_for_day(self, count, min_gap_minutes, max_simultaneous, merged_ranges, target_date, min_datetime=None, global_scheduled_dts=None):
        from datetime import time as dtime

        if global_scheduled_dts is None:
            global_scheduled_dts = []

        valid_offsets = []
        for rng in merged_ranges:
            block_start_h = rng["start_hour"]
            block_end_h = rng["end_hour"]
            is_overnight = block_end_h <= block_start_h

            if is_overnight:
                block_duration = (24 - block_start_h + block_end_h) * 60
            else:
                block_duration = (block_end_h - block_start_h) * 60

            for offset in range(block_duration):
                total_min = block_start_h * 60 + offset
                if total_min >= 24 * 60:
                    actual_date = target_date + timedelta(days=1)
                    total_min -= 24 * 60
                else:
                    actual_date = target_date
                valid_offsets.append((total_min, actual_date))

        if min_datetime:
            filtered = []
            for tm, ad in valid_offsets:
                c_time = dtime(hour=min(tm // 60, 23), minute=tm % 60)
                if datetime.combine(ad, c_time) >= min_datetime:
                    filtered.append((tm, ad))
            valid_offsets = filtered

        if not valid_offsets:
            return []

        results = []
        current_max_simultaneous = 1
        all_existing = global_scheduled_dts.copy()

        if count > 0 and len(valid_offsets) >= count:
            segment_size = len(valid_offsets) // count
            jitter_range = max(1, int(segment_size * 0.3))

            for i in range(count):
                segment_center = i * segment_size + segment_size // 2
                seg_start = max(i * segment_size, segment_center - jitter_range)
                seg_end = min((i + 1) * segment_size - 1, segment_center + jitter_range)
                seg_end = max(seg_start, seg_end)

                chosen_idx = random.randint(seg_start, seg_end)
                chosen_idx = min(chosen_idx, len(valid_offsets) - 1)

                total_min, actual_date = valid_offsets[chosen_idx]
                candidate_time = dtime(hour=min(total_min // 60, 23), minute=total_min % 60)
                candidate_dt = datetime.combine(actual_date, candidate_time)

                close_count = sum(
                    1 for ex_dt in all_existing
                    if abs((candidate_dt - ex_dt).total_seconds()) / 60.0 < min_gap_minutes
                )

                if close_count < current_max_simultaneous:
                    results.append((actual_date, candidate_time))
                    all_existing.append(candidate_dt)

        attempts = 0
        current_max_simultaneous = 1

        while len(results) < count:
            attempts += 1
            
            if attempts > 500:
                current_max_simultaneous = min(2, max_simultaneous)
            if attempts > 1500:
                current_max_simultaneous = max_simultaneous

            if attempts > 3000:
                best_candidate = None
                best_dt = None
                min_collisions = 999999
                
                for _ in range(50):
                    t_min, a_date = random.choice(valid_offsets)
                    c_time = dtime(hour=min(t_min // 60, 23), minute=t_min % 60)
                    c_dt = datetime.combine(a_date, c_time)
                    
                    collisions = sum(
                        1 for ex_dt in all_existing
                        if abs((c_dt - ex_dt).total_seconds()) / 60.0 < min_gap_minutes
                    )
                    
                    if collisions < min_collisions:
                        min_collisions = collisions
                        best_candidate = (a_date, c_time)
                        best_dt = c_dt
                
                if best_candidate and min_collisions < max_simultaneous:
                    results.append(best_candidate)
                    all_existing.append(best_dt)
                    attempts = 0
                else:
                    break
                continue

            total_min, actual_date = random.choice(valid_offsets)
            candidate_time = dtime(hour=min(total_min // 60, 23), minute=total_min % 60)
            candidate_dt = datetime.combine(actual_date, candidate_time)

            close_count = sum(
                1 for ex_dt in all_existing
                if abs((candidate_dt - ex_dt).total_seconds()) / 60.0 < min_gap_minutes
            )
            
            if close_count < current_max_simultaneous:
                results.append((actual_date, candidate_time))
                all_existing.append(candidate_dt)
                attempts = 0

        results.sort()
        return results

    def fill_warmup(self, template_file, start_hour, end_hour,
                    keywords_pool, min_scroll_videos, max_scroll_videos, start_days_from_now,
                    days_spread=1, min_gap_minutes=15, max_simultaneous=1):
        from collections import defaultdict

        wb, rows = load_template(template_file)
        schema = GEELARK_SCHEMAS.get("account_warmup")

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

        merged_ranges = [{"start_hour": start_hour, "end_hour": end_hour}]
        total_tasks = len(rows)

        print(f"[Omni_AccountWarmupFiller] ⏳ {total_tasks} tâches de chauffe détectées.")
        print(f"[Omni_AccountWarmupFiller] 🌊 Mode Moteur 2D : {days_spread} jours | {max_simultaneous} simultanés")

        validation = validate_schedule_capacity(
            total_tasks, start_hour, end_hour,
            min_gap_minutes, days_spread, max_simultaneous
        )
        for w in validation["warnings"]:
            print(f"[Omni_AccountWarmupFiller] {w}")
        days_spread = validation["adjusted_days_spread"]

        base_date = datetime.now().date() + timedelta(days=start_days_from_now)
        is_overnight = end_hour < start_hour or start_hour == end_hour

        if start_days_from_now == 0 and is_overnight and datetime.now().hour < end_hour:
            base_date -= timedelta(days=1)
            print("[Omni_AccountWarmupFiller] 🌙 Détection post-minuit : alignement sur la nuit en cours.")

        account_rows = defaultdict(list)
        for row in rows:
            acc = str(row[1].value) if row[1].value else "unknown"
            account_rows[acc].append(row)

        all_accounts = sorted(account_rows.keys())
        color_map = build_color_map(all_accounts)

        # Distribute accounts over days_spread
        acc_day_starts = {}
        shuffled_accs = list(all_accounts)
        random.shuffle(shuffled_accs)
        
        # Warmup is 1 row per account usually, spread accounts across days evenly
        for i, a in enumerate(shuffled_accs):
            acc_day_starts[a] = (i * days_spread) // len(shuffled_accs)

        events = []
        global_scheduled_dts = []

        shuffled_accounts = list(account_rows.items())
        random.shuffle(shuffled_accounts)

        for acc, acc_rows in shuffled_accounts:
            row_idx = 0
            day_offset = acc_day_starts.get(acc, 0)

            while row_idx < len(acc_rows):
                remaining = len(acc_rows) - row_idx
                remaining_days = days_spread - day_offset
                
                if remaining_days <= 1:
                    posts_today = remaining
                else:
                    posts_today = max(1, remaining // remaining_days)
                    posts_today += random.randint(-1, 1)
                    posts_today = max(1, min(remaining, posts_today))

                min_datetime = None
                now = datetime.now()
                current_date = base_date + timedelta(days=day_offset)
                
                # Protect past scheduling
                if current_date <= now.date():
                    min_datetime = now + timedelta(minutes=15)

                today_times = self._generate_times_for_day(
                    posts_today,
                    min_gap_minutes,
                    max_simultaneous,
                    merged_ranges,
                    current_date,
                    min_datetime=min_datetime,
                    global_scheduled_dts=global_scheduled_dts
                )

                for actual_date, pub_time in today_times:
                    if row_idx >= len(acc_rows):
                        break

                    pub_datetime = datetime.combine(actual_date, pub_time)
                    global_scheduled_dts.append(pub_datetime)
                    
                    row = acc_rows[row_idx]
                    
                    # Apply specific Warmup node formulas
                    row[schema["release_time"] - 1].value = format_paris_time(pub_datetime)
                    row[schema["number_of_videos"] - 1].value = random.randint(min_scroll_videos, max_scroll_videos)
                    keyword = random.choice(keywords_list)
                    row[schema["search_keyword"] - 1].value = keyword

                    events.append({
                        "date": actual_date,
                        "time": pub_time,
                        "account": acc,
                        "caption": f"scroll {row[schema['number_of_videos'] - 1].value} vidéos | {keyword}",
                        "color": color_map.get(acc, "#888"),
                    })

                    row_idx += 1

                day_offset += 1

        output_path = save_template(wb, output_file)

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

        print(f"[Omni_AccountWarmupFiller] ✅ Fichier prêt: {output_path}")
        print(f"[Omni_AccountWarmupFiller] 📊 {len(events)} événements prêts pour le rapport HTML.")

        return (output_path, events_json)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
