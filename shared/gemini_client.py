"""
Omni Shared — Gemini Client & Utilities
==============================================
Central module shared by all Omni ComfyUI nodes.

Provides:
  - IMAGE_CAPABLE_MODELS: Single source of truth for supported models
  - create_gemini_client: Factory for AI Studio / Vertex AI clients (returns client only)
  - call_with_retry: API call with exponential backoff
  - extract_image_from_response: Parse image from Gemini response
  - tensor_to_pil / pil_to_tensor: ComfyUI tensor ↔ PIL converters
"""

from __future__ import annotations

import io
import os
import random
import time
import traceback
from typing import Optional

import numpy as np
import torch
from PIL import Image
from google import genai

# ──────────────────────────────────────────────────────────────────────────────
# Constants  (single source of truth — add future models here only)
# ──────────────────────────────────────────────────────────────────────────────

IMAGE_CAPABLE_MODELS = [
    "gemini-2.0-flash-preview-image-generation",
    "gemini-3-pro-image-preview",
]

VIDEO_CAPABLE_MODELS = [
    "veo-3.1-generate-preview",
    "veo-2.0-generate-001",
]

TEXT_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-pro",
]

PROVIDERS = [
    "AI Studio",
    "Vertex AI",
]

GCP_LOCATIONS = [
    "global",
    "us-central1",
    "europe-west1",
    "europe-west4",
    "asia-northeast1",
]

ASPECT_RATIOS = ["AUTO", "1:1", "16:9", "4:3", "3:4", "9:16"]


# ──────────────────────────────────────────────────────────────────────────────
# Client Factory
# ──────────────────────────────────────────────────────────────────────────────

def create_gemini_client(config: dict) -> genai.Client:
    """
    Create a ``genai.Client`` from a GEMINI_CONFIG dict.
    Returns ``client``.

    For **AI Studio**: uses api_key (from config or ``GOOGLE_API_KEY`` env var).
    For **Vertex AI**: uses Application Default Credentials via
    ``gcloud auth application-default login``.
    """
    provider = config.get("provider", PROVIDERS[0])

    if "Vertex" in provider:
        project = config.get("gcp_project_id", "").strip()
        location = config.get("gcp_location", GCP_LOCATIONS[0]).strip()

        if not project:
            raise ValueError(
                "[Omni] ❌ Vertex AI selected but 'gcp_project_id' is empty. "
                "Please fill in your GCP project ID in the OmniGeminiConfig node."
            )

        # Suppress "No project ID could be determined" warning
        os.environ["GOOGLE_CLOUD_PROJECT"] = project

        try:
            client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
            )
            print(f"[Omni] ✓ Vertex AI client created — project={project}, location={location}")
            return client
        except Exception as e:
            error_str = str(e).lower()
            if "credentials" in error_str or "auth" in error_str or "adc" in error_str:
                raise RuntimeError(
                    "[Omni] ❌ Vertex AI authentication failed.\n"
                    "  → Please run: gcloud auth application-default login\n"
                    "  → Make sure the Google Cloud SDK (gcloud) is installed.\n"
                    f"  → Original error: {e}"
                ) from e
            raise

    else:  # AI Studio
        api_key = config.get("api_key", "").strip()
        if not api_key:
            api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "[Omni] ❌ AI Studio selected but no API key found.\n"
                "  → Provide it in the OmniGeminiConfig node, or\n"
                "  → Set the GOOGLE_API_KEY environment variable."
            )

        client = genai.Client(api_key=api_key)
        print("[Omni] ✓ AI Studio client created")
        return client


# ──────────────────────────────────────────────────────────────────────────────
# Image utilities  (ComfyUI tensor ↔ PIL)
# ──────────────────────────────────────────────────────────────────────────────

def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """
    Convert a ComfyUI IMAGE tensor  (B, H, W, C)  float32 [0, 1]  →  PIL RGB.
    Handles both batched and single-frame tensors.
    """
    t = tensor
    if t.dim() == 4:
        t = t[0]
    t = t.detach().cpu()
    np_img = (t.numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np_img, "RGB")


def pil_to_tensor(img: Image.Image) -> torch.Tensor:
    """
    Convert a PIL Image  →  ComfyUI IMAGE tensor  (1, H, W, C)  float32 [0, 1].
    """
    arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


# ──────────────────────────────────────────────────────────────────────────────
# Shared API helpers
# ──────────────────────────────────────────────────────────────────────────────

