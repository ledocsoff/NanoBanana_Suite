"""
NB_StaticCaptioner — Deterministic caption randomizer for Reels & Carousel
==========================================================================
Generates lowercase, generic captions with 0 APIs.
Supports two content types with distinct internal pools:
  - reel: short Gen Z captions
  - carousel: swipe-friendly captions
No API calls — deterministic generation from internal pools.
"""

from __future__ import annotations

import random


# Internal caption pools
_REEL_CAPTIONS = [
    "and now?", "at least i tried", "be honest", "can you explain?",
    "casual.", "catching the vibe?", "couldn't resist", "current mood",
    "did what had to be done", "didn't even try", "do you like it?", "don't ask.",
    "effortless", "feeling myself today", "good mood today", "how was that?",
    "i like this trend", "i tried ok", "i want this..", "i'm in shock..",
    "i'm lucky?", "i'm your type?", "in my element", "just for fun",
    "living for this", "looking at what?", "making it look easy", "not your average",
    "obsessed.", "oh?", "ok?", "oops.", "rate this 1-10", "simple girl",
    "wait for it..", "what am i doing", "what's going on?", "why not.", "why not?"
]

_CAROUSEL_CAPTIONS = [
    "photo dump", "core memory unlocked", "dump", "lately",
    "a series of events", "in order", "swipe for a surprise",
    "life lately", "random but here", "highlights", "some moments",
    "mini dump", "kept these for you", "weekend dump", "camera roll cleanup",
    "small things", "snap snap", "some favorites", "life in frames",
    "memories i'm keeping", "had to share", "unfiltered", "a few things",
    "slide through", "in no particular order", "all the vibes",
    "take your pick", "some stuff", "brain dump", "just a few",
]


class NB_StaticCaptioner:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("captions",)
    FUNCTION = "generate"
    OUTPUT_NODE = False

    DESCRIPTION = (
        "Generates lowercase captions from internal reel/carousel pools. "
        "Hashtags appended randomly based on probability."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "content_type": (["reel", "carousel"], {
                    "default": "reel",
                    "tooltip": "reel = captions courtes Gen Z. carousel = captions 'photo dump' pour swipe."
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

    def generate(self, content_type: str, hashtag_pool: str, hashtag_probability: float) -> tuple[str]:
        count = 500

        raw_lines = list(_REEL_CAPTIONS if content_type == "reel" else _CAROUSEL_CAPTIONS)

        if not raw_lines:
            raw_lines = ["mood"]

        print(f"[NB_StaticCaptioner] Generating {count} captions (source={content_type}, pool={len(raw_lines)})...")

        # Parse hashtags
        raw_tags = [tag.strip().strip('#') for tag in hashtag_pool.split(',') if tag.strip()]
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
        print(f"[NB_StaticCaptioner] ✓ Generated {count} {content_type} captions")
        return (final_string,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
