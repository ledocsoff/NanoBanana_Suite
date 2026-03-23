"""
shared — Shared utilities & config node for the NanoBanana Suite.
"""

from .gemini_config import NanoBananaGeminiConfig

NODE_CLASS_MAPPINGS = {
    "NanoBananaGeminiConfig": NanoBananaGeminiConfig,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "NanoBananaGeminiConfig": "NanoBanana Gemini Config 🍌⚙️",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
