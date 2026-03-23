"""
NanoBanana Chooser — Interactive Image Selection
===============================================
Pauses ComfyUI execution, sends temporary tensors to the Javascript frontend, 
and waits for the user to make a manual selection before resuming.
"""

import os
import time
import uuid
import threading
from typing import Optional, List, Dict, Any

import torch
import numpy as np
from PIL import Image
from aiohttp import web

import folder_paths
import comfy.model_management
from server import PromptServer

# ──────────────────────────────────────────────────────────────────────────────
# Global Thread-Safe State
# ──────────────────────────────────────────────────────────────────────────────
_state_lock = threading.Lock()
_pending_selections: Dict[str, Dict[str, Any]] = {}


@PromptServer.instance.routes.post("/nanobanana/chooser/select")
async def chooser_select(request):
    """API Endpoint: Receives the specific indices the user selected via UI."""
    data = await request.json()
    node_id = data.get("node_id")
    indices = data.get("indices", [])
    
    with _state_lock:
        if node_id in _pending_selections:
            _pending_selections[node_id]["indices"] = indices
            _pending_selections[node_id]["event"].set()
            return web.json_response({"status": "ok"})
            
    return web.json_response({"status": "error", "message": "Node not waiting"})


def _tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """Safely convert a single ComfyUI tensor (C,H,W or B,C,H,W) to PIL."""
    t = tensor
    if t.dim() == 4:
        t = t[0]
    t = t.detach().cpu()
    np_img = (t.numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np_img, "RGB")


# ──────────────────────────────────────────────────────────────────────────────
# Node
# ──────────────────────────────────────────────────────────────────────────────

class NanoBananaChooser:
    DESCRIPTION = "Pause execution and wait for manual image selection via UI."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "mode": (["Sélection unique", "Sélection multiple"], {"default": "Sélection unique"}),
                "timeout": ("INT", {"default": 600, "min": 60, "max": 3600, "step": 10}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("images", "count")
    FUNCTION = "run"
    CATEGORY = "NanoBanana"
    OUTPUT_NODE = True 

    def run(self, images: torch.Tensor, mode: str, timeout: int, unique_id: str):
        batch_size = images.shape[0]
        
        # 1. Single image fallback (no choice required)
        if batch_size == 1:
            print(f"[NanoBananaChooser] Single image received — passing through (no selection needed)")
            return (images, 1)

        temp_dir = folder_paths.get_temp_directory()
        os.makedirs(temp_dir, exist_ok=True)
        
        # 2. Save images temporarily for frontend viewing
        session_id = uuid.uuid4().hex[:8]
        saved_files = []
        ui_images = []
        
        print(f"[NanoBananaChooser] Received {batch_size} images — waiting for user selection…")
        
        for i in range(batch_size):
            img_pil = _tensor_to_pil(images[i])
            filename = f"nanobanana_chooser_{session_id}_{i}.png"
            filepath = os.path.join(temp_dir, filename)
            
            # Fast minimal compression for temp preview
            img_pil.save(filepath, compress_level=1)
            saved_files.append(filepath)
            
            ui_images.append({
                "filename": filename,
                "subfolder": "",  # root of ComfyUI temp folder
                "type": "temp"
            })
            
        # 3. Setup thread-safe Event
        event = threading.Event()
        with _state_lock:
            _pending_selections[unique_id] = {
                "event": event,
                "indices": [],
            }
            
        # 4. Notify frontend to mount the selection UI
        PromptServer.instance.send_sync("nanobanana.chooser.display", {
            "node_id": unique_id,
            "images": ui_images,
            "mode": mode,
            "timeout": timeout
        })
        
        print(f"[NanoBananaChooser] ⏳ Waiting for selection in ComfyUI interface… (if you don't see the chooser, refresh the page)")
        print(f"[NanoBananaChooser] ⏱ Timeout set to {timeout}s.")
        
        # 5. Polling wait — allows ComfyUI workflow Cancellation to immediately exit
        elapsed = 0.0
        poll_interval = 0.5
        interrupted_by_user = False
        
        while not event.is_set():
            if comfy.model_management.processing_interrupted():
                interrupted_by_user = True
                break
                
            event.wait(timeout=poll_interval)
            elapsed += poll_interval
            if elapsed >= timeout:
                break
                
        # 6. Safety teardown
        with _state_lock:
            selected_indices = _pending_selections.get(unique_id, {}).get("indices", [])
            if unique_id in _pending_selections:
                del _pending_selections[unique_id]
            
        # Hard cleanup of temporary display files (avoids disk filling up over runs)
        for f in saved_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                print(f"[NanoBananaChooser] ⚠ Failed to delete temp file {f}: {e}")
                
        # Exception if user clicked "Cancel Queue" in ComfyUI
        if interrupted_by_user:
            raise InterruptedError("[NanoBananaChooser] Workflow cancelled by user.")
            
        # Handle strict Timeout
        if not selected_indices:
            print(f"[NanoBananaChooser] ⚠ Timeout reached ({timeout}s) or empty selection — passing all {batch_size} images through")
            return (images, batch_size)
            
        # 7. Extract the chosen tensors via array slicing
        selected_indices.sort()
        print(f"[NanoBananaChooser] ✓ User selected image(s): {selected_indices} — resuming workflow")
        
        # Secure bounds selection
        selected_tensors = [images[i] for i in selected_indices if i >= 0 and i < batch_size]
        
        if not selected_tensors:
            print(f"[NanoBananaChooser] ❌ Bad indices received, falling back to all images.")
            return (images, batch_size)
            
        # Stack back (B,H,W,C)
        final_tensor = torch.stack(selected_tensors)
        return (final_tensor, len(selected_tensors))
