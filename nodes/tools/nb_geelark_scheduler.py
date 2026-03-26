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
                "time_block": (TIME_BLOCK_CHOICES, {
                    "default": TIME_BLOCK_CHOICES[2],
                    "tooltip": "Plage horaire Paris dans laquelle répartir les tâches."
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

    def schedule(self, template_file, time_block, start_days_from_now,
                 captions="", days_spread=7, min_gap_minutes=30):
        template_file = template_file.strip().strip("'\"") if template_file else ""

        if not template_file or not os.path.exists(template_file):
            raise Exception(f"Template file introuvable: '{template_file}'. Exporte-le depuis GeeLark (Edit Table → Export).")

        if not template_file.lower().endswith('.xlsx'):
            raise Exception(f"Le fichier template doit être un fichier .xlsx. Chemin fourni: '{template_file}'")

        # Auto-detect template type
        template_type = self._detect_template_type(template_file)
        print(f"[NB_GeeLarkScheduler] 🔍 Type auto-détecté: {template_type}")

        # Auto-generate output filename
        base_name = os.path.splitext(template_file)[0]
        output_file = f"{base_name}_scheduled.xlsx"

        base_date = datetime.now().date() + timedelta(days=start_days_from_now)

        caption_list = self._parse_captions(captions)

        print(f"[NB_GeeLarkScheduler] 📅 Bloc: {time_block} (heure Paris directe)")

        # Fill template and collect scheduled events for the calendar
        events = self._fill_template(template_file, output_file, base_date, days_spread, min_gap_minutes, caption_list, template_type, time_block)

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

    def _generate_times_for_day(self, count, min_gap_minutes, block_start_h, block_end_h, target_date, min_time=None, existing_times=None):
        """Generate random times within a block. Handles overnight blocks (e.g. 22h→04h).
        Returns list of (date, time) tuples since overnight blocks span 2 calendar days."""
        from datetime import time as dtime

        if existing_times is None:
            existing_times = []

        is_overnight = block_end_h <= block_start_h

        # Block duration in minutes
        if is_overnight:
            block_duration = (24 - block_start_h + block_end_h) * 60
        else:
            block_duration = (block_end_h - block_start_h) * 60

        results = []
        attempts = 0

        while len(results) < count and attempts < 2000:
            attempts += 1

            rand_offset = random.randint(0, max(block_duration - 1, 0))
            total_minutes = block_start_h * 60 + rand_offset

            # Handle overflow past midnight for overnight blocks
            if total_minutes >= 24 * 60:
                actual_date = target_date + timedelta(days=1)
                total_minutes -= 24 * 60
            else:
                actual_date = target_date

            hour = total_minutes // 60
            minute = total_minutes % 60
            candidate_time = dtime(hour=min(hour, 23), minute=minute)

            if min_time and actual_date == datetime.now().date() and candidate_time < min_time:
                continue

            candidate_min = candidate_time.hour * 60 + candidate_time.minute
            all_times = [(t[1] if isinstance(t, tuple) else t) for t in results + existing_times]
            too_close = any(
                abs(candidate_min - (ex.hour * 60 + ex.minute)) < min_gap_minutes
                for ex in all_times
            )
            if not too_close:
                results.append((actual_date, candidate_time))

        results.sort()
        return results

    def _fill_template(self, template_file, output_file, base_date, days_spread, min_gap_minutes, caption_list, template_type="post_video/carousel", time_block="🌙 Soir (22h-04h) — Prime Time US"):
        from collections import defaultdict

        # Get block boundaries (Paris hours)
        block = TIME_BLOCKS.get(time_block, {"start_hour": 22, "end_hour": 4})
        block_start_h = block["start_hour"]
        block_end_h = block["end_hour"]

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
        global_times_by_day = defaultdict(list)

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

                min_time_arg = None
                now = datetime.now()
                current_date = base_date + timedelta(days=day_offset)
                if current_date == now.date():
                    safe_now = now + timedelta(minutes=30)
                    min_time_arg = safe_now.time()

                today_times = self._generate_times_for_day(
                    posts_today,
                    min_gap_minutes,
                    block_start_h,
                    block_end_h,
                    current_date,
                    min_time=min_time_arg,
                    existing_times=global_times_by_day.get(current_date, [])
                )

                for actual_date, _ in today_times:
                    global_times_by_day[actual_date].append(_)

                for actual_date, pub_time in today_times:
                    if row_idx >= len(rows):
                        break

                    # Write Paris time directly — no conversion needed
                    pub_datetime = datetime.combine(actual_date, pub_time)
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
