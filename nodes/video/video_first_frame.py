import torch
from ...core import video_utils, image_utils

class NB_VideoFirstFrame:
    CATEGORY = "NanaBanana/Video"
    FUNCTION = "extract"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("first_frame",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "current_video_path": ("STRING", {"forceInput": True}),
                "frame_index": ("INT", {"default": 0, "min": 0, "max": 999})
            }
        }

    def extract(self, current_video_path, frame_index):
        if not current_video_path:
            return (torch.zeros((1, 1, 1, 3), dtype=torch.float32),)

        try:
            frame = video_utils.extract_frame(current_video_path, frame_index)
            tensor = image_utils.frame_to_tensor(frame)
            return (tensor,)
        except Exception as e:
            print(f"[NanaBanana] ⚠️ Failed to extract frame: {e}")
            return (torch.zeros((1, 1, 1, 3), dtype=torch.float32),)
