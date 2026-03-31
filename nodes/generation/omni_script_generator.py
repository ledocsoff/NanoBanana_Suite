import os
import sys
import time
import requests
import re

_custom_nodes_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _custom_nodes_dir not in sys.path:
    sys.path.insert(0, _custom_nodes_dir)

from shared.gemini_client import create_gemini_client, TEXT_MODELS

class Omni_ScriptGenerator:
    CATEGORY = "Omni"
    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("generated_text", "word_count", "status_message")
    FUNCTION = "generate_text"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (["gemini", "ollama"], {"default": "gemini"}),
                "model": (TEXT_MODELS, {"default": "gemini-2.5-flash"}),
                "system_prompt": ("STRING", {
                    "default": "You are a helpful AI assistant.", 
                    "multiline": True,
                    "tooltip": "The permanent system prompt rules and role definition."
                }),
                "directives": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "tooltip": "The dynamic user context or task directives (can be wired from Queue)."
                }),
                "temperature": ("FLOAT", {
                    "default": 0.8, "min": 0.0, "max": 2.0, "step": 0.05,
                    "tooltip": "Creativity / variation rate."
                }),
                "max_retries": ("INT", {"default": 3, "min": 1, "max": 5, "step": 1}),
            },
            "optional": {
                "gemini_config": ("GEMINI_CONFIG",),
                "directive_override": ("STRING", {
                    "forceInput": True,
                    "tooltip": "When connected (e.g. from Directive Randomizer), this text is appended to the directives widget."
                }),
                "ollama_model": ("STRING", {"default": "qwen3.5:9b"}),
                "ollama_url": ("STRING", {"default": "http://localhost:11434"}),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()

    def _clean_text(self, text):
        text = text.strip()
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            text = text[1:-1]

        # Strip markdown code blocks
        text = re.sub(r'```[a-z]*\n(.*?)\n```', r'\1', text, flags=re.DOTALL)

        clean_lines = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Remove purely bracketed lines like [Pause] or (smiling)
            if (line.startswith('[') and line.endswith(']')) or (line.startswith('(') and line.endswith(')')):
                continue
            clean_lines.append(line)

        text = " ".join(clean_lines)
        # Remove mid-line brackets and hashtags
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def generate_text(self, provider, system_prompt, directives, temperature, max_retries, 
                      model="gemini-2.5-flash", gemini_config=None, directive_override="",
                      ollama_model="qwen3.5:9b", ollama_url="http://localhost:11434"
    ):
        # Merge widget directives with override from DirectiveRandomizer
        if directive_override and directive_override.strip():
            directives = f"{directives.strip()}\n{directive_override.strip()}" if directives.strip() else directive_override.strip()

        if not system_prompt.strip() and not directives.strip():
            print("[Omni_ScriptGenerator] SKIP: Both system_prompt and directives are empty.")
            return ("", 0, "SKIP: empty inputs")

        print(f"[Omni_ScriptGenerator] Generating via {provider.upper()}")

        full_prompt = (
            f"SYSTEM RULES:\n{system_prompt.strip()}\n\n"
            f"USER DIRECTIVES:\n{directives.strip()}"
        )

        raw_text = ""
        error_msg = ""
        success = False

        if provider == "gemini":
            if not gemini_config:
                return ("", 0, "ERROR: gemini_config required when provider=gemini")

            safe_config = dict(gemini_config)

            try:
                client = create_gemini_client(safe_config)
            except Exception as e:
                return ("", 0, f"ERROR: Gemini Client init failed: {e}")

            config = {"temperature": temperature}
            
            # Using basic text query, system rules built into prompt text
            contents = [full_prompt]

            for i in range(1, max_retries + 1):
                try:
                    print(f"[Omni_ScriptGenerator] Attempt {i}/{max_retries} (Gemini)...")
                    response = client.models.generate_content(model=model, contents=contents, config=config)
                    if response and hasattr(response, "text") and response.text:
                        raw_text = response.text
                        success = True
                        break
                    else:
                        error_msg = "Empty Gemini Response"
                except Exception as e:
                    print(f"[Omni_ScriptGenerator] API Error: {e}")
                    error_msg = str(e)
                    time.sleep(2)

        elif provider == "ollama":
            url = f"{ollama_url.rstrip('/')}/api/generate"
            payload = {
                "model": ollama_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            for i in range(1, max_retries + 1):
                try:
                    print(f"[Omni_ScriptGenerator] Attempt {i}/{max_retries} (Ollama)...")
                    req = requests.post(url, json=payload, timeout=120)
                    req.raise_for_status()
                    data = req.json()
                    if "response" in data:
                        raw_text = data["response"]
                        success = True
                        break
                    else:
                        error_msg = "No 'response' key in Ollama output"
                except Exception as e:
                    print(f"[Omni_ScriptGenerator] API Error: {e}")
                    error_msg = str(e)
                    time.sleep(2)

        else:
            return ("", 0, f"ERROR: Unknown provider {provider}")

        if not success:
            err = f"ERROR: LLM call failed after {max_retries} retries: {error_msg}"
            print(f"[Omni_ScriptGenerator] {err}")
            return ("", 0, err)

        clean_text = self._clean_text(raw_text)
        word_count = len(clean_text.split())

        print(f"[Omni_ScriptGenerator] ✅ Generated text ({word_count} words): {clean_text[:80]}...")

        return (clean_text, word_count, "OK")

NODE_CLASS_MAPPINGS = {"Omni_ScriptGenerator": Omni_ScriptGenerator}
NODE_DISPLAY_NAME_MAPPINGS = {"Omni_ScriptGenerator": "Generic AI Generator"}
