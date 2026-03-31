import os
import glob
from ...core import video_utils, file_manager

class Omni_BatchVideoQueue:
    OUTPUT_NODE = True
    CATEGORY = "Omni/Batch"
    FUNCTION = "get_next"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "FLOAT", "INT", "INT", "INT")
    RETURN_NAMES = ("current_video_path", "output_folder", "done_folder",
                    "video_filename", "relative_subfolder",
                    "source_duration", "source_fps",
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
                "auto_create_folders": ("BOOLEAN", {"default": True}),
                "recursive": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Scanner les sous-dossiers récursivement. "
                               "La structure est préservée dans output/ et done/."
                }),
            }
        }

    @classmethod
    def IS_CHANGED(cls, source_folder, recursive=False, **kwargs):
        if not source_folder or not os.path.exists(source_folder):
            return 0
        try:
            if recursive:
                all_files = []
                for root, _, files in os.walk(source_folder):
                    all_files.extend(os.path.join(root, f) for f in files)
                return hash(tuple(sorted(all_files)))
            else:
                files = sorted(glob.glob(os.path.join(source_folder, "*")))
                return hash(tuple(files))
        except Exception:
            return 0

    def get_next(self, source_folder, done_folder, output_folder,
                 file_extensions, sort_order, auto_create_folders, recursive=False):

        empty_return = ("", output_folder, done_folder, "", "", 0.0, 0, 0, 0)

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

        source_folder_abs = os.path.abspath(source_folder)
        source_files = video_utils.get_video_files(source_folder_abs, exts, recursive=recursive)

        # Filter out already-processed files (check relative path in done_folder)
        pending_files = []
        for vpath in source_files:
            rel_path = os.path.relpath(vpath, source_folder_abs)
            if done_folder and os.path.exists(os.path.join(done_folder, rel_path)):
                continue
            pending_files.append(vpath)

        if sort_order == "date_modified":
            pending_files.sort(key=os.path.getmtime)
        else:
            pending_files.sort()

        if not pending_files:
            print("[Omni] 🏁 Batch complete. No pending videos in the source folder.")
            return empty_return

        current_video = pending_files[0]

        # Compute relative subfolder (empty string if flat)
        rel_path = os.path.relpath(current_video, source_folder_abs)
        relative_subfolder = os.path.dirname(rel_path)  # "egirl" or "egirl/sub" or ""

        try:
            metadata = video_utils.extract_metadata(current_video)
        except Exception as e:
            print(f"[Omni] ⚠️ Failed to extract metadata for {current_video}: {e}")
            return empty_return

        current_index = 1
        total_count = len(pending_files)
        filename = metadata["filename"]
        duration = metadata["duration"]
        fps = metadata["fps"]

        subfolder_info = f" [{relative_subfolder}]" if relative_subfolder else ""
        print(f"[Omni] 📂 {current_index}/{total_count} | {filename}{subfolder_info} | {duration:.1f}s")

        return (current_video, output_folder, done_folder, filename,
                relative_subfolder, duration, fps, current_index, total_count)
