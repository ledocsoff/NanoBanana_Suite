"""
Omni Gemini Config Node
==============================
Centralized provider selection for all Omni generation nodes.

Outputs a GEMINI_CONFIG dict consumed by sibling nodes via their optional input.
"""

from __future__ import annotations

from .gemini_client import PROVIDERS, GCP_LOCATIONS


class OmniGeminiConfig:
    """
    Centralized Gemini provider configuration (authentication only).

    Connect the GEMINI_CONFIG output to any Omni generation node
    to provide API credentials. Each node selects its own model.
    """

    DESCRIPTION = (
        "Configure the Gemini provider (AI Studio or Vertex AI) "
        "and credentials for all connected Omni nodes."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDERS, {"default": PROVIDERS[0]}),
            },
            "optional": {
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "AIza… (AI Studio only)",
                    },
                ),
                "gcp_project_id": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "my-gcp-project-123 (Vertex AI only)",
                    },
                ),
                "gcp_location": (GCP_LOCATIONS, {"default": GCP_LOCATIONS[0]}),
            },
        }

    RETURN_TYPES = ("GEMINI_CONFIG",)
    RETURN_NAMES = ("gemini_config",)
    FUNCTION = "run"
    CATEGORY = "Omni/Config"
    OUTPUT_NODE = False

    def run(
        self,
        provider: str,
        api_key: str = "",
        gcp_project_id: str = "",
        gcp_location: str = "global",
        **kwargs
    ) -> tuple[dict]:

        config = {
            "provider": provider,
            "api_key": api_key,
            "gcp_project_id": gcp_project_id,
            "gcp_location": gcp_location,
        }

        print(f"[OmniGeminiConfig] provider={provider}")
        return (config,)
