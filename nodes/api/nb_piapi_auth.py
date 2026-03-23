class NB_PiAPIAuth:
    CATEGORY = "NanaBanana/API"
    RETURN_TYPES = ("PIAPI_AUTH",)
    RETURN_NAMES = ("auth",)
    FUNCTION = "authenticate"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Clé API PiAPI (x-api-key). Trouvable dans https://piapi.ai/workspace"
                }),
                "service_mode": (["hya", "public"], {
                    "default": "hya",
                    "tooltip": "hya = consomme les crédits de ton compte Kling connecté. public = consomme les crédits PiAPI."
                }),
            }
        }

    def authenticate(self, api_key, service_mode):
        auth = {
            "api_key": api_key,
            "base_url": "https://api.piapi.ai/api/v1",
            "upload_url": "https://upload.theapi.app/api/ephemeral_resource",
            "headers": {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            },
            "service_mode": "" if service_mode == "hya" else "public"
        }
        return (auth,)
