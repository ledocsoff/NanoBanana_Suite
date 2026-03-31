import os
import shutil

def ensure_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def move_file(src: str, dest_folder: str) -> str:
    if not os.path.exists(src):
        raise ValueError(f"Source file not found: {src}")
        
    ensure_folder(dest_folder)
    
    filename = os.path.basename(src)
    name, ext = os.path.splitext(filename)
    dest_path = os.path.join(dest_folder, filename)
    
    counter = 1
    while os.path.exists(dest_path):
        dest_path = os.path.join(dest_folder, f"{name}_{counter}{ext}")
        counter += 1
        
    shutil.move(src, dest_path)
    return dest_path

def cleanup_files(file_paths: list) -> int:
    deleted_count = 0
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
                deleted_count += 1
            except Exception as e:
                print(f"[Omni] ⚠️ Failed to delete {path}: {e}")
    return deleted_count

def cleanup_folder_if_empty(folder: str) -> bool:
    if not os.path.exists(folder) or not os.path.isdir(folder):
        return False
        
    try:
        if not os.listdir(folder):
            os.rmdir(folder)
            return True
    except Exception as e:
        print(f"[Omni] ⚠️ Failed to remove empty folder {folder}: {e}")
    return False

def get_temp_dir(base_folder: str) -> str:
    temp_dir = os.path.join(base_folder, ".omni_temp")
    return ensure_folder(temp_dir)
