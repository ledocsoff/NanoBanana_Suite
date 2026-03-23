"""
NB_StaticCaptioner — Deterministic, ultra-generic Gen Z caption randomizer
==========================================================================
Generates lowercase, extremely generic captions (e.g. "just me :)") with 0 APIs.
Applies a strict 30% chance to append 1 or 2 random hashtags from a pool.
Guarantees:
- ALL lowercase (forced in Python)
- No AI hallucinations (emojis, over-enthusiasm)
- Blazingly fast (0 API calls)
"""

from __future__ import annotations

import random


class NB_StaticCaptioner:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("captions",)
    FUNCTION = "generate"
    OUTPUT_NODE = False

    DESCRIPTION = (
        "Generates highly generic, lowercase-only captions from a fixed list. "
        "Appends random hashtags from an allowed list exactly 30% of the time. "
        "No AI used, guaranteeing 0 API latency and 0 unrequested emojis."
    )

    @classmethod
    def INPUT_TYPES(cls):
        # A curated list of ultra-generic, non-capitalized Gen Z girl captions
        default_captions = (
            "just me :)\n"
            "anyway...\n"
            "just because\n"
            "too good\n"
            "night out\n"
            "mood\n"
            "vibes\n"
            "not me doing this\n"
            "idk\n"
            "hi\n"
            "late night\n"
            "always\n"
            "nevermind\n"
            "obsessed\n"
            "a moment\n"
            "living\n"
            "tbh\n"
            "felt cute\n"
            "weekend\n"
            "this\n"
            "the usual\n"
            "out and about\n"
            "yep\n"
            ";)\n"
            "<3\n"
            "xoxo\n"
            "for you\n"
            "why not\n"
            "same\n"
            "on repeat"
        )

        return {
            "required": {
                "base_captions": ("STRING", {
                    "default": default_captions,
                    "multiline": True,
                    "tooltip": "Une caption par ligne. Le nœud piochera au hasard."
                }),
                "hashtag_pool": ("STRING", {
                    "default": "fyp, model, reels, explore, viral, explorepage, beauty",
                    "multiline": False,
                    "tooltip": "Hashtags permis, séparés par des virgules."
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

    def generate(self, base_captions: str, hashtag_pool: str, hashtag_probability: float) -> tuple[str]:
        # Generate a massive batch instantly. The Scheduler will only consume what it needs.
        count = 500
        print(f"[NB_StaticCaptioner] Generating a batch of {count} pool captions...")

        # Parse base captions
        raw_lines = [line.strip() for line in base_captions.split('\n') if line.strip()]
        if not raw_lines:
            raw_lines = ["just me :)", "mood"]

        # Parse hashtags
        raw_tags = [tag.strip().strip('#') for tag in hashtag_pool.split(',') if tag.strip()]
        if not raw_tags:
            raw_tags = ["fyp"]

        results = []

        for _ in range(count):
            # Select random base caption
            cap = random.choice(raw_lines)

            # Apply 30% hashtag rule
            if random.random() < hashtag_probability:
                # 1 or 2 tags
                num_tags = random.randint(1, min(2, len(raw_tags)))
                chosen_tags = random.sample(raw_tags, num_tags)
                tags_str = " ".join([f"#{t}" for t in chosen_tags])
                cap = f"{cap}\n\n{tags_str}"

            # FORCE lowercase everywhere (the exact user spec: no caps)
            cap = cap.lower()

            results.append(cap)

        # Output with the '---' separator understood by the scheduler
        final_string = "\n---\n".join(results)
        print(f"[NB_StaticCaptioner] ✓ Generated {count} static captions successfully")
        return (final_string,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always output new ones based on random seeds
        import time
        return time.time()
