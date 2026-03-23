from __future__ import annotations

import io
import os
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
    )
except ImportError:
    raise ImportError(
        "shared package not found. "
        "Make sure it is symlinked in custom_nodes/."
    )

AVAILABLE_MODELS = IMAGE_CAPABLE_MODELS


# ──────────────────────────────────────────────────────────────────────────────
# Node – Variant Director (NLP extraction for variant generation)
# ──────────────────────────────────────────────────────────────────────────────

class NanoBananaVariantDirector:
    """Constructs instructions for generating a variant of an existing image while preserving outfit and background."""
    DESCRIPTION = "Constructs instructions for generating a variant of an existing image while preserving outfit and background."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "gemini_config": ("GEMINI_CONFIG",),
                "natural_prompt": ("STRING", {"multiline": True, "default": "une photo d'elle en train de sauter avec un grand sourire"}),
                "photo_type": (["selfie", "third_person", "mirror"], {"default": "third_person"}),
                "modesty_level": (["low", "medium", "high"], {"default": "medium"}),
                "seed": ("INT", {"default": 1337}),
                "max_retries": ("INT", {"default": 5, "min": 1, "max": 15, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("system_instruction", "json_matrix")
    FUNCTION = "run"
    CATEGORY = "NanoBanana/Variant Workflow"

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

    def run(self, gemini_config: dict, natural_prompt: str, photo_type: str, modesty_level: str, seed: int, max_retries: int) -> tuple[str, str]:
        
        print(f"[NanoBananaVariantDirector] Running NLP on text: '{natural_prompt[:50]}...'")
        
        system_nlp = '''You extract Action and Expression from a user's creative direction text.

Rules:
- Action: the physical pose or movement described (e.g. "sitting on a chair", "walking", "leaning against a wall")
- Expression: the facial expression or mood (e.g. "smiling", "serious", "laughing")
- If the text is vague, infer the most likely action and expression from context
- NEVER return empty strings. If truly ambiguous, use "natural pose" for action and "neutral" for expression
- Always translate to English

Output format (strict JSON only):
{"action": "<action>", "expression": "<expression>"}

Examples:
Input: "dans une autre position"
Output: {"action": "different pose", "expression": "neutral"}

Input: "assise en train de rire"
Output: {"action": "sitting", "expression": "laughing"}

Input: "sexy sur un canapé"
Output: {"action": "lounging on a couch", "expression": "seductive"}

Input: "change"
Output: {"action": "natural pose", "expression": "neutral"}

Input: "debout bras croisés avec un regard sérieux"
Output: {"action": "standing with arms crossed", "expression": "serious"}'''
        
        contents = [
            f"SYSTEM INSTRUCTION: {system_nlp}",
            f"USER PROMPT: {natural_prompt}"
        ]
        
        action_prompt = "natural pose"
        expression_prompt = "neutral"
        
        # VariantDirector uses gemini-2.5-flash (text model for NLP)
        client, _ = create_gemini_client(gemini_config)

        config: dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": 0.2
        }
        
        response, status = call_with_retry(client, "gemini-2.5-flash", contents, config, max_retries)
        if response is None:
            print(f"[NanoBananaVariantDirector] ⚠ NLP Failed: {status}")
        else:
            try:
                text_result = getattr(response, 'text', None)
                if not text_result and getattr(response, 'candidates', None):
                    text_result = response.candidates[0].content.parts[0].text
                
                parsed = json.loads(text_result)
                action_prompt = parsed.get("action", action_prompt)
                expression_prompt = parsed.get("expression", expression_prompt)
                print(f"[NanoBananaVariantDirector] ✓ NLP Parsed: Action='{action_prompt}', Expression='{expression_prompt}'")
            except Exception as e:
                print(f"[NanoBananaVariantDirector] ⚠ Failed to parse NLP JSON: {e}")

        # Fallback guard: never allow empty strings
        if not action_prompt.strip():
            action_prompt = "natural pose"
            print(f"[NanoBananaVariantDirector] ⚠ NLP returned empty Action, using fallback: '{action_prompt}'")
        if not expression_prompt.strip():
            expression_prompt = "neutral"
            print(f"[NanoBananaVariantDirector] ⚠ NLP returned empty Expression, using fallback: '{expression_prompt}'")

        base_neg = (
            "blurry, deformed anatomy, extra fingers, mutated hands, "
            "AI generated, plastic skin, uncanny valley, over-processed, "
            "watermark, text, logo, body hair, arm hair, peach fuzz, "
            "flabby arms, thick arms, muscular arms, masculine body, masculine features, "
            "flat chest, hidden curves, shapeless body, stiff posture, boxy figure, unflattering angle, baggy clothes hiding body"
        )

        imperfections = self.generate_imperfections(seed)
        imperfectionText = f"\\n\\nIMPERFECTION LAYER (add these realistic details):\\n- " + "\\n- ".join(imperfections)

        system_instruction = f'''You are a master photorealistic image generator and variant creator.
Your task is to take a REFERENCE IMAGE and generate a seamless, highly realistic photographic variant of it based on the JSON directives.

CRITICAL RULES — ORDERED BY ABSOLUTE PRIORITY:
RULE #0 — SHARPNESS LOCK: DO NOT just copy the reference image literally. RE-RENDER the background, outfit, and textures with ultra-high frequency detail, pristine photographic sharpness, removing any source compression artifacts or blur.
RULE #1 — ENVIRONMENT LOCK: You MUST preserve the exact background, lighting, and environment from the reference image. Do NOT change where the subject is located.
RULE #2 — APPAREL LOCK: You MUST preserve the exact clothing, outfit, and accessories from the reference image. Do NOT change what the subject is wearing.
RULE #3 — IDENTITY LOCK: The generated person MUST match the provided identity locked exactly.
RULE #4 — ACTION AND EXPRESSION: Alter ONLY the subject's physical pose to match the "action" and face to match the "expression" defined in the JSON.
RULE #5 — NEGATIVE PROMPT: NEVER produce anything listed here: {base_neg}
{imperfectionText}'''
        
        if photo_type == "selfie":
            base_photo = "POV extreme close up selfie. The lens is near the person. DO NOT DRAW A PHONE."
        elif photo_type == "mirror":
            base_photo = "mirror selfie, the model is seen in a MIRROR REFLECTION."
        else:
            base_photo = "third person perspective. someone ELSE is taking the photo. NO phone visible in the frame."

        matrix = {
            "variant_generation_directives": {
                "photo_type_override": base_photo,
                "action": action_prompt.strip(),
                "expression": expression_prompt.strip(),
                "strict_preservation": "The outfit and the background environment MUST be identical to the reference image."
            },
            "subject": {
                "body_build": "elegant slender feminine model body, beautiful natural curves, delicate smooth arms, smooth skin, attractive alluring posture",
                "virtual_model_lock": "This is ALWAYS the exact same virtual model. Same face, same body proportions. NEVER change identity. Base identity purely on the provided reference image."
            },
            "directives": {
                "global_seed": seed,
                "modestyLevel": modesty_level
            }
        }
        
        json_matrix_str = json.dumps(matrix, indent=2)
        return (system_instruction, json_matrix_str)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()


# ──────────────────────────────────────────────────────────────────────────────
# Node – Variant API (Renderer)
# ──────────────────────────────────────────────────────────────────────────────
class NanoBananaVariantAPI:
    """Runs the Variant Generation heavily referencing a base image to change only pose/expression."""
    DESCRIPTION = "Runs the Variant Generation heavily referencing a base image to change only pose/expression."

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "gemini_config": ("GEMINI_CONFIG",),
                "image": ("IMAGE",),
                "system_instruction": ("STRING", {"multiline": True, "forceInput": True}),
                "json_matrix": ("STRING", {"multiline": True, "forceInput": True}),
                "aspect_ratio": (ASPECT_RATIOS,),
                "temperature": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 2.0, "step": 0.01}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "max_retries": ("INT", {"default": 5, "min": 1, "max": 15, "step": 1}),
                "batch_size": ("INT", {"default": 1, "min": 1, "max": 4, "step": 1}),
                "delay_between_calls": ("FLOAT", {"default": 3.0, "min": 0.0, "max": 15.0, "step": 0.5}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("variant_image", "status_message")
    FUNCTION = "run"
    CATEGORY = "NanoBanana/Variant Workflow"
    OUTPUT_NODE = False

    def run(
        self,
        gemini_config: dict,
        image: torch.Tensor,
        system_instruction: str,
        json_matrix: str,
        aspect_ratio: str,
        temperature: float,
        resolution: str = "1K",
        max_retries: int = 5,
        batch_size: int = 1,
        delay_between_calls: float = 3.0,
    ) -> tuple[torch.Tensor, str]:
        
        print(f"[NanoBananaVariantAPI] Generating {batch_size} variant image(s)...")

        client, model = create_gemini_client(gemini_config)

        pil_img = tensor_to_pil(image)
        img_byte_arr = io.BytesIO()
        pil_img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        sys_str = system_instruction.replace("\\n", "\n")
        json_mat_str = json_matrix.replace("\\n", "\n")
        
        base_contents = [
            "REFERENCE IMAGE: Maintain the exact same background environment, lighting, and outfit as this image. Apply the changes specified in the JSON matrix to pose and expression.",
            types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
            f"SYSTEM INSTRUCTIONS:\n{sys_str}\n\n"
        ]

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
                matrix_dict: dict[str, Any] = {"directives": {"global_seed": 1337}}
        except Exception as e:
            print(f"[NanoBananaVariantAPI] ⚠ Could not parse JSON Matrix: {e}")
            matrix_dict: dict[str, Any] = {"directives": {"global_seed": 1337}}

        for i in range(batch_size):
            if i > 0 and delay_between_calls > 0:
                print(f"[NanoBananaVariantAPI] Waiting {delay_between_calls}s before next call...")
                time.sleep(delay_between_calls)
            contents = list(base_contents)
            
            directives = matrix_dict.get("directives", {})
            if isinstance(directives, dict):
                current_seed = directives.get("global_seed", 1337) + i
            else:
                current_seed = 1337 + i
                
            if "directives" in matrix_dict and isinstance(matrix_dict["directives"], dict):
                matrix_dict["directives"]["global_seed"] = current_seed
                
            p_text = f"PROMPT MATRIX (Process this JSON strictly to generate the final image):\n{json.dumps(matrix_dict, indent=2)}"
            contents.append(p_text)

            print(f"[NanoBananaVariantAPI] Calling Gemini Vision... {i + 1}/{batch_size}")
            response, status_msg = call_with_retry(client, model, contents, config, max_retries)
            
            # API Fallback logic
            if response is None and status_msg and "SAFETY" in status_msg.upper():
                print(f"[NanoBananaVariantAPI] ⚠ Safety Block triggered! Initiating automatic fallback with high modesty...")
                if "directives" in matrix_dict and isinstance(matrix_dict["directives"], dict):
                    matrix_dict["directives"]["modestyLevel"] = "high"
                
                p_text_fallback = f"PROMPT MATRIX (Process this JSON strictly to generate the final image):\n{json.dumps(matrix_dict, indent=2)}"
                contents[-1] = p_text_fallback
                
                response, status_msg = call_with_retry(client, model, contents, config, max_retries)
            
            last_status_msg = status_msg

            if response is None:
                print(f"[NanoBananaVariantAPI] ⚠ API Error on image {i + 1}: {status_msg}")
                continue

            result_pil = extract_image_from_response(response)
            if result_pil is None:
                print(f"[NanoBananaVariantAPI] ⚠ No image in response {i + 1}.")
                continue

            print(f"[NanoBananaVariantAPI] ✓ Image {i + 1} Done — output size: {result_pil.size}")
            results.append(pil_to_tensor(result_pil))

            del result_pil
            del response

        gc.collect()

        if len(results) > 0:
            out_tensor = torch.cat(results, dim=0)
            return (out_tensor, last_status_msg)
        else:
            print("[NanoBananaVariantAPI] ⚠ No valid images generated. Returning fallback tensor.")
            return (image, last_status_msg)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
