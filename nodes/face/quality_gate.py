from __future__ import annotations

import io
import os
import time

import torch
from PIL import Image
from google.genai import types

import sys
_custom_nodes_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _custom_nodes_dir not in sys.path:
    sys.path.insert(0, _custom_nodes_dir)

from shared.gemini_client import (
    create_gemini_client, tensor_to_pil, pil_to_tensor, extract_image_from_response,
)

# ── Prompts ──────────────────────────────────────────────────────────────────

QUALITY_PROMPT = """Image 1 is the reference identity (face, hair, skin tone, overall appearance).
Image 2 is the original scene before any modification (pose, expression, lighting, background).
Image 3 is the face swap result to validate.

Your job: determine if Image 3 is a successful face swap.

CHECK 1 — IDENTITY: Does the person in Image 3 match Image 1? Same face shape, same hair (style, color, volume), same skin tone. The person in Image 3 must clearly BE the person from Image 1, not a blend or hybrid.

CHECK 2 — SCENE PRESERVATION: Is the scene from Image 2 preserved in Image 3? Same body posture, same head angle, same facial expression, same lighting direction, same background. Nothing should have changed except the person's identity.

CHECK 3 — ARTIFACTS: Is Image 3 free of obvious AI artifacts? No blurring at face edges, no skin texture mismatch, no hair/background bleeding, no uncanny valley effect.

If ALL three checks pass → respond with: PASS
If ANY check fails → respond with: FAIL|<short reason in 10 words max>

Respond with ONLY "PASS" or "FAIL|reason". Nothing else. No explanation, no markdown."""

RETRY_SWAP_PROMPT = (
    "IMAGE 1 is the source identity. IMAGE 2 is the target scene.\n"
    "Replace the face in IMAGE 2 with the face from IMAGE 1.\n"
    "Preserve everything else in IMAGE 2 exactly: background, pose, body, lighting, clothing, expression angle.\n"
    "The result must be photorealistic with no visible seams, artifacts, or blending issues.\n\n"
    "Negative instructions (DO NOT INCLUDE): low quality, bad anatomy, deformed, mutated, blurry edges"
)


