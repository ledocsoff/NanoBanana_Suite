import base64
from io import BytesIO
import numpy as np
import torch
from PIL import Image

def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    if len(tensor.shape) == 4:
        tensor = tensor[0]
    
    img_np = (tensor.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    return Image.fromarray(img_np)

def pil_to_tensor(image: Image.Image) -> torch.Tensor:
    if image.mode != "RGB":
        image = image.convert("RGB")
    
    img_np = np.array(image).astype(np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)

def pil_to_base64(image: Image.Image, format: str = "PNG") -> str:
    buffered = BytesIO()
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def base64_to_pil(b64_string: str) -> Image.Image:
    image_data = base64.b64decode(b64_string)
    return Image.open(BytesIO(image_data))

def frame_to_tensor(frame: np.ndarray) -> torch.Tensor:
    img_np = frame.astype(np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)
