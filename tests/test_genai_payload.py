from google import genai
try:
    client = genai.Client(api_key="fake_key_just_checking_types")
    
    # Check if we can build a request with the dict
    print("Testing dict payload...")
    try:
        req = client._models._prepare_generate_content_request(
            model="gemini-3-pro-image-preview",
            contents=["test", {"mime_type": "image/png", "data": b"fakebytes"}]
        )
        print("Success dict payload")
    except Exception as e:
        print(f"Error dict payload: {e}")
        
except Exception as e:
    print(f"General error: {e}")
