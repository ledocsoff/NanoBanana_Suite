from __future__ import annotations

import io
import os
import re
import json
import gc
import time
from typing import Any

import torch
from PIL import Image
from google import genai
from google.genai import types

import sys
_custom_nodes_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _custom_nodes_dir not in sys.path:
    sys.path.insert(0, _custom_nodes_dir)

try:
    from shared.gemini_client import (
        IMAGE_CAPABLE_MODELS,
        ASPECT_RATIOS,
        create_gemini_client,
        call_with_retry,
        extract_image_from_response,
        tensor_to_pil,
        pil_to_tensor,
        TEXT_MODELS,
    )
except ImportError:
    raise ImportError(
        "shared package not found. "
        "Make sure it is symlinked in custom_nodes/."
    )

AVAILABLE_MODELS = IMAGE_CAPABLE_MODELS


# ──────────────────────────────────────────────────────────────────────────────
# Node – AI Director (NLP extraction via Gemini 2.5 Flash)
# ──────────────────────────────────────────────────────────────────────────────

class OmniAIDirector:
    """Extracts location, apparel, and photo_type from a natural language prompt using Gemini 2.5 Flash."""
    DESCRIPTION = "Extracts location, apparel, and photo_type from a natural language prompt using Gemini."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "gemini_config": ("GEMINI_CONFIG",),
                "model": (TEXT_MODELS, {"default": "gemini-2.5-flash"}),
                "natural_prompt": ("STRING", {"multiline": True, "default": "une photo d'elle sur une plage avec un bikini rouge et un chapeau"}),
                "photo_type": (["selfie", "third_person", "mirror"], {"default": "third_person"}),
                "max_retries": ("INT", {"default": 5, "min": 1, "max": 15, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("location", "apparel", "photo_type")
    FUNCTION = "run"
    CATEGORY = "Omni/Matrix Core"

    def run(self, gemini_config: dict, natural_prompt: str, photo_type: str, max_retries: int, model: str = "gemini-2.5-flash") -> tuple[str, str, str]:
        print(f"[OmniAIDirector] Running NLP on text with {model}: '{natural_prompt[:50]}...'")
        
        system_instruction = '''You are an expert AI photo director. The user provides a natural language description (often French or English) of a photo they want.
Extract the "location" (which MUST include the environment, lighting, subject's pose, and action) and "apparel".
Translate them to English. 

Output JSON EXACTLY in this format:
{
  "location": "english translation of the environment, lighting, subject's physical pose, and any action they are doing",
  "apparel": "english translation of the clothing"
}
Output ONLY valid JSON.'''
        
        contents = [
            f"SYSTEM INSTRUCTION: {system_instruction}",
            f"USER PROMPT: {natural_prompt}"
        ]
        
        # AIDirector uses gemini-2.5-flash (text model for NLP), not image models
        # We still use the GeminiConfig for client creation (provider/auth)
        client = create_gemini_client(gemini_config)

        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
        
        response, status = call_with_retry(client, model, contents, config, max_retries)
        if response is None:
            print(f"[OmniAIDirector] ⚠ AI Director NLP Failed: {status}")
            return ("", "", photo_type)
            
        try:
            text_result = getattr(response, 'text', None)
            if not text_result and getattr(response, 'candidates', None):
                text_result = response.candidates[0].content.parts[0].text
            
            parsed = json.loads(text_result)
            loc = parsed.get("location", "")
            app = parsed.get("apparel", "")
            
            print(f"[OmniAIDirector] ✓ NLP Parsed successfully.")
            return (loc, app, photo_type)
        except Exception as e:
            print(f"[OmniAIDirector] ⚠ Failed to parse NLP JSON: {e}")
            return ("", "", photo_type)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()



# ──────────────────────────────────────────────────────────────────────────────
# Node – Matrix Builder
# ──────────────────────────────────────────────────────────────────────────────
class OmniMatrixBuilder:
    """Constructs the sophisticated JSON Matrix and Imperfection layers for Gemini."""
    DESCRIPTION = "Constructs the sophisticated JSON Matrix and Imperfection layers for Gemini."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "location": ("STRING", {"forceInput": True}),
                "apparel": ("STRING", {"forceInput": True}),
                "photo_type": ("STRING", {"forceInput": True}),
                "modesty_level": (["low", "medium", "high"], {"default": "medium"}),
                "seed": ("INT", {"default": 1337}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("system_instruction", "json_matrix")
    FUNCTION = "run"
    CATEGORY = "Omni/Matrix Core"

    def generate_imperfections(self, seed: int) -> list[str]:
        full_imperfections = [
            'Slight phone shadow visible on the ground or wall',
            'Minor lens flare from sun or light source',
            'Slightly warm white balance, like an old iPhone',
            'Subject slightly off-center in frame',
            'One strand of hair out of place',
            'Photo slightly tilted 1-2 degrees',
            'Subtle motion blur on one hand',
            'Slightly overexposed highlights on skin',
            'Background object partially cut off by frame edge',
            'Natural skin imperfection visible (freckle, small mark)',
            'Slight 1-2° camera tilt like real hand-held iPhone',
            'Subtle digital grain and noise typical of iPhone 15 Pro sensor',
            'Flyaway hair strands or slightly messy hair',
            'Visible goosebumps or natural skin texture variation',
        ]
        idx1 = (seed * 13) % len(full_imperfections)
        idx2 = (seed * 17) % len(full_imperfections)
        idx3 = (seed * 19) % len(full_imperfections)
        
        res = list(set([full_imperfections[idx1], full_imperfections[idx2], full_imperfections[idx3]]))
        
        idx = seed
        while len(res) < 3:
            item = full_imperfections[idx % len(full_imperfections)]
            if item not in res:
                res.append(item)
            idx += 1
            
        return res[:3]

    def run(self, location: str, apparel: str, photo_type: str, modesty_level: str, seed: int) -> tuple[str, str]:
        
        # Cloaking logic (internalized)
        swaps = [
            (r'(?i)\b(bikini|bikinis|maillot de bain|maillots de bain)\b', "minimal athletic coastal two-piece swimwear"),
            (r'(?i)\b(micro-bikini|micro bikini)\b', "minimal athletic coastal two-piece swimwear with string ties"),
            (r'(?i)\b(lingerie|sous-vêtements|sous-vetements|underwear)\b', "delicate sheer layered intimate casual apparel"),
            (r'(?i)\b(nu|nue|naked|nude|topless|poitrine nue)\b', "wearing a very short cropped atmospheric top"),
            (r'(?i)\b(sexy|provocant|hot)\b', "confident, self-assured, high-fashion"),
            (r'(?i)\b(décolleté|cleavage)\b', "v-neckline accentuating the natural silhouette"),
            (r'(?i)\b(underboob)\b', "cropped comfortable fit"),
            (r'(?i)\b(micro)\b', "minimalist"),
            (r'(?i)\b(sheer)\b', "delicate sheer layers"),
            (r'(?i)\b(wet look)\b', "glowing damp texture"),
            (r'(?i)\b(string ties)\b', "thin straps"),
            (r'(?i)\b(high-cut|high cut)\b', "athletic waist line cut"),
            (r'(?i)\b(bralette)\b', "casual lounge top"),
            (r'(?i)\b(damp hair from ocean|wet hair)\b', "slicked back beach hair"),
            (r'(?i)\b(ass|booty|fesses)\b', "athletic glute profile"),
        ]
        
        safe_apparel = apparel if apparel else ""
        if safe_apparel:
            for pattern, replacement in swaps:
                safe_apparel = re.sub(pattern, replacement, safe_apparel)
        
        if photo_type and photo_type.strip() in ["selfie", "third_person", "mirror"]:
            photo_type = photo_type.strip()
        else:
            photo_type = "third_person"

        base_neg = (
            "blurry, deformed anatomy, extra fingers, mutated hands, "
            "AI generated, plastic skin, uncanny valley, over-processed, "
            "watermark, text, logo, body hair, arm hair, peach fuzz, "
            "flabby arms, thick arms, muscular arms, masculine body, masculine features, "
            "flat chest, hidden curves, shapeless body, stiff posture, boxy figure, unflattering angle, baggy clothes hiding body"
        )

        imperfections = self.generate_imperfections(seed)
        imperfectionText = f"\\n\\nIMPERFECTION LAYER (add these realistic details):\\n- " + "\\n- ".join(imperfections)

        system_instruction = f'''You are a master photorealistic image generator. Your task is to perfectly transpose the subject from the REFERENCE IMAGE into the environment requested by the JSON Matrix.

CRITICAL IDENTITY RULES:
- The REFERENCE IMAGE is the sole and absolute visual identity reference.
- You must generate a photorealistic photo of this EXACT person.
- Do not invent a new face. Do not blend identities. Do not stylize.
- Integrate the person naturally into the environment described in the JSON Matrix.

NEGATIVES: {base_neg}
{imperfectionText}'''
        
        if photo_type == "selfie":
            base_photo = "POV extreme close up selfie. The lens is near the person. DO NOT DRAW A PHONE."
        elif photo_type == "mirror":
            base_photo = "mirror selfie, the model is seen in a MIRROR REFLECTION."
        else:
            base_photo = "third person perspective. someone ELSE is taking the photo. NO phone visible in the frame."

        matrix = {
            "photo_type": base_photo,
            "subject": {
                "apparel": safe_apparel,
                "body_build": "elegant slender feminine model body, beautiful natural curves, delicate smooth arms, smooth skin, attractive alluring posture",
                "virtual_model_lock": "ABSOLUTE CLONE. Replicate the face from the reference image exactly."
            },
            "environment": {
                "location_and_lighting": location
            },
            "directives": {
                "global_seed": seed,
                "modestyLevel": modesty_level
            }
        }
        
        json_matrix_str = json.dumps(matrix, indent=2)
        return (system_instruction, json_matrix_str)


# ──────────────────────────────────────────────────────────────────────────────
# Node – Vision API (Renderer)
# ──────────────────────────────────────────────────────────────────────────────
class OmniVisionAPI:
    """Runs the heavy Image Generation via Gemini Vision, with auto-scaling and safety fallback."""
    DESCRIPTION = "Runs the heavy Image Generation via Gemini Vision, with auto-scaling and safety fallback."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "gemini_config": ("GEMINI_CONFIG",),
                "model": (IMAGE_CAPABLE_MODELS, {"default": "gemini-3-pro-image-preview"}),
                "system_instruction": ("STRING", {"multiline": True, "forceInput": True}),
                "json_matrix": ("STRING", {"multiline": True, "forceInput": True}),
                "aspect_ratio": (ASPECT_RATIOS,),
                "temperature": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 2.0, "step": 0.01}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "max_retries": ("INT", {"default": 5, "min": 1, "max": 15, "step": 1}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
                "delay_between_calls": ("FLOAT", {"default": 3.0, "min": 0.0, "max": 900.0, "step": 0.5}),
            },
            "optional": {
                "image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("generated_image", "status_message")
    FUNCTION = "run"
    CATEGORY = "Omni/Matrix Core"
    OUTPUT_NODE = False

    def run(
        self,
        gemini_config: dict,
        system_instruction: str,
        json_matrix: str,
        aspect_ratio: str,
        temperature: float,
        resolution: str = "1K",
        max_retries: int = 5,
        batch_size: int = 1,
        delay_between_calls: float = 3.0,
        model: str = "gemini-3-pro-image-preview",
        image: torch.Tensor = None,
    ) -> tuple[torch.Tensor, str]:
        
        print(f"[OmniVisionAPI] Generating {batch_size} image(s) with {model}...")

        client = create_gemini_client(gemini_config)

        contents = []
        
        if image is not None:
            pil_img = tensor_to_pil(image)
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            contents.append("REFERENCE IMAGE (Full visual identity reference including face, hairstyle, hair texture, and overall appearance):")
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))

        sys_str = system_instruction.replace("\\n", "\n")
        json_mat_str = json_matrix.replace("\\n", "\n")

        contents.extend([
            f"SYSTEM INSTRUCTIONS:\n{sys_str}\n\n",
            f"PROMPT MATRIX (Process this JSON strictly to generate the final image):\n{json_mat_str}"
        ])

        config: dict[str, Any] = {
            "response_modalities": ["IMAGE"],
            "temperature": float(temperature),
        }
        img_cfg = {"image_size": resolution}
        if aspect_ratio.upper() not in ("AUTO", ""):
            img_cfg["aspect_ratio"] = aspect_ratio
        config["image_config"] = img_cfg

        results = []
        last_status_msg = "Success"
        
        try:
            parsed = json.loads(json_mat_str)
            if isinstance(parsed, dict):
                matrix_dict: dict[str, Any] = parsed
            else:
                matrix_dict: dict[str, Any] = {"directives": {"global_seed": 1337}, "subject": {"apparel": "unknown"}}
        except Exception as e:
            print(f"[OmniVisionAPI] ⚠ Could not parse JSON Matrix: {e}")
            matrix_dict: dict[str, Any] = {"directives": {"global_seed": 1337}, "subject": {"apparel": "unknown"}}

        for i in range(batch_size):
            if i > 0 and delay_between_calls > 0:
                print(f"[OmniVisionAPI] Waiting {delay_between_calls}s before next call...")
                time.sleep(delay_between_calls)
            directives = matrix_dict.get("directives", {})
            if isinstance(directives, dict):
                current_seed = directives.get("global_seed", 1337) + i
            else:
                current_seed = 1337 + i
                
            if i > 0:
                if "directives" in matrix_dict and isinstance(matrix_dict["directives"], dict):
                    matrix_dict["directives"]["global_seed"] = current_seed
                p_text = f"PROMPT MATRIX (Process this JSON strictly to generate the final image):\n{json.dumps(matrix_dict, indent=2)}"
                
                if len(contents) > 0:
                    contents[len(contents)-1] = p_text

            print(f"[OmniVisionAPI] Calling Gemini Vision... {i + 1}/{batch_size}")
            response, status_msg = call_with_retry(client, model, contents, config, max_retries)
            
            # API Fallback logic (Amelioration 2 & 3)
            if response is None and status_msg and "SAFETY" in status_msg.upper():
                print(f"[OmniVisionAPI] ⚠ Safety Block triggered! Initiating automatic fallback with high modesty...")
                if "directives" in matrix_dict and isinstance(matrix_dict["directives"], dict):
                    matrix_dict["directives"]["modestyLevel"] = "high"
                if "subject" in matrix_dict and isinstance(matrix_dict["subject"], dict):
                    matrix_dict["subject"]["apparel"] = "modest high-neck athletic wear, long sleeves, full coverage"
                p_text = f"PROMPT MATRIX (Process this JSON strictly to generate the final image):\n{json.dumps(matrix_dict, indent=2)}"
                
                if len(contents) > 0:
                    contents[len(contents)-1] = p_text
                
                response, status_msg = call_with_retry(client, model, contents, config, max_retries)
            
            last_status_msg = status_msg

            if response is None:
                print(f"[OmniVisionAPI] ⚠ API Error on image {i + 1}: {status_msg}")
                continue

            result_pil = extract_image_from_response(response)
            if result_pil is None:
                print(f"[OmniVisionAPI] ⚠ No image in response {i + 1}.")
                continue

            print(f"[OmniVisionAPI] ✓ Image {i + 1} Done — output size: {result_pil.size}")
            results.append(pil_to_tensor(result_pil))

            del result_pil
            del response

        gc.collect()

        if len(results) > 0:
            out_tensor = torch.cat(results, dim=0)
            return (out_tensor, last_status_msg)
        else:
            print("[OmniVisionAPI] ⚠ No valid images generated. Returning blank tensor.")
            blank = torch.zeros((1, 512, 512, 3), dtype=torch.float32)
            return (blank, last_status_msg)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
