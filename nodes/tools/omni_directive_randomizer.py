import random
import time


_DEFAULT_POOL = """Angle: Guys think wrestlers don't have curves under the singlet. Closer: let me know if you still think the same.
Angle: Guys tell her she's too pretty to hold anyone down on the mat. Closer: come to my next practice and tell me if I'm wrong.
Angle: Every guy she dates gets nervous when she mentions she knows how to choke. Closer: I'm just saying, don't knock it till you've tried it.
Angle: Her last date went silent when she told him what she does to guys on the mat. Closer: so I'm wondering if anyone out there would give me a chance.
Angle: She lives for the moment a guy looks up at her and realizes he can't move. Closer: let me know if you still think the same.
Angle: Guys always brag they can last five minutes with her but never make it past two. Closer: come to my next practice and tell me if I'm wrong.
Angle: Her training partner forgot what move he was doing when she wrapped her legs around him. Closer: I'm just saying, don't knock it till you've tried it.
Angle: A new guy at the gym said she couldn't submit him and thirty seconds later he was tapping her thigh. Closer: so I'm wondering if anyone out there would give me a chance.
Angle: She never expected to learn what sounds guys make when they can't breathe under her. Closer: let me know if you still think the same.
Angle: Guys think a wrestler can't be soft and strong at the same time. Closer: come to my next practice and tell me if I'm wrong.
Angle: Her coach told her to go easy on the new guys but she can't help it. Closer: I'm just saying, don't knock it till you've tried it.
Angle: Every guy she trains with says he won't tap out and every single one does. Closer: let me know if you still think the same."""


class Omni_DirectiveRandomizer:
    """Picks a random directive from a user-editable pool at each execution.
    Connect the 'directive' output to the ScriptGenerator's 'directive_override' input."""

    CATEGORY = "Omni"
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("directive", "pool_size")
    FUNCTION = "execute"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directives_pool": ("STRING", {
                    "default": _DEFAULT_POOL.strip(),
                    "multiline": True,
                    "tooltip": "One directive per line. A random line is picked each execution."
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xFFFFFFFF,
                    "tooltip": "Randomize to change the pick each execution.",
                }),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def execute(self, directives_pool, seed):
        lines = [line.strip() for line in directives_pool.split("\n") if line.strip()]

        if not lines:
            fallback = "Generate a spoken script following the system prompt structure."
            print(f"[Omni_DirectiveRandomizer] ⚠️ Pool empty, using fallback.")
            return (fallback, 0)

        pool_size = len(lines)
        index = seed % pool_size
        directive = lines[index]

        print(f"[Omni_DirectiveRandomizer] 🎲 Picked directive {index + 1}/{pool_size}: {directive[:80]}...")

        return (directive, pool_size)


NODE_CLASS_MAPPINGS = {"Omni_DirectiveRandomizer": Omni_DirectiveRandomizer}
NODE_DISPLAY_NAME_MAPPINGS = {"Omni_DirectiveRandomizer": "🎯 Directive Randomizer"}
