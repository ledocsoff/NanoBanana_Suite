"""
Omni_StaticCaptioner — Deterministic caption randomizer for Reels & Carousel
==========================================================================
Generates lowercase, generic captions with 0 APIs.
Supports two content types with distinct internal pools:
  - reel: short Gen Z captions
  - carousel: swipe-friendly captions
No API calls — deterministic generation from internal pools.
"""

from __future__ import annotations

import random


class Omni_StaticCaptioner:
    CATEGORY = "Omni/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("captions",)
    FUNCTION = "generate"
    OUTPUT_NODE = False

    DESCRIPTION = (
        "Generates lowercase captions from user defined pools. "
        "Hashtags appended randomly based on probability."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "captions_pool": ("STRING", {
                    "default": "casual.\ncurrent mood\ncatching the vibe?\nrate this 1-10",
                    "multiline": True,
                    "tooltip": "Une caption par ligne."
                }),
                "hashtag_pool": ("STRING", {
                    "default": "fyp, model, reels, explore, viral, explorepage, beauty",
                    "multiline": True,
                    "tooltip": "Hashtags permis, séparés par des virgules ou sauts de ligne."
                }),
                "hashtag_probability": ("FLOAT", {
                    "default": 0.30,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": "Probabilité (0.30 = 30%) d'ajouter 1 ou 2 hashtags."
                }),
            }
        }

    def generate(self, captions_pool: str, hashtag_pool: str, hashtag_probability: float) -> tuple[str]:
        count = 500

        raw_lines = [line.strip() for line in captions_pool.split('\n') if line.strip()]

        if not raw_lines:
            raw_lines = ["mood"]

        print(f"[Omni_StaticCaptioner] Generating {count} captions (pool={len(raw_lines)})...")

        # Parse hashtags (comma or newline separated)
        raw_tags = [tag.strip().strip('#') for tag in hashtag_pool.replace('\n', ',').split(',') if tag.strip()]
        if not raw_tags:
            raw_tags = ["fyp"]

        results = []
        for _ in range(count):
            cap = random.choice(raw_lines)

            if random.random() < hashtag_probability:
                num_tags = random.randint(1, min(2, len(raw_tags)))
                chosen_tags = random.sample(raw_tags, num_tags)
                tags_str = " ".join([f"#{t}" for t in chosen_tags])
                cap = f"{cap}\n\n{tags_str}"

            cap = cap.lower()
            results.append(cap)

        final_string = "\n---\n".join(results)
        print(f"[Omni_StaticCaptioner] ✓ Generated {count} {content_type} captions")
        return (final_string,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
