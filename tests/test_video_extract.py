import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.video_utils import extract_metadata, extract_frame
from core.image_utils import frame_to_tensor, tensor_to_pil

def test_video(video_path):
    print(f"Testing video: {video_path}")
    
    try:
        meta = extract_metadata(video_path)
        print("✅ Metadata extracted:")
        for k, v in meta.items():
            print(f"  {k}: {v}")
            
        frame = extract_frame(video_path, 0)
        tensor = frame_to_tensor(frame)
        pil_img = tensor_to_pil(tensor)
        
        out_path = os.path.join(os.path.dirname(video_path), "test_frame_0.png")
        pil_img.save(out_path)
        print(f"✅ First frame saved to: {out_path} ({pil_img.width}x{pil_img.height})")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_video_extract.py <path_to_video>")
    else:
        test_video(sys.argv[1])
