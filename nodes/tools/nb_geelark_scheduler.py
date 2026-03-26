"""
NB_GeeLarkScheduler V4 — Template-only GeeLark schedule filler
===============================================================
Reads a GeeLark-exported .xlsx template, injects randomized scheduling
dates and captions (from NB_GeminiCaptioner or defaults), and outputs:
  1. A ready-to-reimport .xlsx file
  2. An HTML calendar report (open in browser) for visual planning

Uses direct Paris hours — no timezone conversion needed.
No more "from scratch" mode. This node ONLY modifies existing templates.
"""

import random
import os
import importlib.util
from datetime import datetime, timedelta

# Import shared scheduling constants
_shared_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "shared"
)

_spec = importlib.util.spec_from_file_location("xlsx_utils", os.path.join(_shared_dir, "xlsx_utils.py"))
_xlsx_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_xlsx_utils)

_spec2 = importlib.util.spec_from_file_location("calendar_html", os.path.join(_shared_dir, "calendar_html.py"))
_calendar_html = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_calendar_html)

TIME_BLOCKS = _xlsx_utils.TIME_BLOCKS
TIME_BLOCK_CHOICES = _xlsx_utils.TIME_BLOCK_CHOICES
BLOCK_KEYS = _xlsx_utils.BLOCK_KEYS
merge_time_blocks = _xlsx_utils.merge_time_blocks
merged_duration_minutes = _xlsx_utils.merged_duration_minutes
format_paris_time = _xlsx_utils.format_paris_time
load_template = _xlsx_utils.load_template
build_calendar_html = _calendar_html.build_calendar_html
build_color_map = _calendar_html.build_color_map


