import os
import time
import tempfile
import uuid

# Check for required google.genai SDK
try:
    import google.genai
    from google.genai import types
    _HAS_GENAI = True
except ImportError:
    print("[Omni_Veo] 🚨 ERROR: 'google-genai' library not found. Please run: pip install google-genai")
    _HAS_GENAI = False

from shared.gemini_client import create_gemini_client, tensor_to_pil


class Omni_Veo:
    """Omni node for generating video using Google's Veo 3.1 via google-genai API."""
    
    CATEGORY = "Omni"
    FUNCTION = "execute"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "gemini_config": ("GEMINI_CONFIG",),
                "prompt": ("STRING", {
                    "default": "Close-up selfie angle, subtle handheld micro-shaking throughout, looking directly at camera lens, talking with confidence, natural hand gestures while speaking, subtle head tilts, expressive eyebrows, natural daylight, parked car, stationary background, iPhone front camera quality, vertical video, ends with a brief confident silence looking at camera",
                    "multiline": True
                }),
                "negative_prompt": ("STRING", {
                    "default": "zoom in, zoom out, camera movement, driving, moving car, moving background, multiple people, blurry face, distorted face, morphing, text overlay, watermark",
                    "multiline": True
                }),
                "model": ([
                    "veo-3.1-generate-preview",
                    "veo-3.1-lite-generate-preview",
                    "veo-3.1-fast-generate-preview"
                ], {
                    "default": "veo-3.1-generate-preview"
                }),
                "aspect_ratio": (["9:16", "16:9", "1:1"], {
                    "default": "9:16"
                }),
                "resolution": (["720p", "1080p"], {
                    "default": "1080p"
                }),
                "duration": ("INT", {
                    "default": 8, "min": 5, "max": 8,
                    "tooltip": "Durée cible en secondes. Veo supporte 4 à 8s maximum."
                }),
                "enable_audio": ("BOOLEAN", {
                    "default": True
                }),
            },
            "optional": {
                "output_folder": ("STRING", {"forceInput": True}),
                "video_filename": ("STRING", {"forceInput": True}),
                "speech_text": ("STRING", {"forceInput": True}),
                "skip_trigger": ("STRING", {"forceInput": True})
            }
        }

    def execute(self, image, gemini_config, prompt, negative_prompt, output_folder="", video_filename="",
                model="veo-3.1-generate-preview", aspect_ratio="9:16", resolution="1080p", duration=8, enable_audio=True,
                speech_text="", skip_trigger=""):
        
        if skip_trigger and skip_trigger.strip().upper().startswith("FAIL"):
            print(f"[Omni_Veo] 🛑 Execution skipped due to upstream FAIL trigger: {skip_trigger.strip()}")
            return ("",)
        
        if not _HAS_GENAI:
            print("[Omni_Veo] 🚨 ERROR: 'google-genai' library not installed.")
            return ("",)

        # Build final path
        output_dir_clean = output_folder.strip() if output_folder else "/tmp"
        # Ensure output directory exists
        os.makedirs(output_dir_clean, exist_ok=True)
        
        if video_filename and video_filename.strip():
            safe_stem = video_filename.strip()
            output_path = os.path.join(output_dir_clean, f"{safe_stem}_veo.mp4")
        else:
            unique_id = f"veo_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            output_path = os.path.join(output_dir_clean, f"{unique_id}.mp4")

        temp_img_path = None
        
        try:
            # 1. Init Client
            print(f"[Omni_Veo] 🔄 Initializing Google GenAI Client...")
            client = create_gemini_client(gemini_config)

            # 2. Conversion tensor → fichier temporaire PNG
            pil_image = tensor_to_pil(image)
            temp_img_path = os.path.join(output_dir_clean, f"temp_veo_input_{uuid.uuid4().hex[:6]}.png")
            pil_image.save(temp_img_path)

            # 3. Préparer l'objet Image
            with open(temp_img_path, "rb") as f:
                img_bytes = f.read()
            veo_image = types.Image(image_bytes=img_bytes, mime_type="image/png")
            print(f"[Omni_Veo] 📤 Image loaded into memory (Size: {len(img_bytes)} bytes)")

            # 4. Construction du prompt final
            final_prompt = prompt.strip()
                
            if enable_audio and speech_text and speech_text.strip():
                final_prompt += f'\n\nThe person is talking directly to the viewer. They say exactly this:\n"{speech_text.strip()}"'
                print(f"[Omni_Veo] 🎙️ Speech injected into prompt ({len(speech_text.split())} words) - Note: native generate_audio disabled due to API limits.")

            # 5. Configuration Veo (CRITIQUE)
            safe_duration = max(4, min(8, int(duration)))
            if safe_duration != int(duration):
                print(f"[Omni_Veo] ℹ️ Duration clamped from {duration}s to {safe_duration}s (API limit)")

            config = types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                duration_seconds=safe_duration,
                person_generation="ALLOW_ADULT",  # Absolument obligatoire sinon refus !
                number_of_videos=1,
            )
            
            if negative_prompt and negative_prompt.strip():
                config.negative_prompt = negative_prompt.strip()

            print(f"[Omni_Veo] 🚀 Submitting to {model}...")
            operation = client.models.generate_videos(
                model=model,
                prompt=final_prompt,
                image=veo_image,
                config=config,
            )
            print(f"[Omni_Veo] 🚀 Video generation started: {operation.name}")

            # 7. Polling (Long Running Operation)
            timeout = 600  # 10 minutes max
            poll_interval = 15
            elapsed = 0

            while not operation.done:
                if elapsed >= timeout:
                    raise TimeoutError(f"Timeout after {timeout}s")
                time.sleep(poll_interval)
                elapsed += poll_interval
                operation = client.operations.get(operation)
                
                status_str = getattr(operation, "status", getattr(operation, "state", "processing"))
                print(f"[Omni_Veo] ⏳ {operation.name} | {status_str} | {elapsed}s")

            # Check operation errors
            if hasattr(operation, "error") and operation.error:
                raise Exception(f"Operation failed: {operation.error}")

            # 8. Téléchargement de la vidéo
            if hasattr(operation.result, "generated_videos") and len(operation.result.generated_videos) > 0:
                video_obj = operation.result.generated_videos[0]
                
                if hasattr(video_obj, "video") and hasattr(video_obj.video, "uri"):
                    video_uri = video_obj.video.uri
                    video_data = client.files.download(file=video_uri)
                    
                    with open(output_path, "wb") as f:
                        f.write(video_data)
                    print(f"[Omni_Veo] ✅ Done → {output_path}")
                else:
                    raise Exception("No video URI in generated_videos response")
            else:
                raise Exception("result.generated_videos is empty or missing")

            return (output_path,)

        except Exception as e:
            err_msg = str(e).lower()
            if "unexpected keyword argument" in err_msg:
                print(f"[Omni_Veo] 🚨 TypeError / SDK API Mismatch: {e}")
            elif "403" in err_msg or "permission" in err_msg:
                print("[Omni_Veo] 🚨 Google API Error: Model not found or not allowlisted. Check your Google AI Studio access.")
            elif "safety" in err_msg or "block" in err_msg or "policy" in err_msg:
                print(f"[Omni_Veo] 🚨 Content violation / Safety Block: Try a different image or prompt. ({e})")
            else:
                print(f"[Omni_Veo] 🚨 Execution Failed: {e}")
            return ("",)

        finally:
            # 9. Cleanup
            
            # Clean up the local temp image
            if temp_img_path and os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass

NODE_CLASS_MAPPINGS = {"Omni_Veo": Omni_Veo}
NODE_DISPLAY_NAME_MAPPINGS = {"Omni_Veo": "Omni_Veo"}
