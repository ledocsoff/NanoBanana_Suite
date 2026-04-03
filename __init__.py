import os
import sys
import importlib.util

# Ensure ComfyUI and Python can resolve internal module paths (like 'shared.' and 'core.') universally.
extension_path = os.path.dirname(os.path.abspath(__file__))
if extension_path not in sys.path:
    sys.path.insert(0, extension_path)

# --- Generation ---
from .nodes.generation.prompt_to_image import OmniPromptToImage
from .nodes.generation.image_to_image import OmniImageToImage

# --- Direction ---
from .nodes.direction.ia_director import OmniAIDirector, OmniMatrixBuilder, OmniVisionAPI
from .nodes.direction.variant_director import OmniVariantDirector, OmniVariantAPI
from .nodes.direction.chooser import OmniChooser

# --- Face ---
from .nodes.face.swap import OmniSwap
from .nodes.face.identity_gate import OmniIdentityGate

# --- Post-process ---
from .nodes.postprocess.output import OmniPreview, OmniCleanSave

# --- Video ---
from .nodes.video.batch_video_queue import Omni_BatchVideoQueue
from .nodes.video.video_first_frame import Omni_VideoFirstFrame

# --- API ---
from .nodes.api.omni_piapi_auth import Omni_PiAPIAuth
from .nodes.api.omni_piapi_kling_mc import Omni_PiAPIKlingMotionControl

from .nodes.api.omni_piapi_kling_i2v import NODE_CLASS_MAPPINGS as KLING_OMNI_MAPPINGS
from .nodes.api.omni_piapi_kling_i2v import NODE_DISPLAY_NAME_MAPPINGS as KLING_OMNI_DISPLAY

from .nodes.api.omni_veo import NODE_CLASS_MAPPINGS as VEO_MAPPINGS
from .nodes.api.omni_veo import NODE_DISPLAY_NAME_MAPPINGS as VEO_DISPLAY

# --- Talking Video Pipeline ---
from .nodes.generation.omni_script_generator import NODE_CLASS_MAPPINGS as SCRIPT_GEN_MAPPINGS
from .nodes.generation.omni_script_generator import NODE_DISPLAY_NAME_MAPPINGS as SCRIPT_GEN_DISPLAY

# --- Collect ---
from .nodes.collect.omni_apify_collector import NODE_CLASS_MAPPINGS as APIFY_MAPPINGS
from .nodes.collect.omni_apify_collector import NODE_DISPLAY_NAME_MAPPINGS as APIFY_DISPLAY
from .nodes.collect.omni_apify_report import NODE_CLASS_MAPPINGS as APIFY_REPORT_MAPPINGS
from .nodes.collect.omni_apify_report import NODE_DISPLAY_NAME_MAPPINGS as APIFY_REPORT_DISPLAY


# --- Batch Processing & Loaders ---
from .nodes.tools.omni_batch_script_queue import NODE_CLASS_MAPPINGS as BATCH_SCRIPT_MAPPINGS
from .nodes.tools.omni_batch_script_queue import NODE_DISPLAY_NAME_MAPPINGS as BATCH_SCRIPT_DISPLAY

from .nodes.tools.omni_image_pool_loader import NODE_CLASS_MAPPINGS as POOL_LOADER_MAPPINGS
from .nodes.tools.omni_image_pool_loader import NODE_DISPLAY_NAME_MAPPINGS as POOL_LOADER_DISPLAY

from .nodes.tools.omni_directive_randomizer import NODE_CLASS_MAPPINGS as DIRECTIVE_RAND_MAPPINGS
from .nodes.tools.omni_directive_randomizer import NODE_DISPLAY_NAME_MAPPINGS as DIRECTIVE_RAND_DISPLAY

# --- Tools ---
from .nodes.tools.omni_spoofer import Omni_Spoofer
from .nodes.tools.omni_geelark_scheduler import Omni_GeeLarkScheduler
from .nodes.tools.omni_schedule_report import NODE_CLASS_MAPPINGS as SCHEDULE_REPORT_MAPPINGS
from .nodes.tools.omni_schedule_report import NODE_DISPLAY_NAME_MAPPINGS as SCHEDULE_REPORT_DISPLAY
from .nodes.tools.omni_static_captioner import Omni_StaticCaptioner
from .nodes.tools.omni_emoji_bio_gen import Omni_EmojiBioGen
from .nodes.tools.omni_profile_filler import Omni_ProfileFiller
from .nodes.tools.omni_warmup_filler import Omni_AccountWarmupFiller

# --- Shared ---
from .shared.gemini_config import OmniGeminiConfig

