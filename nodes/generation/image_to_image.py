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


class NanoBananaImageToImage:
    """
    Generate or modify an image using a single reference image and a text prompt via Gemini.
    """

    DESCRIPTION = "Image-to-Image composition via Gemini image generation API"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gemini_config":      ("GEMINI_CONFIG",),
                "image":              ("IMAGE",),
                "positive_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": (
                            "Use this image as a reference and modify it according to these instructions. RE-RENDER the image with ultra-high frequency detail and pristine photographic sharpness, avoiding any blur or source compression artifacts. "
                        ),
                    },
                ),
                "negative_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                    },
                ),
                "aspect_ratio":       (ASPECT_RATIOS,),
                "temperature":        ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "resolution":         (["1K", "2K", "4K"], {"default": "1K"}),
                "max_retries":        ("INT",   {"default": 5, "min": 1, "max": 15, "step": 1}),
                "batch_size":         ("INT",   {"default": 1, "min": 1, "max": 4, "step": 1}),
                "delay_between_calls": ("FLOAT", {"default": 3.0, "min": 0.0, "max": 15.0, "step": 0.5}),
            },
        }

    RETURN_TYPES  = ("IMAGE", "STRING")
    RETURN_NAMES  = ("generated_image", "status_message")
    FUNCTION      = "run"
    CATEGORY      = "NanoBanana"
    OUTPUT_NODE   = False

    def run(
        self,
        gemini_config:      dict,
        image:              torch.Tensor,
        positive_prompt:    str,
        negative_prompt:    str,
        aspect_ratio:       str,
        temperature:        float,
        resolution:         str = "1K",
        max_retries:        int = 5,
        batch_size:         int = 1,
        delay_between_calls: float = 3.0,
    ) -> tuple[torch.Tensor, str]:

        print("[NanoBananaImageToImage] Starting image generation…")

        client, model = create_gemini_client(gemini_config)

        pil_img = tensor_to_pil(image)
        img_byte_arr = io.BytesIO()
        pil_img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        print(f"[NanoBananaImageToImage] Input image: {pil_img.size}")

        final_prompt = positive_prompt.strip()
        if negative_prompt.strip():
            final_prompt += f"\n\nNegative instructions (DO NOT INCLUDE): {negative_prompt.strip()}"

        contents = [
            "Reference Image:",
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
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
                print(f"[NanoBananaImageToImage] Waiting {delay_between_calls}s before next call...")
                time.sleep(delay_between_calls)
            print(f"[NanoBananaImageToImage] Generating image {i + 1}/{batch_size}...")
            response, status_msg = call_with_retry(client, model, contents, config, max_retries)
            last_status_msg = status_msg

            if response is None:
                print(f"[NanoBananaImageToImage] ⚠ API Error on image {i + 1}: {status_msg}")
                continue

            result_pil = extract_image_from_response(response)

            if result_pil is None:
                print(f"[NanoBananaImageToImage] ⚠ No image in response {i + 1}.")
                continue

            print(f"[NanoBananaImageToImage] ✓ Image {i + 1} Done — output size: {result_pil.size}")
            results.append(pil_to_tensor(result_pil))

            del result_pil
            del response

        del contents
        del pil_img
        gc.collect()

        if len(results) > 0:
            out_tensor = torch.cat(results, dim=0)
            return (out_tensor, last_status_msg)
        else:
            print("[NanoBananaImageToImage] ⚠ No valid images generated. Returning original image as fallback.")
            return (image, last_status_msg)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
