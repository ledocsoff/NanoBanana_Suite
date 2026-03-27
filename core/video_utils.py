import os
import glob
import cv2
import math
import numpy as np

def extract_metadata(video_path: str) -> dict:
    if not os.path.exists(video_path):
        raise ValueError(f"File not found: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    try:
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0.0
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        filename = os.path.splitext(os.path.basename(video_path))[0]
        extension = os.path.splitext(video_path)[1]
        
        filesize_mb = os.path.getsize(video_path) / (1024 * 1024)
        aspect_ratio = compute_aspect_ratio(width, height)
        
        return {
            "fps": fps,
            "frame_count": frame_count,
            "duration": duration,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "filename": filename,
            "extension": extension,
            "filesize_mb": filesize_mb
        }
    finally:
        cap.release()

def extract_frame(video_path: str, frame_index: int = 0) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
        
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()
        if not ret:
            raise ValueError(f"Cannot read frame {frame_index} from {video_path}")
            
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    finally:
        cap.release()

def get_video_files(folder: str, extensions: tuple = (".mp4", ".mov", ".webm"), recursive: bool = False) -> list:
    """List video files in a folder. If recursive=True, walks all subdirectories."""
    video_files = []
    exts = tuple(ext.lower() for ext in extensions)

    if not os.path.exists(folder):
        return video_files

    if recursive:
        for root, _dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(exts):
                    video_files.append(os.path.abspath(os.path.join(root, file)))
    else:
        for file in os.listdir(folder):
            path = os.path.join(folder, file)
            if os.path.isfile(path) and file.lower().endswith(exts):
                video_files.append(os.path.abspath(path))

    return sorted(video_files)

def compute_aspect_ratio(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "0:0"
    gcd = math.gcd(width, height)
    return f"{width//gcd}:{height//gcd}"