NODE_CLASS_MAPPINGS = {
    # Generation
    "OmniPromptToImage": OmniPromptToImage,
    "OmniImageToImage": OmniImageToImage,
    
    # Direction
    "OmniAIDirector": OmniAIDirector,
    "OmniMatrixBuilder": OmniMatrixBuilder,
    "OmniVisionAPI": OmniVisionAPI,
    "OmniVariantDirector": OmniVariantDirector,
    "OmniVariantAPI": OmniVariantAPI,
    "OmniChooser": OmniChooser,
    
    # Face
    "OmniSwap": OmniSwap,
    "OmniIdentityGate": OmniIdentityGate,
    
    # Post-process
    "OmniPreview": OmniPreview,
    "OmniCleanSave": OmniCleanSave,
    
    # Shared
    "OmniGeminiConfig": OmniGeminiConfig,
    
    # Video
    "Omni_BatchVideoQueue": Omni_BatchVideoQueue,
    "Omni_VideoFirstFrame": Omni_VideoFirstFrame,
    # Tools
    "Omni_Spoofer": Omni_Spoofer,
    "Omni_GeeLarkScheduler": Omni_GeeLarkScheduler,
    "Omni_StaticCaptioner": Omni_StaticCaptioner,
    "Omni_EmojiBioGen": Omni_EmojiBioGen,
    "Omni_ProfileFiller": Omni_ProfileFiller,
    "Omni_AccountWarmupFiller": Omni_AccountWarmupFiller,
    # API
    "Omni_PiAPIAuth": Omni_PiAPIAuth,
    "Omni_PiAPIKlingMotionControl": Omni_PiAPIKlingMotionControl,
}

NODE_CLASS_MAPPINGS.update(SCRIPT_GEN_MAPPINGS)

NODE_CLASS_MAPPINGS.update(BATCH_SCRIPT_MAPPINGS)
NODE_CLASS_MAPPINGS.update(POOL_LOADER_MAPPINGS)
NODE_CLASS_MAPPINGS.update(KLING_OMNI_MAPPINGS)
NODE_CLASS_MAPPINGS.update(VEO_MAPPINGS)
NODE_CLASS_MAPPINGS.update(DIRECTIVE_RAND_MAPPINGS)
NODE_CLASS_MAPPINGS.update(APIFY_MAPPINGS)
NODE_CLASS_MAPPINGS.update(APIFY_REPORT_MAPPINGS)
NODE_CLASS_MAPPINGS.update(SCHEDULE_REPORT_MAPPINGS)

NODE_DISPLAY_NAME_MAPPINGS = {
    # Generation
    "OmniPromptToImage": "Prompt to Image",
    "OmniImageToImage": "Image to Image",
    
    # Direction
    "OmniAIDirector": "IA Director",
    "OmniMatrixBuilder": "Matrix Builder",
    "OmniVisionAPI": "Vision API",
    "OmniVariantDirector": "Variant Director",
    "OmniVariantAPI": "Variant API",
    "OmniChooser": "Chooser",
    
    # Face
    "OmniSwap": "Swap",
    "OmniIdentityGate": "Identity Gate",
    
    # Post-process
    "OmniPreview": "Preview",
    "OmniCleanSave": "Clean Save",
    
    # Shared
    "OmniGeminiConfig": "Gemini Config",
    
    # Video
    "Omni_BatchVideoQueue": "Batch Video Queue",
    "Omni_VideoFirstFrame": "Video First Frame",
    
    # Tools
    "Omni_Spoofer": "Spoofer",
    "Omni_GeeLarkScheduler": "GeeLark Scheduler",
    "Omni_StaticCaptioner": "Static Captioner",
    "Omni_EmojiBioGen": "Emoji Bio Generator",
    "Omni_ProfileFiller": "Profile Filler",
    "Omni_AccountWarmupFiller": "Account Warmup Filler",
    
    # API
    "Omni_PiAPIAuth": "PiAPI Kling Auth",
    "Omni_PiAPIKlingMotionControl": "PiAPI Kling Motion Control",
}

NODE_DISPLAY_NAME_MAPPINGS.update(SCRIPT_GEN_DISPLAY)

NODE_DISPLAY_NAME_MAPPINGS.update(BATCH_SCRIPT_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(POOL_LOADER_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(KLING_OMNI_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(VEO_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(DIRECTIVE_RAND_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(APIFY_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(APIFY_REPORT_DISPLAY)
NODE_DISPLAY_NAME_MAPPINGS.update(SCHEDULE_REPORT_DISPLAY)

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
