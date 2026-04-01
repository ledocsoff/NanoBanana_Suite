from __future__ import annotations

import io
import os
import gc
import time
from typing import Any

import torch
from PIL import Image
from google import genai
from google.genai import types

import sys
_custom_nodes_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _custom_nodes_dir not in sys.path:
    sys.path.insert(0, _custom_nodes_dir)

try:
    from shared.gemini_client import (
        ASPECT_RATIOS,
        IMAGE_CAPABLE_MODELS,
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


class OmniSwap:
    """
    Perform a photorealistic swap (face, outfit, object, etc.) using Gemini.

    Inputs
    ------
    source_image : Source object/person to transplant.
    target_image : Image whose region will be replaced.
    prompt       : Instruction sent to Gemini (e.g. "Swap the face", "Swap the outfit").
    max_retries  : Retry budget for transient API errors.
    """

    DESCRIPTION = "Image swap via Gemini image generation API"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gemini_config": ("GEMINI_CONFIG",),
                "model": (IMAGE_CAPABLE_MODELS, {"default": "gemini-3-pro-image-preview"}),
                "source_image":  ("IMAGE",),
                "target_image":  ("IMAGE",),
                "prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": (
                            "IMAGE 1 is the source. IMAGE 2 is the target.\n"
                            "Replace the relevant part in IMAGE 2 with the one from IMAGE 1.\n"
                            "Preserve everything else in IMAGE 2 exactly: background, pose, lighting, etc.\n"
                            "The result must be photorealistic with no visible seams or artifacts."
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
                "aspect_ratio": (ASPECT_RATIOS,),
                "temperature":  ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "resolution":   (["1K", "2K", "4K"], {"default": "1K"}),
                "max_retries":  ("INT",   {"default": 5, "min": 1, "max": 15, "step": 1}),
                "batch_size":   ("INT",   {"default": 1, "min": 1, "max": 4, "step": 1}),
                "delay_between_calls": ("FLOAT", {"default": 3.0, "min": 0.0, "max": 900.0, "step": 0.5}),
            },
            "optional": {
                "skip_trigger": ("STRING", {"forceInput": True, "tooltip": "Status message to evaluate."})
            }
        }

    RETURN_TYPES  = ("IMAGE", "STRING")
    RETURN_NAMES  = ("swapped_image", "status_message")
    FUNCTION      = "run"
    CATEGORY      = "Omni"
    OUTPUT_NODE   = False

    def run(
        self,
        gemini_config: dict,
        source_image:  torch.Tensor,
        target_image:  torch.Tensor,
        prompt:        str,
        negative_prompt: str,
        aspect_ratio:  str,
        temperature:   float,
        model:         str = "gemini-3-pro-image-preview",
        resolution:    str = "1K",
        max_retries:   int = 5,
        batch_size:    int = 1,
        delay_between_calls: float = 3.0,
        skip_trigger:  str = "",
    ) -> tuple[torch.Tensor, str]:

        if skip_trigger and skip_trigger.strip().upper().startswith("FAIL"):
            print(f"[OmniSwap] 🛑 Upstream failure detected. Skipping swap and propagating FAIL.")
            return (target_image, skip_trigger)

        print(f"[OmniSwap] Starting swap with {model}…")

        client = create_gemini_client(gemini_config)

        source_pil = tensor_to_pil(source_image)
        target_pil = tensor_to_pil(target_image)
        
        source_byte_arr = io.BytesIO()
        source_pil.save(source_byte_arr, format='PNG')
        source_bytes = source_byte_arr.getvalue()
        
        target_byte_arr = io.BytesIO()
        target_pil.save(target_byte_arr, format='PNG')
        target_bytes = target_byte_arr.getvalue()

        print(f"[OmniSwap] Source: {source_pil.size}")
        print(f"[OmniSwap] Target: {target_pil.size}")

        final_prompt = prompt.strip()
        if negative_prompt and negative_prompt.strip():
            final_prompt += f"\n\nNegative instructions (DO NOT INCLUDE): {negative_prompt.strip()}"

        contents = [
            "IMAGE 1 — Source:",
            types.Part.from_bytes(data=source_bytes, mime_type="image/png"),
            "IMAGE 2 — Target (image to be replaced):",
            types.Part.from_bytes(data=target_bytes, mime_type="image/png"),
            final_prompt,
        ]

        config: dict[str, Any] = {
            "response_modalities": ["IMAGE"],
            "temperature": temperature,
        }
        img_cfg = {"image_size": resolution}
        if aspect_ratio.upper() not in ("AUTO", ""):
            img_cfg["aspect_ratio"] = aspect_ratio
        config["image_config"] = img_cfg

        results = []
        last_status_msg = "Success"
        
        for i in range(batch_size):
            if i > 0 and delay_between_calls > 0:
                print(f"[OmniSwap] Waiting {delay_between_calls}s before next call...")
                time.sleep(delay_between_calls)
            print(f"[OmniSwap] Generating image {i + 1}/{batch_size}...")
            response, status_msg = call_with_retry(client, model, contents, config, max_retries)
            last_status_msg = status_msg

            if response is None:
                print(f"[OmniSwap] ⚠ API Error on image {i + 1}: {status_msg}")
                continue

            result_pil = extract_image_from_response(response)

            if result_pil is None:
                print(f"[OmniSwap] ⚠ No image in response {i + 1}.")
                continue

            print(f"[OmniSwap] ✓ Image {i + 1} Done — output size: {result_pil.size}")
            results.append(pil_to_tensor(result_pil))

            del result_pil
            del response

        del contents
        del source_pil
        del target_pil
        gc.collect()

        if len(results) > 0:
            out_tensor = torch.cat(results, dim=0)
            return (out_tensor, last_status_msg)
        else:
            print("[OmniSwap] ⚠ No valid images generated. Returning target unchanged, emitting FAIL trigger.")
            error_msg = f"FAIL: {last_status_msg}"
            return (target_image, error_msg)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