class NB_GeeLarkScheduler:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("output_file", "calendar_html",)
    FUNCTION = "schedule"
    OUTPUT_NODE = True

    DESCRIPTION = (
        "Reads a GeeLark template .xlsx, auto-detects the type (Reels/Carousel/Profile), "
        "fills in scheduling dates and captions, and outputs a ready-to-import file "
        "+ an HTML calendar for visual planning."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template_file": ("STRING", {
                    "default": "",
                    "tooltip": "Chemin du fichier .xlsx exporté depuis GeeLark. Le type (Reels/Profile) est auto-détecté."
                }),
                "block_matin": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "☀️ Matin (08h-16h) — Warmup"
                }),
                "block_apresmidi": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "🌆 Après-midi (16h-22h) — Maintenance"
                }),
                "block_soir": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "🌙 Soir (22h-04h) — Prime Time US"
                }),
                "start_days_from_now": ("INT", {
                    "default": 1,
                    "min": 0,
                    "max": 30,
                    "tooltip": "Début dans X jours (0 = aujourd'hui, 1 = demain)"
                }),
            },
            "optional": {
                "captions": ("STRING", {
                    "default": "",
                    "forceInput": True,
                    "tooltip": "Captions (depuis NB_StaticCaptioner ou NB_GeminiCaptioner). Ignoré pour les templates Edit Profile."
                }),
                "days_spread": ("INT", {
                    "default": 7,
                    "min": 1,
                    "max": 60,
                    "tooltip": "Nombre de jours sur lesquels étaler les publications (défaut: 7)"
                }),
                "min_gap_minutes": ("INT", {
                    "default": 30,
                    "min": 10,
                    "max": 180,
                    "tooltip": "Espacement minimum en minutes entre deux publications (défaut: 30)"
                }),
            }
        }

    def _detect_template_type(self, template_file):
        """Auto-detect GeeLark template type from Excel column headers."""
        import openpyxl
        wb = openpyxl.load_workbook(template_file, read_only=True)
        ws = wb.active
        headers = [str(cell.value).lower() if cell.value else "" for cell in next(ws.iter_rows(max_row=1))]
        wb.close()

        # Check col5 header to determine type
        col5 = headers[4] if len(headers) > 4 else ""
        if "nickname" in col5 or "username" in col5:
            return "edit_profile"
        if "video" in col5 or "numberofvideo" in col5.replace(" ", ""):
            return "account_warmup"
        # Default: it's a post template (caption in col5)
        return "post_video/carousel"

    def schedule(self, template_file, block_matin, block_apresmidi, block_soir,
                 start_days_from_now, captions="", days_spread=7, min_gap_minutes=30):
        template_file = template_file.strip().strip("'\"") if template_file else ""

        if not template_file or not os.path.exists(template_file):
            raise Exception(f"Template file introuvable: '{template_file}'. Exporte-le depuis GeeLark (Edit Table → Export).")

        if not template_file.lower().endswith('.xlsx'):
            raise Exception(f"Le fichier template doit être un fichier .xlsx. Chemin fourni: '{template_file}'")

        # Build merged time ranges from active toggles
        active_keys = []
        if block_matin:
            active_keys.append(BLOCK_KEYS["block_matin"])
        if block_apresmidi:
            active_keys.append(BLOCK_KEYS["block_apresmidi"])
        if block_soir:
            active_keys.append(BLOCK_KEYS["block_soir"])

        merged_ranges = merge_time_blocks(active_keys)
        total_minutes = merged_duration_minutes(merged_ranges)

        # Auto-detect template type
        template_type = self._detect_template_type(template_file)
        print(f"[NB_GeeLarkScheduler] 🔍 Type auto-détecté: {template_type}")

        # Auto-generate output filename
        base_name = os.path.splitext(template_file)[0]
        output_file = f"{base_name}_scheduled.xlsx"

        base_date = datetime.now().date() + timedelta(days=start_days_from_now)

        caption_list = self._parse_captions(captions)

        block_labels = [k for k, v in BLOCK_KEYS.items() if v in active_keys]
        print(f"[NB_GeeLarkScheduler] 📅 Blocs actifs: {', '.join(block_labels)} ({total_minutes} min dispo/jour)")

        # Fill template and collect scheduled events for the calendar
        events = self._fill_template(
            template_file, output_file, base_date, days_spread,
            min_gap_minutes, caption_list, template_type, merged_ranges
        )

        # Generate HTML calendar (shared module)
        html_path = output_file.replace(".xlsx", "_calendar.html")
        html_content = build_calendar_html(events, base_date, days_spread)
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

    def _generate_times_for_day(self, count, min_gap_minutes, merged_ranges, target_date, min_datetime=None, global_scheduled_dts=None):
        """Generate random times across multiple time ranges for a given day.

        Args:
            count: number of time slots to generate
            min_gap_minutes: minimum gap between any two slots
            merged_ranges: list of {"start_hour": int, "end_hour": int} dicts
            target_date: the base date for scheduling
            min_datetime: earliest allowed datetime (for same-day safety)
            global_scheduled_dts: absolute datetimes already scheduled across all accounts

        Returns:
            list of (date, time) tuples, sorted chronologically.
        """
        from datetime import time as dtime

        if global_scheduled_dts is None:
            global_scheduled_dts = []

        # Build a flat list of all valid minute offsets across all ranges
        valid_offsets = []  # list of (absolute_minute_from_midnight, target_date_for_that_minute)
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

        if not valid_offsets:
            return []

        results = []
        attempts = 0

        while len(results) < count and attempts < 3000:
            attempts += 1

            total_min, actual_date = random.choice(valid_offsets)
            hour = total_min // 60
            minute = total_min % 60
            candidate_time = dtime(hour=min(hour, 23), minute=minute)
            candidate_dt = datetime.combine(actual_date, candidate_time)

            if min_datetime and candidate_dt < min_datetime:
                continue

            too_close = False
            for ex_dt in global_scheduled_dts + [datetime.combine(r[0], r[1]) for r in results]:
                diff_mins = abs((candidate_dt - ex_dt).total_seconds()) / 60.0
                if diff_mins < min_gap_minutes:
                    too_close = True
                    break
            
            if not too_close:
                results.append((actual_date, candidate_time))

        results.sort()
        return results

    def _fill_template(self, template_file, output_file, base_date, days_spread, min_gap_minutes, caption_list, template_type="post_video/carousel", merged_ranges=None):
        from collections import defaultdict

        if merged_ranges is None:
            merged_ranges = [{"start_hour": 22, "end_hour": 4}]

        wb, data_rows = load_template(template_file)

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
        color_map = build_color_map(all_accounts)

        cap_idx = 0
        events = []  # For HTML calendar
        global_scheduled_dts = []

        for acc, rows in account_rows.items():
            random.shuffle(rows)
            row_idx = 0
            day_offset = 0

            while row_idx < len(rows):
                remaining = len(rows) - row_idx
                remaining_days = days_spread - day_offset
                posts_today = max(1, remaining // remaining_days) if remaining_days > 0 else remaining

                if remaining_days > 1:
                    posts_today = min(remaining, posts_today + random.randint(-1, 1))
                    posts_today = max(1, posts_today)
                else:
                    posts_today = remaining

                min_datetime = None
                now = datetime.now()
                current_date = base_date + timedelta(days=day_offset)
                if current_date == now.date():
                    min_datetime = now + timedelta(minutes=30)

                today_times = self._generate_times_for_day(
                    posts_today,
                    min_gap_minutes,
                    merged_ranges,
                    current_date,
                    min_datetime=min_datetime,
                    global_scheduled_dts=global_scheduled_dts
                )

                for actual_date, pub_time in today_times:
                    if row_idx >= len(rows):
                        break

                    # Write Paris time directly — no conversion needed
                    pub_datetime = datetime.combine(actual_date, pub_time)
                    global_scheduled_dts.append(pub_datetime)
                    
                    row = rows[row_idx]
                    row[3].value = format_paris_time(pub_datetime)

                    caption = ""
                    if template_type == "post_video/carousel":
                        caption = used_captions[cap_idx] if cap_idx < len(used_captions) else ""
                        if caption:
                            row[4].value = caption
                        cap_idx += 1

                    events.append({
                        "date": actual_date,
                        "time": pub_time,
                        "account": acc,
                        "caption": caption,
                        "color": color_map.get(acc, "#888"),
                    })

                    row_idx += 1

                day_offset += 1

            print(f"[NB_GeeLarkScheduler] 📅 {acc}: {row_idx} tâches planifiées sur {day_offset} jours")

        wb.save(output_file)
        print(f"[NB_GeeLarkScheduler] 📄 Fichier sauvegardé: {output_file}")
        return events

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
