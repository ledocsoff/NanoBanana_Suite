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
                    "tooltip": "Dossier contenant les vidéos à spoofer"
                }),
                "number_of_folders": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 50,
                    "tooltip": "Nombre de sous-dossiers (1, 2, 3...) à créer avec une copie intégrale."
                }),
            }
        }

    def spoof(self, input_folder, number_of_folders):
        input_folder = input_folder.strip().strip("'\"")
        
        if not os.path.exists(input_folder):
            raise Exception(f"Le dossier source n'existe pas : {input_folder}")

        # Le dossier maitre qui contiendra tous les lots (copies)
        out_dirname = "_SPOOFED_BATCHES"
        spoofed_base_path = os.path.join(input_folder, out_dirname)
        os.makedirs(spoofed_base_path, exist_ok=True)

        # Lister les vidéos (parcours récursif pour inclure les sous-dossiers "dance", "talking"...)
        video_extensions = ('.mp4', '.mov', '.webm')
        videos = []
        for root, _, files in os.walk(input_folder):
            rel_root = os.path.relpath(root, input_folder)
            parts = rel_root.split(os.sep)
            
            # 1. Ignorer totalement le dossier de sortie _SPOOFED_BATCHES
            if parts[0] == out_dirname:
                continue
                
            # 2. Ignorer les anciens dossiers générés à la racine (1, 2, 3...) par mesure de sécurité
            if parts[0].isdigit():
                continue
                
            for f in files:
                if f.lower().endswith(video_extensions):
                    rel_path = os.path.relpath(os.path.join(root, f), input_folder)
                    videos.append(rel_path)
        
        videos.sort()
        
        if not videos:
            raise Exception(f"Aucune vidéo trouvée récursivement dans {input_folder}")
        
        total_generated = 0
        
        for folder_idx in range(1, number_of_folders + 1):
            target_base_dir = os.path.join(spoofed_base_path, str(folder_idx))
            os.makedirs(target_base_dir, exist_ok=True)
            
            for rel_video_path in videos:
                input_path = os.path.join(input_folder, rel_video_path)
                
                # Reconstruire l'arborescence (ex: 1/dance/)
                rel_dir = os.path.dirname(rel_video_path)
                target_sub_dir = os.path.join(target_base_dir, rel_dir)
                os.makedirs(target_sub_dir, exist_ok=True)
                
                prefixes = ["CapCut", "IMG", "VID", "Snapchat", "InShot", "video", "WhatsApp_Video"]
                output_name = f"{random.choice(prefixes)}_{uuid.uuid4().hex[:8]}.mp4"
                output_path = os.path.join(target_sub_dir, output_name)
                
                self._spoof_single(input_path, output_path)
                total_generated += 1
                
            print(f"🍌 [NB_VideoSpoofer] ✅ Lot {folder_idx}/ créé avec {len(videos)} vidéos spoofées.")
        
        print(f"🍌 [NB_VideoSpoofer] 🎉 Spoofing terminé: {total_generated} vidéos totales réparties.")
        # Return the master spoof folder so downstream nodes (if any) can find the output root
        return (spoofed_base_path,)

    def _spoof_single(self, input_path, output_path):
        """Applique des micro-transformations aléatoires uniques à chaque vidéo"""
        
        # ── Paramètres aléatoires (différents pour chaque copie) ──
        brightness = random.uniform(-0.03, 0.03)      # ±3%
        contrast = random.uniform(0.97, 1.03)          # ±3%
        saturation = random.uniform(0.97, 1.03)        # ±3%
        crop_pct = random.randint(2, 4) / 100.0        # 2-4% de crop (suffisant pour changer le hash, quasi invisible)
        crf = random.randint(25, 28)                   # Sweet spot Instagram (2-3x plus léger, qualité identique sur mobile)
        speed = random.uniform(1.01, 1.07)             # +1% à +7% vitesse
        volume = random.uniform(0.95, 1.05)            # ±5% volume
        
        preset = random.choice(["medium", "slow"])     # Pas de 'fast' : compression moins efficace pour la même qualité
        profile = random.choice(["main", "high"])      # Pas de 'baseline' : compression dégradée sur appareils modernes
        
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
            f"crop=iw*(1-2*{crop_pct:.2f}):ih*(1-2*{crop_pct:.2f}):iw*{crop_pct:.2f}:ih*{crop_pct:.2f}",
            f"scale=1080:1920:flags=lanczos",        # Rescale HD imposé avec Lanczos
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
            "-preset", preset,
            "-profile:v", profile,
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",                                     # Overwrite
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr[:500] if result.stderr else 'Unknown error'}")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
