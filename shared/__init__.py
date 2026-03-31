"""
shared — Shared utilities & config node for the Omni Suite.
"""

from .gemini_config import OmniGeminiConfig

NODE_CLASS_MAPPINGS = {
    "OmniGeminiConfig": OmniGeminiConfig,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OmniGeminiConfig": "Omni Gemini Config ⚙️",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