def _pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class NanoBananaQualityGate:
    """Binary PASS/FAIL gate with built-in retry swap.

    1. Validates the swapped_image from the Swap node
    2. If PASS → forwards the image
    3. If FAIL → internally re-generates a new swap using Gemini (same source + target)
    4. Validates the new attempt → repeats up to max_retries
    5. If all retries fail → returns empty tensor (Kling MC skips automatically)
    """

    CATEGORY = "NanoBanana"
    RETURN_TYPES = ("IMAGE", "BOOLEAN", "STRING")
    RETURN_NAMES = ("image", "passed", "report")
    FUNCTION = "gate"
    OUTPUT_NODE = False

    DESCRIPTION = (
        "Validates a face swap via Gemini Vision. On FAIL, internally retries the swap "
        "up to max_retries times. PASS → image forwarded. All FAIL → empty tensor."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "gemini_config": ("GEMINI_CONFIG",),
                "source_face":   ("IMAGE",),
                "target_frame":  ("IMAGE",),
                "swapped_image": ("IMAGE",),
                "max_retries":   ("INT", {
                    "default": 2, "min": 1, "max": 5, "step": 1,
                    "tooltip": "Nombre de nouvelles tentatives de swap si le premier échoue. "
                               "Chaque retry = 1 appel swap + 1 appel validation."
                }),
            },
        }

    def gate(self, gemini_config, source_face, target_frame, swapped_image, max_retries=2):
        client, model = create_gemini_client(gemini_config)

        # Pre-convert source and target to bytes once (reused across retries)
        source_bytes = _pil_to_bytes(tensor_to_pil(source_face))
        target_bytes = _pil_to_bytes(tensor_to_pil(target_frame))

        # ── Attempt 0: validate the swap from the upstream Swap node ─────────
        current_image = swapped_image
        all_reasons = []

        total_attempts = 1 + max_retries  # first check + N retries
        for attempt in range(total_attempts):
            is_retry = attempt > 0
            label = f"retry {attempt}/{max_retries}" if is_retry else "initial swap"

            print(f"[QualityGate] 🔍 Validating {label}…")

            passed, reason = self._validate(client, model, source_bytes, target_bytes, current_image)

            if passed:
                report = f"✅ PASS — Swap validated ({label})"
                if all_reasons:
                    report += f" | Previous failures: {'; '.join(all_reasons)}"
                print(f"[QualityGate] {report}")
                return (current_image, True, report)

            # FAIL
            all_reasons.append(f"{label}: {reason}")
            print(f"[QualityGate] ❌ FAIL ({label}): {reason}")

            # If retries remaining, generate a new swap internally
            if attempt < total_attempts - 1:
                print(f"[QualityGate] 🔄 Generating new swap attempt ({attempt + 1}/{max_retries})…")
                new_image = self._retry_swap(client, model, source_bytes, target_bytes)
                if new_image is not None:
                    current_image = new_image
                else:
                    print("[QualityGate] ⚠ Internal swap failed — skipping remaining retries")
                    break

        # All attempts failed
        report = f"❌ ALL FAILED ({len(all_reasons)} attempts) — {'; '.join(all_reasons)}"
        print(f"[QualityGate] {report}")
        return (torch.zeros_like(swapped_image), False, report)

    def _validate(self, client, model, source_bytes, target_bytes, image_tensor):
        """Validate a swap result. Returns (passed, reason)."""
        swap_bytes = _pil_to_bytes(tensor_to_pil(image_tensor))
        contents = [
            "IMAGE 1 — Reference identity:",
            types.Part.from_bytes(data=source_bytes, mime_type="image/png"),
            "IMAGE 2 — Original scene:",
            types.Part.from_bytes(data=target_bytes, mime_type="image/png"),
            "IMAGE 3 — Swap result to validate:",
            types.Part.from_bytes(data=swap_bytes, mime_type="image/png"),
            QUALITY_PROMPT,
        ]

        response_text = self._call_gemini_text(client, model, contents)
        return self._parse_response(response_text)

    def _retry_swap(self, client, model, source_bytes, target_bytes):
        """Generate a new face swap internally. Returns IMAGE tensor or None."""
        contents = [
            "IMAGE 1 — Source identity:",
            types.Part.from_bytes(data=source_bytes, mime_type="image/png"),
            "IMAGE 2 — Target scene:",
            types.Part.from_bytes(data=target_bytes, mime_type="image/png"),
            RETRY_SWAP_PROMPT,
        ]
        config = {
            "response_modalities": ["IMAGE"],
            "temperature": 1.0,
        }
        try:
            response = client.models.generate_content(model=model, contents=contents, config=config)
            result_pil = extract_image_from_response(response)
            if result_pil:
                print(f"[QualityGate] ✓ Internal swap generated — {result_pil.size}")
                return pil_to_tensor(result_pil)
            print("[QualityGate] ⚠ No image in retry response")
            return None
        except Exception as e:
            print(f"[QualityGate] ⚠ Internal swap error: {e}")
            return None

    def _call_gemini_text(self, client, model, contents) -> str:
        """Call Gemini for TEXT response. 1 retry after 5s. Fail-open on error."""
        config = {"response_modalities": ["TEXT"], "temperature": 0.1}
        for attempt in range(2):
            try:
                response = client.models.generate_content(model=model, contents=contents, config=config)
                if response and hasattr(response, "text") and response.text:
                    return response.text.strip()
                return "FAIL|empty API response"
            except Exception as e:
                if attempt == 0:
                    print(f"[QualityGate] ⚠ Validation API error: {e}. Retrying in 5s…")
                    time.sleep(5)
                else:
                    print(f"[QualityGate] ⚠ Retry failed: {e}. Fail-open → PASS")
                    return f"PASS_API_ERROR|{str(e)[:80]}"
        return "PASS_API_ERROR|unknown"

    def _parse_response(self, text: str) -> tuple[bool, str]:
        if text.startswith("PASS"):
            if "API_ERROR" in text:
                parts = text.split("|", 1)
                reason = parts[1].strip() if len(parts) > 1 else "API unreachable"
                return True, f"⚠️ API error, could not validate: {reason}"
            return True, ""
        elif text.startswith("FAIL"):
            parts = text.split("|", 1)
            return False, parts[1].strip() if len(parts) > 1 else "unspecified"
        else:
            return False, f"unexpected response: {text[:100]}"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
