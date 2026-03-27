import requests
import base64
import time
import os
import shutil


def _move_to_failed(source_path, output_folder, done_folder, relative_subfolder=""):
    """Move a source video to a /failed subfolder, preserving relative structure."""
    if not source_path or not os.path.exists(source_path):
        return
    if done_folder:
        # Replace only the last component: /path/to/done → /path/to/failed
        parent = os.path.dirname(done_folder)
        last_part = os.path.basename(done_folder)
        failed_part = last_part.replace("done", "failed") if "done" in last_part else "failed"
        failed_base = os.path.join(parent, failed_part)
    else:
        failed_base = os.path.join(os.path.dirname(output_folder), "failed")
    failed_folder = os.path.join(failed_base, relative_subfolder) if relative_subfolder else failed_base
    os.makedirs(failed_folder, exist_ok=True)
    dest = os.path.join(failed_folder, os.path.basename(source_path))
    shutil.move(source_path, dest)
    print(f"[NanaBanana] 📦 Vidéo source déplacée vers : {failed_folder}")


class NB_PiAPIKlingMotionControl:
    CATEGORY = "NanaBanana/API"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_url", "video_filename")
    FUNCTION = "generate"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "auth": ("PIAPI_AUTH",),
                "image": ("IMAGE",),
                "video_path": ("STRING", {"default": ""}),
                "video_filename": ("STRING", {"default": ""}),
                "output_folder": ("STRING", {"default": "./output"}),

                # --- Options Kling ---
                "version": (["2.6", "3.0"], {"default": "3.0"}),
                "motion_direction": (["video", "image"], {
                    "default": "video",
                    "tooltip": "video = suit la vidéo ref (max 30s). image = suit l'image (max 10s)."
                }),
                "mode": (["std", "pro"], {
                    "default": "std",
                    "tooltip": "std = 720p. pro = 1080p."
                }),
                "keep_original_sound": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Prompt optionnel. Max 2500 chars."
                }),
                "source_video_path": ("STRING", {"default": ""}),
                "done_folder": ("STRING", {"default": ""}),
                "relative_subfolder": ("STRING", {
                    "default": "",
                    "tooltip": "Sous-dossier relatif (depuis Batch Video Queue). "
                               "Préserve la structure dans output/done/failed."
                }),
            }
        }

    def generate(self, auth, image, video_path, video_filename, output_folder,
                 version, motion_direction, mode, keep_original_sound,
                 prompt="", source_video_path="", done_folder="", relative_subfolder=""):

        # --- QUALITY GATE: skip if image is empty (all zeros = QualityGate FAIL) ---
        if image.max().item() == 0:
            print("[NanaBanana] ⚠️ Image vide reçue (Quality Gate FAIL). Skip Kling MC.")
            _move_to_failed(source_video_path, output_folder, done_folder, relative_subfolder)
            return ("", video_filename)

        # --- SWAP FAILURE DETECTION ---
        failed_swap = False
        try:
            from ...core import video_utils
            target_video = source_video_path if source_video_path and os.path.exists(source_video_path) else video_path
            if target_video and os.path.exists(target_video):
                meta = video_utils.extract_metadata(target_video)
                vid_w, vid_h = meta.get("width", 0), meta.get("height", 0)
                
                img_h, img_w = image.shape[1], image.shape[2]
                
                if vid_w > 0 and vid_h > 0 and img_w == vid_w and img_h == vid_h:
                    failed_swap = True
                    print(f"[NanaBanana] ⚠️ Échec du FaceSwap détecté (dimensions identiques {img_w}x{img_h}). Skip API Kling pour économiser les crédits.")
        except Exception as e:
            print(f"[NanaBanana] ⚠️ Erreur lors de la vérification des dimensions : {e}")

        if failed_swap:
            _move_to_failed(source_video_path, output_folder, done_folder, relative_subfolder)
            return ("", video_filename)

        try:
            # 1. Upload de l'image
            print(f"[NanaBanana] 📤 Uploading image to PiAPI ephemeral storage...")
            image_b64 = self._tensor_to_base64(image)
            image_url = self._upload_file(auth, f"{video_filename}_char.png", image_b64)

            # 2. Upload de la vidéo motion reference
            print(f"[NanaBanana] 📤 Procédure d'upload vidéo sur PiAPI ephemeral storage...")
            if not os.path.exists(video_path) and source_video_path:
                video_path = source_video_path
                
            if os.path.exists(video_path):
                file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                if file_size_mb > 9.9:
                    print(f"[NanaBanana] ⚠️ Vidéo de {file_size_mb:.1f}MB (>10MB). Compression FFmpeg automatique à la volée...")
                    import subprocess
                    compressed_path = os.path.join(output_folder, f"TEMP_compressed_{video_filename}.mp4")
                    cmd = [
                        "ffmpeg", "-y", "-i", video_path, 
                        "-vcodec", "libx264", "-crf", "28", "-preset", "fast", compressed_path
                    ]
                    # Executer et attendre
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(compressed_path):
                        video_path = compressed_path
                        print(f"[NanaBanana] ✅ Compression terminée. Nouvelle taille : {os.path.getsize(compressed_path) / (1024 * 1024):.1f}MB")
                    else:
                        raise Exception("Erreur fatale lors de la compression FFmpeg. Assurez-vous d'avoir FFmpeg installé.")
                
            video_b64 = self._file_to_base64(video_path)
            video_ext = os.path.splitext(video_path)[1].lstrip(".")
            if not video_ext:
                video_ext = "mp4"
            video_url = self._upload_file(auth, f"{video_filename}_motion.{video_ext}", video_b64)

            # 3. Créer la tâche Motion Control
            print(f"[NanaBanana] 🚀 Submitting task to PiAPI Kling ({version} {mode})...")
            payload = {
                "model": "kling",
                "task_type": "motion_control",
                "input": {
                    "image_url": image_url,
                    "video_url": video_url,
                    "preset_motion": "",
                    "motion_direction": motion_direction,
                    "keep_original_sound": keep_original_sound,
                    "mode": mode,
                    "version": version
                },
                "config": {
                    "service_mode": auth["service_mode"],
                    "webhook_config": {
                        "endpoint": "",
                        "secret": ""
                    }
                }
            }

            if prompt and prompt.strip():
                payload["input"]["prompt"] = prompt.strip()[:2500]

            response = requests.post(
                f"{auth['base_url']}/task",
                headers=auth["headers"],
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            task_data = response.json()

            if task_data.get("code") != 200:
                raise Exception(f"PiAPI task creation failed: {task_data}")

            task_id = task_data["data"]["task_id"]

            # 4. Polling
            result_url = self._poll_task(auth, task_id)

            # 5. Télécharger (preserve subfolder structure)
            effective_output = os.path.join(output_folder, relative_subfolder) if relative_subfolder else output_folder
            output_path = os.path.join(effective_output, f"{video_filename}_mc.mp4")
            os.makedirs(effective_output, exist_ok=True)
            self._download_video(result_url, output_path)

        except Exception as e:
            print(f"[NanaBanana] 🚨 ERREUR CRITIQUE PiAPI interceptée : {e}")
            print("[NanaBanana] 🛡️ Le filet de sécurité s'active. La vidéo est isolée, la queue continue.")
            
            if "TEMP_compressed_" in video_path and os.path.exists(video_path):
                os.remove(video_path)
                
            _move_to_failed(source_video_path, output_folder, done_folder, relative_subfolder)
            return ("", video_filename)

        # 6. Nettoyage et Déplacement de la source (Success — preserve subfolder)
        if "TEMP_compressed_" in video_path and os.path.exists(video_path):
            os.remove(video_path)

        if source_video_path and done_folder and os.path.exists(source_video_path):
            effective_done = os.path.join(done_folder, relative_subfolder) if relative_subfolder else done_folder
            os.makedirs(effective_done, exist_ok=True)
            dest = os.path.join(effective_done, os.path.basename(source_video_path))
            shutil.move(source_video_path, dest)
            print(f"[NanaBanana] 📦 Moved source video to {effective_done}")

        return (output_path, video_filename)

    def _upload_file(self, auth, file_name, file_data_b64):
        response = requests.post(
            auth["upload_url"],
            headers=auth["headers"],
            json={
                "file_name": file_name,
                "file_data": file_data_b64
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        if result.get("code") != 200:
            raise Exception(f"PiAPI upload failed: {result}")
        return result["data"]["url"]

    def _poll_task(self, auth, task_id, max_wait=600, interval=10):
        elapsed = 0
        while elapsed < max_wait:
            response = requests.get(
                f"{auth['base_url']}/task/{task_id}",
                headers=auth["headers"],
                timeout=30
            )
            response.raise_for_status()
            data = response.json()["data"]
            status = data.get("status", "")
            
            print(f"[NanaBanana] ⏳ PiAPI Task {task_id} | Status: {status} | {elapsed}s")

            if status == "completed":
                output = data.get("output", {})
                
                # 1. URL directe sans watermark
                video_url = output.get("video_url")
                
                # 2. works[0] fallbacks
                if not video_url:
                    works = output.get("works", [])
                    if works and len(works) > 0:
                        video_data = works[0].get("video", {})
                        # 2a. sans watermark dans works
                        video_url = video_data.get("resource_without_watermark")
                        # 2b. avec watermark (fallback)
                        if not video_url:
                            video_url = video_data.get("resource")

                if video_url:
                    return video_url
                    
                raise Exception(f"Task completed but no video URL in response: {data}")

            if status == "failed":
                error = data.get("error", {})
                raise Exception(f"PiAPI task failed: {error}")

            time.sleep(interval)
            elapsed += interval

        raise Exception(f"PiAPI task timeout after {max_wait}s. Task ID: {task_id}")

    def _tensor_to_base64(self, image_tensor):
        import numpy as np
        from PIL import Image
        import io

        if len(image_tensor.shape) == 4:
            img_np = image_tensor[0].cpu().numpy()
        else:
            img_np = image_tensor.cpu().numpy()

        img_np = (img_np * 255).clip(0, 255).astype(np.uint8)
        pil_img = Image.fromarray(img_np)

        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _file_to_base64(self, file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _download_video(self, url, output_path):
        print(f"[NanaBanana] ⬇️ Downloading final video to {output_path}...")
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"[NanaBanana] ✅ Video downloaded successfully!")
