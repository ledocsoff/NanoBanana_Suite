"""
NanoBanana Gemini Config Node
==============================
Centralized provider selection for all NanoBanana generation nodes.

Outputs a GEMINI_CONFIG dict consumed by sibling nodes via their optional input.
"""

from __future__ import annotations

from .gemini_client import IMAGE_CAPABLE_MODELS, PROVIDERS, GCP_LOCATIONS


class NanoBananaGeminiConfig:
    """
    Centralized Gemini provider configuration.

    Connect the GEMINI_CONFIG output to any NanoBanana generation node
    to override its built-in api_key / model fields.
    """

    DESCRIPTION = (
        "Configure the Gemini provider (AI Studio or Vertex AI) "
        "and model for all connected NanoBanana nodes."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDERS, {"default": PROVIDERS[0]}),
                "model": (IMAGE_CAPABLE_MODELS, {"default": IMAGE_CAPABLE_MODELS[-1]}),
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
    CATEGORY = "NanoBanana/Config"
    OUTPUT_NODE = False

    def run(
        self,
        provider: str,
        model: str,
        api_key: str = "",
        gcp_project_id: str = "",
        gcp_location: str = "global",
    ) -> tuple[dict]:

        config = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "gcp_project_id": gcp_project_id,
            "gcp_location": gcp_location,
        }

        print(f"[NanoBananaGeminiConfig] provider={provider}, model={model}")
        return (config,)
