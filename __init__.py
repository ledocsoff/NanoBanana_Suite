import os
import sys
import importlib.util

# Ensure ComfyUI and Python can resolve internal module paths (like 'shared.' and 'core.') universally.
extension_path = os.path.dirname(os.path.abspath(__file__))
if extension_path not in sys.path:
    sys.path.insert(0, extension_path)

# --- Generation ---
from .nodes.generation.prompt_to_image import NanoBananaPromptToImage
from .nodes.generation.image_to_image import NanoBananaImageToImage

# --- Direction ---
from .nodes.direction.ia_director import NanoBananaAIDirector, NanoBananaMatrixBuilder, NanoBananaVisionAPI
from .nodes.direction.variant_director import NanoBananaVariantDirector, NanoBananaVariantAPI
from .nodes.direction.chooser import NanoBananaChooser

# --- Face ---
from .nodes.face.swap import NanoBananaSwap
from .nodes.face.quality_gate import NanoBananaQualityGate

# --- Post-process ---
from .nodes.postprocess.output import NanoBananaPreview, NanoBananaCleanSave

# --- Video ---
from .nodes.video.batch_video_queue import NB_BatchVideoQueue
from .nodes.video.video_first_frame import NB_VideoFirstFrame
from .nodes.video.export_for_kling import NB_ExportForKling

# --- API ---
from .nodes.api.nb_piapi_auth import NB_PiAPIAuth
from .nodes.api.nb_piapi_kling_mc import NB_PiAPIKlingMotionControl

# --- Tools ---
from .nodes.tools.nb_video_spoofer import NB_VideoSpoofer
from .nodes.tools.nb_geelark_scheduler import NB_GeeLarkScheduler
from .nodes.tools.nb_static_captioner import NB_StaticCaptioner
from .nodes.tools.nb_emoji_bio_gen import NB_EmojiBioGen
from .nodes.tools.nb_profile_filler import NB_ProfileFiller
from .nodes.tools.nb_warmup_filler import NB_AccountWarmupFiller

# --- Shared ---
from .shared.gemini_config import NanoBananaGeminiConfig

NODE_CLASS_MAPPINGS = {
    # Generation
    "NanoBananaPromptToImage": NanoBananaPromptToImage,
    "NanoBananaImageToImage": NanoBananaImageToImage,
    
    # Direction
    "NanoBananaAIDirector": NanoBananaAIDirector,
    "NanoBananaMatrixBuilder": NanoBananaMatrixBuilder,
    "NanoBananaVisionAPI": NanoBananaVisionAPI,
    "NanoBananaVariantDirector": NanoBananaVariantDirector,
    "NanoBananaVariantAPI": NanoBananaVariantAPI,
    "NanoBananaChooser": NanoBananaChooser,
    
    # Face
    "NanoBananaSwap": NanoBananaSwap,
    "NanoBananaQualityGate": NanoBananaQualityGate,
    
    # Post-process
    "NanoBananaPreview": NanoBananaPreview,
    "NanoBananaCleanSave": NanoBananaCleanSave,
    
    # Shared
    "NanoBananaGeminiConfig": NanoBananaGeminiConfig,
    
    # Video
    "NB_BatchVideoQueue": NB_BatchVideoQueue,
    "NB_VideoFirstFrame": NB_VideoFirstFrame,
    "NB_ExportForKling": NB_ExportForKling,
    # Tools
    "NB_VideoSpoofer": NB_VideoSpoofer,
    "NB_GeeLarkScheduler": NB_GeeLarkScheduler,
    "NB_StaticCaptioner": NB_StaticCaptioner,
    "NB_EmojiBioGen": NB_EmojiBioGen,
    "NB_ProfileFiller": NB_ProfileFiller,
    "NB_AccountWarmupFiller": NB_AccountWarmupFiller,
    # API
    "NB_PiAPIAuth": NB_PiAPIAuth,
    "NB_PiAPIKlingMotionControl": NB_PiAPIKlingMotionControl,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    # Generation
    "NanoBananaPromptToImage": "🍌 Prompt to Image",
    "NanoBananaImageToImage": "🍌 Image to Image",
    
    # Direction
    "NanoBananaAIDirector": "🍌 IA Director",
    "NanoBananaMatrixBuilder": "🍌 Matrix Builder",
    "NanoBananaVisionAPI": "🍌 Vision API",
    "NanoBananaVariantDirector": "🍌 Variant Director",
    "NanoBananaVariantAPI": "🍌 Variant API",
    "NanoBananaChooser": "🍌 Chooser",
    
    # Face
    "NanoBananaSwap": "🍌 Swap",
    "NanoBananaQualityGate": "🍌 Quality Gate",
    
    # Post-process
    "NanoBananaPreview": "🍌 Preview",
    "NanoBananaCleanSave": "🍌 Clean Save",
    
    # Shared
    "NanoBananaGeminiConfig": "🍌 Gemini Config",
    
    # Video
    "NB_BatchVideoQueue": "🍌 Batch Video Queue",
    "NB_VideoFirstFrame": "🍌 Video First Frame",
    "NB_ExportForKling": "🍌 Export for Kling",
    
    # Tools
    "NB_VideoSpoofer": "🍌 Video Spoofer",
    "NB_GeeLarkScheduler": "🍌 GeeLark Scheduler",
    "NB_StaticCaptioner": "🍌 Static Captioner",
    "NB_EmojiBioGen": "🍌 Emoji Bio Generator",
    "NB_ProfileFiller": "🍌 Profile Filler",
    "NB_AccountWarmupFiller": "🍌 Account Warmup Filler",
    
    # API
    "NB_PiAPIAuth": "🍌 PiAPI Kling Auth",
    "NB_PiAPIKlingMotionControl": "🍌 PiAPI Kling Motion Control",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
