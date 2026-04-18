import requests
import base64
import time
import os
import json


class Omni_PiAPIKlingOmni:
    """Kling Image-to-Video via PiAPI (task_type: video_generation).
    Supports Kling 2.6 (silent) and Kling 3.0 (with optional native audio).
    When enable_audio is True + speech_text is provided, Kling 3.0 generates
    a talking-head video with synchronized voice in a single API call."""

    CATEGORY = "Omni/API"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "status_message")
    FUNCTION = "generate"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "auth": ("PIAPI_AUTH",),
                "image": ("IMAGE",),
                "output_folder": ("STRING", {"forceInput": True}),
                "video_filename": ("STRING", {"forceInput": True}),
                "prompt": ("STRING", {
                    "default": "Close-up selfie angle, static camera, looking directly at camera lens, talking with confidence, subtle head tilts, expressive eyebrows, natural daylight, iPhone front camera quality, vertical video",
                    "multiline": True,
                    "tooltip": "Visual description of the scene. Describes framing, mood, and action ONLY. Never describe physical appearance — that comes from the source image. Max 2500 chars."
                }),
                "version": (["3.0", "2.6"], {"default": "3.0"}),
                "mode": (["720p", "1080p"], {
                    "default": "720p",
                    "tooltip": "720p (Standard Kling). 1080p (Pro Kling, costs ~50% more)."
                }),
                "duration": ("INT", {
                    "default": 5, "min": 1, "max": 20, "step": 1,
                    "tooltip": "Video duration in seconds. Note: standard Kling accepts 5s or 10s. Pro/3.0 may accept custom."
                }),
                "aspect_ratio": (["9:16", "16:9", "1:1"], {
                    "default": "9:16",
                    "tooltip": "9:16 = vertical (TikTok/Reels). 16:9 = landscape. 1:1 = square."
                }),
                "cfg_scale": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": "How closely the output follows the prompt. 0.5 recommended."
                }),
                "enable_audio": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Enable Kling 3.0 native audio generation. Requires version 3.0. Adds ~$0.05/s to cost."
                }),
            },
            "optional": {
                "speech_text": ("STRING", {
                    "forceInput": True,
                    "tooltip": "Dialogue script from Generic AI Generator. Only used when enable_audio=True."
                }),
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "What to avoid in the generated video."
                }),
                "poll_interval": ("INT", {"default": 10, "min": 5, "max": 60, "step": 1}),
                "max_poll_time": ("INT", {"default": 600, "min": 60, "max": 1800, "step": 10}),
                "skip_trigger": ("STRING", {"forceInput": True, "tooltip": "Connect status_message from upstream nodes. If it starts with FAIL, the node skips execution."}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def _build_final_prompt(self, prompt, enable_audio, speech_text):
        """Compose the final prompt: visual description + optional speech injection."""
        final = prompt.strip()
        if enable_audio and speech_text and speech_text.strip():
            final += f'\n\nThe person is talking directly to the viewer. They say exactly this:\n"{speech_text.strip()}"'
            print(f"[Omni_KlingI2V] 🎙️ Audio enabled — speech injected ({len(speech_text.split())} words)")
        return final[:2500]

    def generate(self, auth, image, output_folder, video_filename, prompt,
                 version, mode, duration, aspect_ratio, cfg_scale, enable_audio,
                 speech_text="", negative_prompt="",
                 poll_interval=10, max_poll_time=600, skip_trigger=""):

        if skip_trigger and skip_trigger.strip().upper().startswith("FAIL"):
            print(f"[Omni_KlingI2V] 🛑 Execution skipped due to upstream FAIL trigger: {skip_trigger.strip()}")
            return ("", "", f"SKIP: {skip_trigger.strip()}")

        # Guard: empty image (upstream skip / QualityGate FAIL)
        if image is None or image.max().item() == 0:
            print("[Omni_KlingI2V] ⚠️ Empty image received. Skipping.")
            return ("", "", "SKIP: empty image")

        # Guard: empty prompt
        if not prompt or not prompt.strip():
            return ("", "", "ERROR: prompt is required for I2V")

        # Guard: audio requested with Kling 2.6
        if enable_audio and version == "2.6":
            print("[Omni_KlingI2V] ⚠️ Native audio requires Kling 3.0. Forcing version to 3.0.")
            version = "3.0"

        final_prompt = self._build_final_prompt(prompt, enable_audio, speech_text)

        try:
            # 1. Upload image
            print("[Omni_KlingI2V] 📤 Uploading image to PiAPI...")
            image_b64 = self._tensor_to_base64(image)
            image_url = self._upload_file(auth, f"{video_filename}_i2v.png", image_b64)

            kling_mode = "std" if mode == "720p" else "pro"
            audio_label = " + 🎙️ AUDIO" if enable_audio else ""
            print(f"[Omni_KlingI2V] 🚀 Submitting I2V task (Kling {version} {kling_mode}, {duration}s, {aspect_ratio}{audio_label})...")

            input_data = {
                "image_url": image_url,
                "prompt": final_prompt,
                "negative_prompt": negative_prompt.strip()[:2500] if negative_prompt else "",
                "cfg_scale": float(cfg_scale),
                "duration": int(duration),
                "aspect_ratio": aspect_ratio,
                "mode": kling_mode,
                "version": version,
            }

            if enable_audio:
                input_data["enable_audio"] = True

            service_mode = auth.get("service_mode", "")

            payload = {
                "model": "kling",
                "task_type": "video_generation",
                "input": input_data,
                "config": {
                    "service_mode": service_mode,
                    "webhook_config": {
                        "endpoint": "",
                        "secret": ""
                    }
                }
            }

            print(f"\n[Omni_KlingI2V] 📋 PiAPI Payload:\n{json.dumps(payload, indent=2)}")

            # 3. Submit task (with HYA→public fallback for audio)
            task_id = self._submit_with_fallback(auth, payload, service_mode, enable_audio)

            # 4. Poll
            video_url = self._poll_task(auth, task_id, max_wait=max_poll_time, interval=poll_interval)

            # 5. Download
            os.makedirs(output_folder, exist_ok=True)
            output_path = os.path.join(output_folder, f"{video_filename}_i2v.mp4")
            self._download_video(video_url, output_path)

            print(f"[Omni_KlingI2V] ✅ Done → {output_path}")
            return (output_path, video_url, "OK")

        except Exception as e:
            print(f"[Omni_KlingI2V] 🚨 ERROR: {e}")
            return ("", "", f"ERROR: {e}")

    def _submit_with_fallback(self, auth, payload, original_service_mode, enable_audio):
        """Submit task to PiAPI. If audio fails on HYA, fallback to public mode with explicit warning."""
        response = requests.post(
            f"{auth['base_url']}/task",
            headers=auth["headers"],
            json=payload,
            timeout=30
        )

        # If request failed AND audio is enabled AND we were using HYA → try public fallback
        if response.status_code != 200 and enable_audio and original_service_mode != "public":
            error_text = response.text.lower()
            if "audio" in error_text or response.status_code in (400, 422):
                print("[Omni_KlingI2V] ⚠️⚠️⚠️ HYA mode rejected audio request.")
                print("[Omni_KlingI2V] 💰 FALLBACK → Retrying with service_mode='public' (PAY-AS-YOU-GO — higher cost!)")
                payload["config"]["service_mode"] = "public"
                response = requests.post(
                    f"{auth['base_url']}/task",
                    headers=auth["headers"],
                    json=payload,
                    timeout=30
                )

        if response.status_code != 200:
            print(f"[Omni_KlingI2V] 🚨 PiAPI Error {response.status_code}: {response.text}")

        response.raise_for_status()
        task_data = response.json()

        if task_data.get("code") != 200:
            raise Exception(f"PiAPI task creation failed: {task_data}")

        return task_data["data"]["task_id"]

    # ── Helpers (same proven pattern as MC node) ──────────────────────────────

    def _upload_file(self, auth, file_name, file_data_b64):
        for retry in range(3):
            try:
                response = requests.post(
                    auth["upload_url"],
                    headers=auth["headers"],
                    json={"file_name": file_name, "file_data": file_data_b64},
                    timeout=120
                )
                response.raise_for_status()
                result = response.json()
                if result.get("code") != 200:
                    raise Exception(f"PiAPI upload failed: {result}")
                return result["data"]["url"]
            except Exception as e:
                print(f"[Omni_KlingI2V] Upload retry {retry+1}/3: {e}")
                time.sleep(5)
        raise Exception("Upload failed after 3 retries.")

    def _poll_task(self, auth, task_id, max_wait=600, interval=10):
        elapsed = 0
        while elapsed < max_wait:
            response = requests.get(
                f"{auth['base_url']}/task/{task_id}",
                headers=auth["headers"],
                timeout=30
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            status = data.get("status", "")

            print(f"[Omni_KlingI2V] ⏳ Task {task_id} | {status} | {elapsed}s")

            if status == "completed":
                output = data.get("output", {})
                video_url = output.get("video_url") or output.get("video")
                if not video_url:
                    works = output.get("works", [])
                    if works:
                        video_data = works[0].get("video", {})
                        video_url = video_data.get("resource_without_watermark") or video_data.get("resource")
                if video_url:
                    return video_url
                raise Exception(f"Completed but no video URL: {output}")

            if status == "failed":
                raise Exception(f"Task failed: {data.get('error', {})}")

            time.sleep(interval)
            elapsed += interval

        raise Exception(f"Timeout after {max_wait}s. task_id: {task_id}")

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

    def _download_video(self, url, output_path):
        for retry in range(3):
            try:
                print(f"[Omni_KlingI2V] ⬇️ Download attempt {retry+1}...")
                response = requests.get(url, stream=True, timeout=120)
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return
            except Exception as e:
                print(f"[Omni_KlingI2V] DL failed: {e}")
                time.sleep(2)
        raise Exception("Download failed after 3 retries.")


NODE_CLASS_MAPPINGS = {"Omni_PiAPIKlingOmni": Omni_PiAPIKlingOmni}
NODE_DISPLAY_NAME_MAPPINGS = {"Omni_PiAPIKlingOmni": "🎬 PiAPI Kling Omni"}
