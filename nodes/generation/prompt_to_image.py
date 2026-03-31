"""
Omni Custom Nodes for ComfyUI
====================================
Integrates Google AI Studio (Gemini) image generation into ComfyUI workflows.

Nodes:
  - OmniPromptToImage : Generate an image from a text prompt.

Requirements:
  - google-genai  (`pip install google-genai`)
  - shared package (symlinked in custom_nodes/)
"""

from __future__ import annotations

import io
import os
import gc
import time
from typing import Any

import numpy as np
import torch
from PIL import Image
from google import genai
from google.genai import types

# ──────────────────────────────────────────────────────────────────────────────
# Shared imports (shared — mandatory)
# ──────────────────────────────────────────────────────────────────────────────

import sys
_custom_nodes_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _custom_nodes_dir not in sys.path:
    sys.path.insert(0, _custom_nodes_dir)

try:
    from shared.gemini_client import (
        IMAGE_CAPABLE_MODELS,
        ASPECT_RATIOS,
        create_gemini_client,
        call_with_retry,
        extract_image_from_response,
        tensor_to_pil,
        pil_to_tensor,
    )
except ImportError:
    raise ImportError(
        "shared package not found. "
        "Make sure it is symlinked in custom_nodes/."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Node - Prompt to Image
# ──────────────────────────────────────────────────────────────────────────────

class OmniPromptToImage:
    """
    Generate an image using a text prompt via Gemini.
    """

    DESCRIPTION = "Text-to-Image generation via Gemini image API"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gemini_config":      ("GEMINI_CONFIG",),
                "model":              (IMAGE_CAPABLE_MODELS, {"default": "gemini-3-pro-image-preview"}),
                "prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": (
                            "A highly detailed, photorealistic image of..."
                        ),
                    },
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "low quality, bad anatomy, deformed, mutated",
                    },
                ),
                "aspect_ratio":       (ASPECT_RATIOS,),
                "temperature":        ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "resolution":         (["1K", "2K", "4K"], {"default": "1K"}),
                "max_retries":        ("INT",   {"default": 5, "min": 1, "max": 15, "step": 1}),
                "batch_size":         ("INT",   {"default": 1, "min": 1, "max": 4, "step": 1}),
                "delay_between_calls": ("FLOAT", {"default": 3.0, "min": 0.0, "max": 15.0, "step": 0.5}),
            },
            "optional": {
                "images": ("IMAGE",),
                "skip_trigger": ("STRING", {"forceInput": True, "tooltip": "Status message to evaluate."})
            }
        }

    RETURN_TYPES  = ("IMAGE", "STRING")
    RETURN_NAMES  = ("generated_image", "status_message")
    FUNCTION      = "run"
    CATEGORY      = "Omni"
    OUTPUT_NODE   = False

    def run(
        self,
        gemini_config:      dict,
        prompt:             str,
        negative_prompt:    str,
        aspect_ratio:       str,
        temperature:        float,
        model:              str = "gemini-3-pro-image-preview",
        resolution:         str = "1K",
        max_retries:        int = 5,
        batch_size:         int = 1,
        delay_between_calls: float = 3.0,
        images:             Optional[torch.Tensor] = None,
        skip_trigger:       str = "",
    ) -> tuple[torch.Tensor, str]:

        if skip_trigger and skip_trigger.strip().upper().startswith("FAIL"):
            print(f"[OmniPromptToImage] 🛑 Upstream failure detected. Skipping generation and propagating FAIL.")
            # Return current images if they exist, otherwise a blank tensor
            out = images if images is not None else torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (out, skip_trigger)

        print(f"[OmniPromptToImage] Starting text-to-image generation with {model}…")

        # --- Client resolution via GeminiConfig ---
        client = create_gemini_client(gemini_config)

        # Assemble final text prompt
        final_prompt = prompt.strip()
        if negative_prompt.strip():
            final_prompt += f"\n\nNegative instructions (DO NOT INCLUDE): {negative_prompt.strip()}"

        contents = [
            final_prompt,
        ]

        config: dict[str, Any] = {
            "response_modalities": ["IMAGE"],
            "temperature": temperature,
        }

        # Add aspect ratio and image_size
        img_cfg = {"image_size": resolution}
        if aspect_ratio.upper() not in ("AUTO", ""):
            img_cfg["aspect_ratio"] = aspect_ratio
        config["image_config"] = img_cfg

        results = []
        last_status_msg = "Success"
        
        for i in range(batch_size):
            if i > 0 and delay_between_calls > 0:
                print(f"[OmniPromptToImage] Waiting {delay_between_calls}s before next call...")
                time.sleep(delay_between_calls)
            print(f"[OmniPromptToImage] Generating image {i + 1}/{batch_size}...")
            response, status_msg = call_with_retry(client, model, contents, config, max_retries)
            last_status_msg = status_msg

            if response is None:
                print(f"[OmniPromptToImage] ⚠ API Error on image {i + 1}: {status_msg}")
                continue

            result_pil = extract_image_from_response(response)

            if result_pil is None:
                print(f"[OmniPromptToImage] ⚠ No image in response {i + 1}.")
                continue

            print(f"[OmniPromptToImage] ✓ Image {i + 1} Done — output size: {result_pil.size}")
            results.append(pil_to_tensor(result_pil))

            del result_pil
            del response

        # Memory Cleanup
        del contents
        gc.collect()

        if len(results) > 0:
            out_tensor = torch.cat(results, dim=0)
            return (out_tensor, last_status_msg)
        else:
            print("[OmniPromptToImage] ⚠ No valid images generated. Returning blank tensor, emitting FAIL trigger.")
            blank = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            error_msg = f"FAIL: {last_status_msg}"
            return (blank, error_msg)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
