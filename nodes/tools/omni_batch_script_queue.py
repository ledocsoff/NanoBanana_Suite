import os
import time
import random
import string

class Omni_BatchScriptQueue:
    """A purely stateless node that generates random filenames.
    Relies entirely on ComfyUI's native Auto-Queue for looping.
    Class name left as Omni_BatchScriptQueue for backwards compatibility,
    but it now simply outputs unique string names."""
    
    CATEGORY = "Omni"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_folder", "filename_stem")
    FUNCTION = "generate_name"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_folder": ("STRING", {
                    "default": "./output/kling_videos",
                    "tooltip": "Path where generated videos will be saved."
                }),
                "filename_prefix": ("STRING", {
                    "default": "reel_",
                    "tooltip": "Prefix for the generated video (e.g., 'reel_' -> 'reel_a1b2c3.mp4')."
                }),
                "auto_create_folders": ("BOOLEAN", {"default": True}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Force execution every ComfyUI run to guarantee a new random name
        return time.time()

    def generate_name(self, output_folder, filename_prefix, auto_create_folders):
        if auto_create_folders and output_folder:
            os.makedirs(output_folder, exist_ok=True)

        random_chars = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        filename_stem = f"{filename_prefix}{random_chars}"

        print(f"[Omni_RandomName] 🎲 Generated unique stem: {filename_stem}")

        return (output_folder, filename_stem)

NODE_CLASS_MAPPINGS = {"Omni_BatchScriptQueue": Omni_BatchScriptQueue}
NODE_DISPLAY_NAME_MAPPINGS = {"Omni_BatchScriptQueue": "🎲 Random Filename Generator"}
