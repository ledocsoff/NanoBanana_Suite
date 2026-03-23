import subprocess
import random
import uuid
import os
import time

class NB_VideoSpoofer:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("spoofed_folder",)
    FUNCTION = "spoof"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_folder": ("STRING", {
                    "default": "",
                    "tooltip": "Dossier contenant les vidéos MC à spoofer (ex: /output)"
                }),
                "output_folder": ("STRING", {
                    "default": "",
                    "tooltip": "Dossier de sortie pour les vidéos spoofées"
                }),
                "copies_per_video": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 10,
                    "tooltip": "Nombre de copies spoofées par vidéo source."
                }),
            }
        }

    def spoof(self, input_folder, output_folder, copies_per_video):
        os.makedirs(output_folder, exist_ok=True)
        
        # Lister les vidéos dans le dossier input
        video_extensions = ('.mp4', '.mov', '.webm')
        videos = sorted([
            f for f in os.listdir(input_folder) 
            if f.lower().endswith(video_extensions)
        ])
        
        if not videos:
            raise Exception(f"Aucune vidéo trouvée dans {input_folder}")
        
        total_generated = 0
        
        for video_file in videos:
            input_path = os.path.join(input_folder, video_file)
            
            for copy_idx in range(copies_per_video):
                # Toujours utiliser un nommage complètement aléatoire
                # Cela permet un tri alphabétique totalement hasardeux
                # vital pour la fonction 'Upload in order' de GeeLark
                output_name = f"CapCut_{uuid.uuid4().hex[:8]}.mp4"
                
                output_path = os.path.join(output_folder, output_name)
                
                self._spoof_single(input_path, output_path)
                total_generated += 1
                print(f"[NanaBanana] 🎭 Spoofed {total_generated}: {output_name}")
        
        print(f"[NanaBanana] ✅ Spoofing terminé: {total_generated} vidéos dans {output_folder}")
        return (output_folder,)

    def _spoof_single(self, input_path, output_path):
        """Applique des micro-transformations aléatoires uniques à chaque vidéo"""
        
        # ── Paramètres aléatoires (différents pour chaque copie) ──
        brightness = random.uniform(-0.03, 0.03)      # ±3%
        contrast = random.uniform(0.97, 1.03)          # ±3%
        saturation = random.uniform(0.97, 1.03)        # ±3%
        crop_px = random.randint(1, 4)                 # 1-4 pixels
        crf = random.randint(20, 24)                   # Qualité variable
        speed = random.uniform(1.01, 1.03)             # +1% à +3% vitesse
        volume = random.uniform(0.95, 1.05)            # ±5% volume
        
        # ── Metadata fake ──
        fake_encoders = [
            "Lavf58.76.100",
            "Lavf60.3.100", 
            "com.apple.photos",
            "MediaCodec",
        ]
        encoder = random.choice(fake_encoders)
        
        # Date de création aléatoire (derniers 7 jours)
        fake_timestamp = int(time.time()) - random.randint(0, 7 * 86400)
        from datetime import datetime
        fake_date = datetime.fromtimestamp(fake_timestamp).strftime("%Y-%m-%dT%H:%M:%S")
        
        # ── Filtres FFmpeg ──
        v_filters = [
            f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}",
            f"crop=iw-{crop_px*2}:ih-{crop_px*2}:{crop_px}:{crop_px}",
            f"scale=iw+{crop_px*2}:ih+{crop_px*2}",  # Rescale à la taille originale
            f"setpts={1/speed:.4f}*PTS"              # Vitesse vidéo
        ]
        a_filters = [
            f"atempo={speed:.4f}",                   # Vitesse audio (sans pitch bizarre)
            f"volume={volume:.4f}"                   # Changement léger du volume
        ]
        
        import shutil
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            # Fallbacks pour Mac si ComfyUI Desktop isole le PATH
            for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
                if os.path.exists(p):
                    ffmpeg_path = p
                    break
        
        if not ffmpeg_path:
            raise Exception("FFmpeg introuvable ! Ouvrez votre Terminal Mac et tapez : brew install ffmpeg")
            
        cmd = [
            ffmpeg_path, "-i", input_path,
            "-vf", ",".join(v_filters),
            "-af", ",".join(a_filters),
            "-map_metadata", "-1",                    # Strip toute metadata
            "-metadata", f"encoder={encoder}",        # Fake encoder
            "-metadata", f"creation_time={fake_date}",# Fake date
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",                                     # Overwrite
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr[:500] if result.stderr else 'Unknown error'}")
