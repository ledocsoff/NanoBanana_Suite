import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nodes.batch.batch_video_queue import Omni_BatchVideoQueue
from nodes.kling.kling_auth import Omni_KlingAuth
from nodes.kling.kling_motion_control import Omni_KlingMotionControl
from nodes.video.video_first_frame import Omni_VideoFirstFrame

if __name__ == "__main__":
    print("This script is a structural stub to verify imports for the full pipeline.")
    print("✅ All node classes imported successfully.")
