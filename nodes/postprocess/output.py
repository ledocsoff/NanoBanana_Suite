"""
NanoBanana PostProcess Nodes for ComfyUI
=========================================
Save and preview images within ComfyUI workflows.

Nodes:
  - NanoBananaPreview   : Preview image inline (pass-through).
  - NanoBananaCleanSave : Save image to absolute path without metadata.
"""

from __future__ import annotations

import os
import time

import torch
from PIL import Image

import folder_paths

# Shared imports — single source of truth
import sys
_custom_nodes_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _custom_nodes_dir not in sys.path:
    sys.path.insert(0, _custom_nodes_dir)

try:
    from shared.gemini_client import tensor_to_pil, pil_to_tensor
except ImportError:
    raise ImportError(
        "shared package not found. "
        "Make sure it is symlinked in custom_nodes/."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Node – Preview Image (Pass-Through)
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
            img = tensor_to_pil(image)
            
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
# Node – Clean Save (No Metadata)
# ──────────────────────────────────────────────────────────────────────────────

class NanoBananaCleanSave:
    """
    Saves an image to an absolute path on the disk without adding ANY ComfyUI 
    or EXIF metadata.
    """
    DESCRIPTION = "Save an image to a custom path without any metadata"

    @classmethod
    def INPUT_TYPES(s):
        import folder_paths as fp
        default_out = os.path.join(fp.get_output_directory(), "NanoBanana")
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
            import folder_paths as fp
            save_path = os.path.join(fp.get_output_directory(), "NanoBanana")
            
        os.makedirs(save_path, exist_ok=True)
        
        results = list()
        
        for (batch_number, image) in enumerate(images):
            img = tensor_to_pil(image)
            
            # Remove EXIF/Metadata by copying only pixel data into a fresh Image
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)
            
            timestamp = int(time.time() * 1000)
            file = f"{filename_prefix}_{timestamp}_{batch_number}.png"
            full_path = os.path.join(save_path, file)
            
            clean_img.save(full_path, pnginfo=None, compress_level=1)
            
            results.append({
                "filename": file,
                "subfolder": "",
                "type": "output"
            })

        print(f"[NanoBananaCleanSave] Saved {len(images)} clean image(s) to '{save_path}'")
        return { "ui": { "images": results }, "result": (images,) }
