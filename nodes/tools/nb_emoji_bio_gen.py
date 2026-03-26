"""
NB_EmojiBioGen — Aesthetic Unicode bio generator for Instagram profiles
========================================================================
Generates random bios using aesthetic Unicode symbols (Egyptian hieroglyphs,
Tibetan marks, kaomoji, combining characters) organized by "vibe".
Supports a fixed line (e.g. "19 · nyc · ♡") injected into every bio.
No API calls — uses a local JSON fragment dictionary.
"""

from __future__ import annotations

import json
import os
import random


_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "emoji_fragments.json")
_fragments_cache = None

INSTAGRAM_BIO_LIMIT = 150


def _load_fragments() -> dict:
    global _fragments_cache
    if _fragments_cache is None:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            _fragments_cache = json.load(f)
    return _fragments_cache


class NB_EmojiBioGen:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("bios",)
    FUNCTION = "generate"
    OUTPUT_NODE = False

    DESCRIPTION = (
        "Generates aesthetic Unicode bios (⋆.ೃ࿔, 𓆉, ꒰꒱ style) from a built-in "
        "fragment dictionary. Supports a fixed line injected into every bio. "
        "No API calls."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Désactivé = retourne vide, le Profile Filler ignore la bio."
                }),
                "style": (["aesthetic_pure", "aesthetic_with_emoji", "kaomoji"], {
                    "default": "aesthetic_with_emoji",
                    "tooltip": "aesthetic_pure = symboles seuls. aesthetic_with_emoji = mix. kaomoji = visages texte."
                }),
                "vibe": (["cute", "ethereal", "ocean", "celestial", "floral", "dark", "soft", "mixed"], {
                    "default": "cute",
                    "tooltip": "Ambiance des symboles utilisés."
                }),
                "bio_length": (["short", "medium", "full"], {
                    "default": "short",
                    "tooltip": "short = 1 ligne deco. medium = deco + fixed. full = deco multi-ligne + fixed."
                }),
            },
            "optional": {
                "fixed_line": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Texte fixe injecté dans chaque bio. Ex: '19 · nyc · ♡'"
                }),
                "fixed_position": (["end", "start"], {
                    "default": "end",
                    "tooltip": "Position du texte fixe dans la bio."
                }),
            }
        }

    def generate(self, enabled: bool, style: str, vibe: str, bio_length: str,
                 fixed_line: str = "", fixed_position: str = "end") -> tuple[str]:

        if not enabled:
            print("[NB_EmojiBioGen] ⏸ Désactivé — sortie vide, bios non modifiées.")
            return ("",)

        count = 200  # Auto: assez pour couvrir n'importe quel template
        fragments = _load_fragments()
        results = set()  # Use set to guarantee uniqueness

        max_attempts = count * 3  # Guard against infinite loop if pool is small
        attempts = 0
        while len(results) < count and attempts < max_attempts:
            bio = self._build_single_bio(fragments, style, vibe, bio_length)

            # Inject fixed line
            if fixed_line and fixed_line.strip():
                if fixed_position == "start":
                    bio = f"{fixed_line.strip()}\n{bio}"
                else:
                    bio = f"{bio}\n{fixed_line.strip()}"

            # Enforce Instagram 150 char limit
            if len(bio) > INSTAGRAM_BIO_LIMIT:
                bio = bio[:INSTAGRAM_BIO_LIMIT].rstrip()

            results.add(bio)
            attempts += 1

        final = "\n---\n".join(results)
        print(f"[NB_EmojiBioGen] ✓ Generated {len(results)} unique bios (vibe={vibe}, style={style})")
        return (final,)

    def _build_single_bio(self, fragments: dict, style: str, vibe: str, bio_length: str) -> str:
        """Assemble one bio from fragments."""

        # Select vibe data
        if vibe == "mixed":
            available_vibes = [k for k in fragments if not k.startswith("_")]
            chosen_vibe = random.choice(available_vibes)
        else:
            chosen_vibe = vibe

        vibe_data = fragments.get(chosen_vibe, fragments.get("cute"))
        standalone = fragments.get("_standalone_bios", [])

        # Decide source elements based on style
        pool = list(vibe_data.get("symbols", []))
        if style in ("aesthetic_with_emoji",):
            pool.extend(vibe_data.get("decorative", []))
        if style == "kaomoji":
            pool = list(vibe_data.get("kaomoji", []))
            if not pool:
                pool = list(vibe_data.get("symbols", []))

        templates = vibe_data.get("templates", [])
        kaomoji_list = vibe_data.get("kaomoji", [])

        if bio_length == "short":
            return self._build_short(pool, templates, kaomoji_list, standalone, style)
        elif bio_length == "medium":
            return self._build_medium(pool, templates, kaomoji_list, standalone, style)
        else:
            return self._build_full(pool, templates, kaomoji_list, standalone, style)

    def _build_short(self, pool, templates, kaomoji_list, standalone, style) -> str:
        """Single decorative line."""
        strategy = random.choice(["template", "standalone", "raw_combo"])

        if strategy == "standalone" and standalone:
            return random.choice(standalone)

        if strategy == "template" and templates:
            return self._fill_template(random.choice(templates), pool, kaomoji_list)

        # raw_combo: 2-5 random symbols
        count = random.randint(2, 5)
        chosen = random.sample(pool, min(count, len(pool)))
        sep = random.choice([" ", "", "⋆", "˚", " · "])
        return sep.join(chosen)

    def _build_medium(self, pool, templates, kaomoji_list, standalone, style) -> str:
        """Two lines: one decorative + one variation."""
        line1 = self._build_short(pool, templates, kaomoji_list, standalone, style)
        # Second line: different strategy
        strategy = random.choice(["kaomoji", "symbols", "template"])
        if strategy == "kaomoji" and kaomoji_list:
            line2 = random.choice(kaomoji_list)
        elif strategy == "template" and templates:
            line2 = self._fill_template(random.choice(templates), pool, kaomoji_list)
        else:
            count = random.randint(2, 4)
            chosen = random.sample(pool, min(count, len(pool)))
            line2 = " ".join(chosen)

        # Prevent identical lines
        if line1 == line2:
            line2 = random.choice(pool) if pool else "♡"

        return f"{line1}\n{line2}"

    def _build_full(self, pool, templates, kaomoji_list, standalone, style) -> str:
        """Three lines: decorative sandwich."""
        line1 = self._build_short(pool, templates, kaomoji_list, standalone, style)
        line2 = self._build_short(pool, templates, kaomoji_list, standalone, style)
        line3 = self._build_short(pool, templates, kaomoji_list, standalone, style)

        # Ensure all 3 are different
        seen = {line1}
        while line2 in seen:
            line2 = self._build_short(pool, templates, kaomoji_list, standalone, style)
        seen.add(line2)
        while line3 in seen:
            line3 = self._build_short(pool, templates, kaomoji_list, standalone, style)

        return f"{line1}\n{line2}\n{line3}"

    def _fill_template(self, template: str, pool: list, kaomoji_list: list) -> str:
        """Replace {a}, {b}, {c}, {e}, {center}, {kaomoji} placeholders in a template."""
        result = template

        # General symbol placeholders
        for placeholder in ["{a}", "{b}", "{c}", "{d}", "{e}"]:
            if placeholder in result:
                result = result.replace(placeholder, random.choice(pool) if pool else "♡", 1)

        # Center = symbol or kaomoji
        if "{center}" in result:
            if kaomoji_list and random.random() < 0.5:
                result = result.replace("{center}", random.choice(kaomoji_list), 1)
            else:
                result = result.replace("{center}", random.choice(pool) if pool else "♡", 1)

        # Kaomoji
        if "{kaomoji}" in result:
            if kaomoji_list:
                result = result.replace("{kaomoji}", random.choice(kaomoji_list), 1)
            else:
                result = result.replace("{kaomoji}", random.choice(pool) if pool else "♡", 1)

        return result

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
