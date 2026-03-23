import os
import glob
from ...core import video_utils, file_manager

class NB_BatchVideoQueue:
    OUTPUT_NODE = True
    CATEGORY = "NanaBanana/Batch"
    FUNCTION = "get_next"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "FLOAT", "INT", "INT", "INT")
    RETURN_NAMES = ("current_video_path", "output_folder", "done_folder",
                    "video_filename", "source_duration", "source_fps",
                    "current_index", "total_count")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_folder": ("STRING", {"default": ""}),
                "done_folder": ("STRING", {"default": ""}),
                "output_folder": ("STRING", {"default": ""}),
                "file_extensions": ("STRING", {"default": "mp4,mov,webm"}),
                "sort_order": (["alphabetical", "date_modified"], {"default": "alphabetical"}),
                "auto_create_folders": ("BOOLEAN", {"default": True})
            }
        }

    @classmethod
    def IS_CHANGED(cls, source_folder, **kwargs):
        if not source_folder or not os.path.exists(source_folder):
            return 0
        try:
            files = sorted(glob.glob(os.path.join(source_folder, "*")))
            return hash(tuple(files))
        except Exception:
            return 0

    def get_next(self, source_folder, done_folder, output_folder, file_extensions, sort_order, auto_create_folders):
        empty_return = ("", output_folder, done_folder, "", 0.0, 0, 0, 0)
        if not source_folder or not os.path.exists(source_folder):
            if auto_create_folders and source_folder:
                file_manager.ensure_folder(source_folder)
            else:
                return empty_return

        if auto_create_folders:
            if done_folder: file_manager.ensure_folder(done_folder)
            if output_folder: file_manager.ensure_folder(output_folder)

        exts = tuple(f".{ext.strip()}" for ext in file_extensions.replace(' ', '').split(',') if ext)
        if not exts: exts = (".mp4", ".mov", ".webm")

        source_files = video_utils.get_video_files(source_folder, exts)
        
        pending_files = []
        for vpath in source_files:
            fname = os.path.basename(vpath)
            if done_folder and os.path.exists(os.path.join(done_folder, fname)):
                continue
            pending_files.append(vpath)

        if sort_order == "date_modified":
            pending_files.sort(key=os.path.getmtime)
        else:
            pending_files.sort()

        if not pending_files:
            print("[NanaBanana] 🏁 Batch complete. No pending videos in the source folder.")
            return empty_return

        current_video = pending_files[0]
        try:
            metadata = video_utils.extract_metadata(current_video)
        except Exception as e:
            print(f"[NanaBanana] ⚠️ Failed to extract metadata for {current_video}: {e}")
            return empty_return

        current_index = 1
        total_count = len(pending_files)
        filename = metadata["filename"]
        duration = metadata["duration"]
        fps = metadata["fps"]

        print(f"[NanaBanana] 📂 {current_index}/{total_count} | {filename} | {duration:.1f}s")
        return (current_video, output_folder, done_folder, filename, duration, fps, current_index, total_count)