# Status codes / keywords that warrant a retry (transient server errors)
RETRYABLE_STATUS_CODES = {429, 499, 500, 502, 503, 504}
RETRYABLE_KEYWORDS = [
    "resource_exhausted", "resource exhausted",
    "too many requests", "rate limit", "quota exceeded", "quota_exceeded",
    "cancelled", "unavailable", "internal", "deadline exceeded",
]


def _is_retryable_error(error: Exception) -> bool:
    """Return True if the error is transient and worth retrying."""
    s = str(error).lower()
    # Check for known status codes
    for code in RETRYABLE_STATUS_CODES:
        if str(code) in s:
            return True
    # Check for known keyword patterns
    return any(kw in s for kw in RETRYABLE_KEYWORDS)


def extract_image_from_response(response) -> Optional[Image.Image]:
    """
    Extract the first image part from a google.genai SDK response object.
    Returns a PIL Image or None.
    """
    if not response or not hasattr(response, "candidates") or not response.candidates:
        print(f"[Omni] ⚠ Empty response or no candidates: {response}")
        return None

    candidate = response.candidates[0]
    if not hasattr(candidate, "content") or not candidate.content or not hasattr(candidate.content, "parts") or not candidate.content.parts:
        print(f"[Omni] ⚠ Candidate has no content parts: {candidate}")
        return None

    for part in candidate.content.parts:
        try:
            if hasattr(part, "inline_data") and part.inline_data:
                data = part.inline_data.data
                if data:
                    return Image.open(io.BytesIO(data)).convert("RGB")

            elif hasattr(part, "image") and part.image:
                if hasattr(part.image, "image_bytes"):
                    return Image.open(io.BytesIO(part.image.image_bytes)).convert("RGB")
                if isinstance(part.image, Image.Image):
                    return part.image.convert("RGB")

        except Exception as e:
            print(f"[Omni] ⚠ Error parsing part into PIL image: {e}")

    print("[Omni] ⚠ Gemini API replied successfully, but with NO image.")
    print("--- RAW API RESPONSE START ---")
    for part in candidate.content.parts:
        if hasattr(part, "text") and part.text:
            print(f"TEXT: {part.text}")
        else:
            print(f"UNKNOWN PART TYPE: {dir(part)}")
    print("--- RAW API RESPONSE END ---")

    return None


def call_with_retry(
    client: genai.Client,
    model: str,
    contents: list,
    config: dict,
    max_retries: int,
) -> tuple[Optional[object], str]:
    """
    Call ``client.models.generate_content`` with exponential backoff.

    Retries on transient errors (429, 499 CANCELLED, 500, 502, 503, 504).
    Fails immediately on non-retryable errors (400, 403, 404, safety blocks).
    Returns ``(response, status_message)``.
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            print(f"[Omni] → {model}  attempt {attempt + 1}/{max_retries}")
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            # Check if Gemini blocked it but returned 200 OK
            if response and hasattr(response, "candidates") and response.candidates:
                cand = response.candidates[0]
                if hasattr(cand, "finish_reason") and cand.finish_reason:
                    reason_str = str(cand.finish_reason).upper()
                    if "SAFETY" in reason_str or "BLOCK" in reason_str:
                        print(f"[Omni] ⚠ Content blocked by API internal filters (Finish Reason: {reason_str})")
                        return None, f"SAFETY_BLOCK: {reason_str}"

            return response, "Success"

        except Exception as e:
            last_error = e
            error_str = str(e)

            # Safety / policy blocks — never retry
            if any(t in error_str.lower() for t in ["safety", "blocked", "policy", "harmful"]):
                print(f"[Omni] ⚠ Content blocked by safety filters: {e}")
                return None, f"Content blocked by safety filters. Try modifying your prompt or images. ({error_str})"

            # Retryable transient errors
            if _is_retryable_error(e):
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt + random.uniform(0, 1), 30)
                    print(f"[Omni] ✗ {error_str[:80]} (attempt {attempt + 1}/{max_retries}) — retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    return None, f"Transient error after {max_retries} retries. Last error: {error_str}"

            # Non-retryable error (400, 403, 404, etc.) — fail immediately
            print(f"[Omni] ✗ Non-retryable error: {e}")
            traceback.print_exc()
            return None, f"Gemini API Error: {error_str}"

    return None, f"All {max_retries} attempts failed. Last error: {str(last_error)}"
