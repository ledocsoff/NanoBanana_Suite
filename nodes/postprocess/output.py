"""
NanoBanana Custom Nodes for ComfyUI
====================================
Integrates Google AI Studio (Gemini) image generation into ComfyUI workflows.

Nodes:
  - NanoBananaSwap      : Replace a source region in a target image.
  - NanoBananaCleanSave : Save image cleanly.
  - NanoBananaPreview   : Preview image inline.

Requirements:
  - google-genai  (`pip install google-genai`)
  - A valid Google AI Studio API key with the Generative Language API enabled.
"""

from __future__ import annotations

import io
import os
import random
import time
import traceback
import gc
from typing import Optional, Any

import json
import numpy as np
import torch
from PIL import Image
from google import genai
import folder_paths

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

AVAILABLE_MODELS = [
    "gemini-3-pro-image-preview",
]

ASPECT_RATIOS = ["AUTO", "1:1", "16:9", "4:3", "3:4", "9:16"]


# ──────────────────────────────────────────────────────────────────────────────
# Image utilities  (ComfyUI tensor ↔ PIL)
# ──────────────────────────────────────────────────────────────────────────────

def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """
    Convert a ComfyUI IMAGE tensor  (B, H, W, C)  float32 [0, 1]  →  PIL RGB.
    Handles both batched and single-frame tensors.
    """
    t = tensor
    if t.dim() == 4:
        t = t[0]
    t = t.detach().cpu()
    np_img = (t.numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np_img, "RGB")


def pil_to_tensor(img: Image.Image) -> torch.Tensor:
    """
    Convert a PIL Image  →  ComfyUI IMAGE tensor  (1, H, W, C)  float32 [0, 1].
    """
    arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_rate_limit_error(error: Exception) -> bool:
    """Check if the error is a rate limit / quota error."""
    s = str(error).lower()
    return any(x in s for x in [
        "429", "resource_exhausted", "resource exhausted",
        "too many requests", "rate limit", "quota exceeded", "quota_exceeded"
    ])


def _extract_image_from_response(response) -> Optional[Image.Image]:
    """
    Extract the first image part from a google.genai SDK response object.
    Returns a PIL Image or None.
    """
    if not response or not hasattr(response, "candidates") or not response.candidates:
        print(f"[NanoBanana] ⚠ Empty response or no candidates: {response}")
        return None

    candidate = response.candidates[0]
    if not hasattr(candidate, "content") or not candidate.content or not hasattr(candidate.content, "parts") or not candidate.content.parts:
        print(f"[NanoBanana] ⚠ Candidate has no content parts: {candidate}")
        return None

    # Try to find an image in the parts
    for part in candidate.content.parts:
        try:
            # 1. Check for standard inline_data (bytes)
            if hasattr(part, "inline_data") and part.inline_data:
                data = part.inline_data.data
                if data:
                    return Image.open(io.BytesIO(data)).convert("RGB")
                    
            # 2. Check for newer genai SDK structure (part.image or part.file_data)
            elif hasattr(part, "image") and part.image:
                # Sometimes part.image has image_bytes
                if hasattr(part.image, "image_bytes"):
                    return Image.open(io.BytesIO(part.image.image_bytes)).convert("RGB")
                # Sometimes it is just a PIL image directly in some SDK wrappers
                if isinstance(part.image, Image.Image):
                    return part.image.convert("RGB")
                    
        except Exception as e:
            print(f"[NanoBanana] ⚠ Error parsing part into PIL image: {e}")

    # If we got here, no image was found. Let's log EXACTLY what Gemini replied.
    print("[NanoBanana] ⚠ Gemini API replied successfully, but with NO image.")
    print("--- RAW API RESPONSE START ---")
    for part in candidate.content.parts:
        if hasattr(part, "text") and part.text:
            print(f"TEXT: {part.text}")
        else:
            print(f"UNKNOWN PART TYPE: {dir(part)}")
    print("--- RAW API RESPONSE END ---")
    
    return None


