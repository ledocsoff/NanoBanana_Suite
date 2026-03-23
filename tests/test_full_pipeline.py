import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nodes.batch.batch_video_queue import NB_BatchVideoQueue
from nodes.kling.kling_auth import NB_KlingAuth
from nodes.kling.kling_motion_control import NB_KlingMotionControl
from nodes.video.video_first_frame import NB_VideoFirstFrame

if __name__ == "__main__":
    print("This script is a structural stub to verify imports for the full pipeline.")
    print("✅ All node classes imported successfully.")
