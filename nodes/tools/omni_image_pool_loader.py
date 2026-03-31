import os
import glob
import random
import time
from pathlib import Path

import torch
import numpy as np
from PIL import Image, ImageOps

class Omni_ImagePoolLoader:
    CATEGORY = "Omni/Tools"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "filename")
    FUNCTION = "load_image"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "", "tooltip": "Absolute path to your image pool folder"}),
                "mode": (["random", "sequential", "fixed_index"], {"default": "random"}),
                "index": ("INT", {"default": 1, "min": 1, "max": 99999, "step": 1, "tooltip": "Used in sequential or fixed mode"}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, folder_path, mode, index, **kwargs):
        # Force re-evaluation if in random or sequential mode
        if mode == "random" or mode == "sequential":
            return time.time()
        return hash((folder_path, mode, index))

    def _get_supported_files(self, folder_path):
        extensions = [".png", ".jpg", ".jpeg", ".webp"]
        files = []
        for ext in extensions:
            pattern = os.path.join(folder_path, f"*{ext}")
            files.extend(glob.glob(pattern))
            pattern_upper = os.path.join(folder_path, f"*{ext.upper()}")
            files.extend(glob.glob(pattern_upper))
        return sorted(list(set(files)))

    def load_image(self, folder_path, mode, index):
        if not folder_path or not os.path.exists(folder_path):
            raise Exception(f"[Omni Image Pool Loader] L'erreur: Dossier introuvable: '{folder_path}'")

        files = self._get_supported_files(folder_path)
        
        if not files:
            raise Exception(f"[Omni Image Pool Loader] L'erreur: Aucun fichier image trouve dans: '{folder_path}'")

        total_files = len(files)
        
        # Determine the file to load
        if mode == "random":
            selected_file = random.choice(files)
        elif mode == "sequential":
            # 1-indexed, so we subtract 1. Modulo to wrap around.
            idx = (index - 1) % total_files
            selected_file = files[idx]
        elif mode == "fixed_index":
            # Just cap it to the available files to avoid crash
            idx = min(max(index - 1, 0), total_files - 1)
            selected_file = files[idx]
        else:
            selected_file = files[0]

        filename = os.path.basename(selected_file)
        print(f"[Omni Image Pool Loader] Chargement de: {filename} ({mode})")

        # Process Image for ComfyUI [1, H, W, 3] Float tensor
        img = Image.open(selected_file)
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        
        image_np = np.array(img).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_np)[None,]

        return (image_tensor, filename)

NODE_CLASS_MAPPINGS = {"Omni_ImagePoolLoader": Omni_ImagePoolLoader}
NODE_DISPLAY_NAME_MAPPINGS = {"Omni_ImagePoolLoader": "Image Pool Loader"}
