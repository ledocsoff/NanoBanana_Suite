from google import genai
from google.genai import types
import io

try:
    client = genai.Client(api_key="fake")
    dummy_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    
    # Method 1
    try:
        from google.genai.types import Part
        print("Types has Part:", bool(Part))
    except Exception as e:
        print(f"Error checking types.Part: {e}")

    # Method 2: Part.from_bytes
    try:
        part = types.Part.from_bytes(data=dummy_bytes, mime_type="image/png")
        print("Method 2 (types.Part.from_bytes) SUCCESS:", bool(part))
    except Exception as e:
        print(f"Method 2 FAILED: {type(e).__name__} - {e}")
except Exception as e:
    print(f"Genai setup failed: {e}")