def _call_with_retry(
    client: genai.Client,
    model: str,
    contents: list,
    config: dict,
    max_retries: int,
) -> tuple[Optional[object], str]:
    """
    Call client.models.generate_content with exponential backoff.
    Mirrors the retry logic from base.py.
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            print(f"[NanoBanana] → {model}  attempt {attempt + 1}/{max_retries}")
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            
            # Check if Gemini blocked it but returned 200 OK
            if response and hasattr(response, "candidates") and response.candidates:
                cand = response.candidates[0]
                if hasattr(cand, "finish_reason") and cand.finish_reason:
                    reason_str = str(cand.finish_reason).upper()
                    if "SAFETY" in reason_str or "BLOCK" in reason_str:
                        print(f"[NanoBanana] ⚠ Content blocked by API internal filters (Finish Reason: {reason_str})")
                        return None, f"SAFETY_BLOCK: {reason_str}"
            
            return response, "Success"

        except Exception as e:
            last_error = e

            if _is_rate_limit_error(e):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
                    print(f"[NanoBanana] ⏳ Rate limited. Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}…")
                    time.sleep(wait_time)
                    continue
                else:
                    return None, f"Rate limit exceeded after {max_retries} retries. Last error: {str(e)}"

            elif any(t in str(e).lower() for t in ["safety", "blocked", "policy", "harmful"]):
                print(f"[NanoBanana] ⚠ Content blocked by safety filters: {e}")
                return None, f"Content blocked by safety filters. Try modifying your prompt or images. ({str(e)})"

            else:
                print(f"[NanoBanana] ✗ Error: {e}")
                traceback.print_exc()
                return None, f"Gemini API Error: {str(e)}"

    return None, f"All {max_retries} attempts failed. Last error: {str(last_error)}"


# ──────────────────────────────────────────────────────────────────────────────
# Node 1 – Face Swap
# ──────────────────────────────────────────────────────────────────────────────

class NanoBananaPreview:
    """
    Displays an image preview in the node and passes the image through as output.
    Allows chaining to other nodes like CleanSave.
    """
    DESCRIPTION = "Preview an image and pass it to output"

    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_temp"
        self.compress_level = 1

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "preview_images"
    OUTPUT_NODE = True
    CATEGORY = "NanoBanana"

    def preview_images(self, images):
        filename_prefix = "NanoBanana_Preview" + self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
        
        for (batch_number, image) in enumerate(images):
            # Convert single image tensor to PIL directly
            img = tensor_to_pil(image)
            
            # Save without metadata (pnginfo=None) to temp folder
            file = f"{filename}_{counter:05}_.png"
            img.save(os.path.join(full_output_folder, file), pnginfo=None, compress_level=self.compress_level)
            
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        print(f"[NanoBananaPreview] Saved {len(images)} preview image(s) to {full_output_folder}")
        return { "ui": { "images": results }, "result": (images,) }

# ──────────────────────────────────────────────────────────────────────────────
# Node 6 – Prompt Matrix API Core (Direct Generation)
# ──────────────────────────────────────────────────────────────────────────────
import json

class NanoBananaCleanSave:
    """
    Saves an image to an absolute path on the disk without adding ANY ComfyUI 
    or EXIF metadata.
    """
    DESCRIPTION = "Save an image to a custom path without any metadata"

    @classmethod
    def INPUT_TYPES(s):
        import os
        import folder_paths
        default_out = os.path.join(folder_paths.get_output_directory(), "NanoBanana")
        return {
            "required": {
                "images": ("IMAGE", ),
                "save_path": ("STRING", {"default": default_out, "multiline": False}),
                "filename_prefix": ("STRING", {"default": "NanoBanana_Clean"})
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "NanoBanana"

    def save_images(self, images, save_path="", filename_prefix="NanoBanana_Clean"):
        if not save_path:
            import folder_paths
            save_path = os.path.join(folder_paths.get_output_directory(), "NanoBanana")
            
        # Ensure the output directory exists
        os.makedirs(save_path, exist_ok=True)
        
        results = list()
        
        for (batch_number, image) in enumerate(images):
            # Convert single image tensor to PIL directly
            img = tensor_to_pil(image)
            
            # Remove EXIF/Metadata if any by copying only the image data into a new Image
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)
            
            # Generate a unique filename using timestamp
            timestamp = int(time.time() * 1000)
            file = f"{filename_prefix}_{timestamp}_{batch_number}.png"
            full_path = os.path.join(save_path, file)
            
            # Save without metadata (pnginfo=None) with minimal compression for max quality
            clean_img.save(full_path, pnginfo=None, compress_level=1)
            
            results.append({
                "filename": file,
                "subfolder": "",  # Not using ComfyUI deep subfolders here
                "type": "output"
            })

        print(f"[NanoBananaCleanSave] Saved {len(images)} clean image(s) to '{save_path}'")
        return { "ui": { "images": results }, "result": (images,) }


# ──────────────────────────────────────────────────────────────────────────────
# Node 5 – Preview Image (Pass-Through)
# ──────────────────────────────────────────────────────────────────────────────

