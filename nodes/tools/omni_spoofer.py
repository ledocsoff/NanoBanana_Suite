import subprocess
import random
import uuid
import os
import time
import shutil
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageEnhance


# ══════════════════════════════════════════════════════════════════════════════
# 🔒 CONFIGURATION DEVICE — Modifier ici pour changer l'identité de TOUTES
#    les vidéos spoofées. Un seul endroit à maintenir.
# ══════════════════════════════════════════════════════════════════════════════
DEVICE_MODEL    = "iPhone 16 Pro Max"
DEVICE_SOFTWARE = "26.3.1"

# Zone GPS de base (Miami, FL — USA). Chaque vidéo aura une micro-variation.
# Pour changer de ville : modifier lat/lon/alt ci-dessous.
# Exemples :  Los Angeles = 34.05, -118.25, 0-150m
#             New York    = 40.71, -74.00,  0-50m
#             Miami       = 25.76, -80.19,  0-30m
GPS_BASE_LAT = 25.76
GPS_BASE_LON = -80.19
GPS_ALT_MIN  = 0.0
GPS_ALT_MAX  = 30.0   # Miami est plat, altitude très basse

# Timezone US (heures de décalage UTC). Miami = Eastern Time.
# Exemples :  Los Angeles (Pacific)  = [-8, -7]
#             Chicago (Central)      = [-6, -5]
#             New York/Miami (East)  = [-5, -4]
TZ_OFFSETS = [-5, -4]  # EST / EDT

# ══════════════════════════════════════════════════════════════════════════════


class Omni_Spoofer:
    CATEGORY = "Omni/Tools"
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

        out_dirname = "_SPOOFED_BATCHES"
        spoofed_base_path = os.path.join(input_folder, out_dirname)
        os.makedirs(spoofed_base_path, exist_ok=True)

        media_extensions = ('.mp4', '.mov', '.webm', '.jpg', '.jpeg', '.png')
        media_files = []
        for root, _, files in os.walk(input_folder):
            rel_root = os.path.relpath(root, input_folder)
            parts = rel_root.split(os.sep)

            if parts[0] == out_dirname:
                continue
            if parts[0].isdigit():
                continue

            for f in files:
                if f.lower().endswith(media_extensions):
                    rel_path = os.path.relpath(os.path.join(root, f), input_folder)
                    media_files.append(rel_path)

        media_files.sort()

        if not media_files:
            raise Exception(f"Aucun média trouvé récursivement dans {input_folder}")

        total_generated = 0

        for folder_idx in range(1, number_of_folders + 1):
            target_base_dir = os.path.join(spoofed_base_path, str(folder_idx))
            os.makedirs(target_base_dir, exist_ok=True)

            # Séquences uniques pour éviter les collisions sans utiliser d'UUID
            seq_nums = random.sample(range(1000, 9999), len(media_files))

            for rel_media_path, seq_num in zip(media_files, seq_nums):
                input_path = os.path.join(input_folder, rel_media_path)

                rel_dir = os.path.dirname(rel_media_path)
                target_sub_dir = os.path.join(target_base_dir, rel_dir)
                os.makedirs(target_sub_dir, exist_ok=True)

                is_photo = input_path.lower().endswith(('.jpg', '.jpeg', '.png'))

                if is_photo:
                    prefix = "IMG"
                    output_name = f"{prefix}_{seq_num}.JPG"
                    output_path = os.path.join(target_sub_dir, output_name)
                    self._spoof_photo(input_path, output_path)
                else:
                    prefix = "IMG"
                    output_name = f"{prefix}_{seq_num}.MP4"
                    output_path = os.path.join(target_sub_dir, output_name)
                    self._spoof_video(input_path, output_path)

                total_generated += 1

            print(f"[Omni_Spoofer] ✅ Lot {folder_idx}/ créé avec {len(media_files)} fichiers spoofés.")

        print(f"[Omni_Spoofer] 🎉 Spoofing terminé: {total_generated} fichiers totaux.")
        return (spoofed_base_path,)

    def _generate_variable_metadata(self):
        """Génère les données VARIABLES par vidéo (date, GPS) tout en gardant le device FIXE."""

        # ── Date de création unique (derniers 7 jours, heure crédible 7h-23h) ──
        days_ago = random.randint(0, 7)
        hour = random.randint(7, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)

        tz_offset = timedelta(hours=random.choice(TZ_OFFSETS))
        tz = timezone(tz_offset)
        local_dt = datetime.now(tz) - timedelta(days=days_ago)
        local_dt = local_dt.replace(hour=hour, minute=minute, second=second, microsecond=0)
        utc_dt = local_dt.astimezone(timezone.utc)

        tz_sign = "+" if tz_offset.total_seconds() >= 0 else "-"
        tz_h = int(abs(tz_offset.total_seconds()) // 3600)
        tz_m = int((abs(tz_offset.total_seconds()) % 3600) // 60)

        creationdate = local_dt.strftime(f"%Y-%m-%dT%H:%M:%S{tz_sign}{tz_h:02d}{tz_m:02d}")
        creation_time_utc = utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000000Z")

        # ── GPS micro-variation (quelques dizaines de mètres autour de la base) ──
        lat = GPS_BASE_LAT + random.uniform(-0.002, 0.002)
        lon = GPS_BASE_LON + random.uniform(-0.002, 0.002)
        alt = random.uniform(GPS_ALT_MIN, GPS_ALT_MAX)
        # Gestion du signe pour ISO 6709 (latitudes/longitudes négatives possibles aux USA)
        lat_sign = "+" if lat >= 0 else ""
        lon_sign = "+" if lon >= 0 else ""
        location_iso6709 = f"{lat_sign}{lat:.4f}{lon_sign}{lon:08.4f}+{alt:.3f}/"
        gps_accuracy = round(random.uniform(5.0, 50.0), 6)

        offset_str = f"{tz_sign}{tz_h:02d}:{tz_m:02d}"
        subsec = str(random.randint(100, 999))
        
        # Exposure / Photo variables
        iso = random.choice([32, 40, 50, 64, 80, 100, 125, 160, 200, 320, 640])
        exposure_time = random.choice([30, 40, 50, 60, 120])
        brightness_val = round(random.uniform(-2.5, 4.5), 2)

        return {
            "creationdate": creationdate,
            "creation_time_utc": creation_time_utc,
            "location_iso6709": location_iso6709,
            "gps_accuracy": str(gps_accuracy),
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "datetime_original": local_dt.strftime("%Y:%m:%d %H:%M:%S"),
            "offset_str": offset_str,
            "subsec": subsec,
            "iso": str(iso),
            "exposure_time": f"1/{exposure_time}",
            "brightness_val": str(brightness_val)
        }

    def _find_tool(self, name, fallback_paths=None):
        """Cherche un outil CLI (ffmpeg, exiftool) dans le PATH puis dans les chemins connus."""
        path = shutil.which(name)
        if path:
            return path
        for p in (fallback_paths or []):
            if os.path.exists(p):
                return p
        return None

    def _spoof_video(self, input_path, output_path):
        """Encode la vidéo pour compatibilité Android (GeeLark) + metadata iPhone réalistes."""

        # ── Paramètres visuels aléatoires (changent le hash binaire) ──
        brightness = random.uniform(-0.03, 0.03)
        contrast = random.uniform(0.97, 1.03)
        saturation = random.uniform(0.97, 1.03)
        crop_pct = random.randint(2, 4) / 100.0
        crf = random.randint(25, 28)
        speed = random.uniform(1.01, 1.07)
        volume = random.uniform(0.95, 1.05)

        preset = random.choice(["medium", "slow"])
        profile = random.choice(["main", "high"])

        # ── Données variables pour cette vidéo ──
        meta = self._generate_variable_metadata()

        # ── Filtres FFmpeg ──
        # scale=1080:-2 préserve le ratio original (hauteur auto, arrondie au pair)
        # setsar=1:1 garantit des pixels carrés pour éviter la distorsion Android
        v_filters = [
            f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}",
            f"crop=iw*(1-2*{crop_pct:.2f}):ih*(1-2*{crop_pct:.2f}):iw*{crop_pct:.2f}:ih*{crop_pct:.2f}",
            "scale=1080:-2:flags=lanczos",
            "setsar=1:1",
            f"setpts={1/speed:.4f}*PTS",
        ]
        a_filters = [
            f"atempo={speed:.4f}",
            f"volume={volume:.4f}",
        ]

        ffmpeg_path = self._find_tool("ffmpeg", ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"])
        if not ffmpeg_path:
            raise Exception("FFmpeg introuvable ! Ouvrez votre Terminal Mac et tapez : brew install ffmpeg")

        cmd = [
            ffmpeg_path, "-i", input_path,

            # ── Filtres visuels + audio ──
            "-vf", ",".join(v_filters),
            "-af", ",".join(a_filters),

            # ── Format MP4 ──
            "-f", "mp4",

            # ── FASTSTART : moov atom en tête du fichier ──
            # CRITIQUE pour Android : le MediaScanner et MediaMetadataRetriever
            # lisent le moov atom pour générer le thumbnail et indexer le fichier.
            # Sans faststart, le moov est en fin de fichier → le scanner peut
            # timeout sur les cloud phones GeeLark (I/O cloud plus lent).
            "-movflags", "+faststart+use_metadata_tags",

            # ── Strip TOUTE metadata existante de la source ──
            "-map_metadata", "-1",

            # ── Metadata standard (udta) — LISIBLE PAR ANDROID ──
            # Android MediaStore scanne uniquement le format udta, pas mdta.
            # Ces tags sont essentiels pour l'indexation et le tri chronologique.
            "-metadata", f"creation_time={meta['creation_time_utc']}",
            "-metadata", f"date={meta['creation_time_utc']}",
            "-metadata", "make=Apple",
            "-metadata", f"model={DEVICE_MODEL}",

            # ── Anti-Forensic léger (metadata-only, sans corrompre le container) ──
            # NOTE : Les flags bitexact ont été RETIRÉS car ils produisent un
            # container MP4 non-standard qu'Android considère comme corrompu.
            "-metadata", "encoder=",
            "-metadata", "encoding_tool=",

            # ── Stream-level metadata (handler names Apple) ──
            "-metadata:s:v:0", "vendor_id=appl",
            "-metadata:s:v:0", "encoder=H.264",
            "-metadata:s:a:0", "encoder=AAC",
            "-metadata:s:v:0", "handler_name=Core Media Video",
            "-metadata:s:a:0", "handler_name=Core Media Audio",

            # ── Encodage vidéo ──
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", preset,
            "-profile:v", profile,
            "-pix_fmt", "yuv420p",
            "-tag:v", "avc1",

            # NOTE : Le filtre SEI (filter_units=remove_types=6) a été RETIRÉ.
            # Les SEI contiennent pic_timing et recovery_point utilisés par les
            # décodeurs hardware ARM d'Android. Sans eux → black frames, seek
            # cassé, et thumbnail noire via MediaMetadataRetriever.

            # ── Encodage audio ──
            "-c:a", "aac",
            "-b:a", "192k",
            "-tag:a", "mp4a",

            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr[:500] if result.stderr else 'Unknown error'}")

        # ── Post-processing : Injecter les metadata Apple mdta via ExifTool ──
        # FFmpeg écrit les metadata QuickTime mdta de façon peu fiable.
        # ExifTool les injecte proprement sans altérer le container MP4.
        exiftool_path = self._find_tool("exiftool", ["/opt/homebrew/bin/exiftool", "/usr/local/bin/exiftool"])
        if exiftool_path:
            exif_cmd = [
                exiftool_path, "-overwrite_original",
                f"-QuickTime:Make=Apple",
                f"-QuickTime:Model={DEVICE_MODEL}",
                f"-QuickTime:Software={DEVICE_SOFTWARE}",
                f"-QuickTime:CreationDate={meta['creationdate']}",
                f"-QuickTime:GPSCoordinates={meta['lat']:.6f} {meta['lon']:.6f} {meta['alt']:.1f}",
                f"-QuickTime:LocationISO6709={meta['location_iso6709']}",
                output_path
            ]
            subprocess.run(exif_cmd, capture_output=True, text=True)

            # ── Re-faststart : ExifTool réécrit tout le fichier MP4 et peut ──
            # déplacer le moov atom en fin de fichier, annulant le faststart.
            # Ce remux léger (pas de ré-encodage) remet le moov en tête.
            tmp_path = output_path + ".tmp"
            remux = subprocess.run([
                ffmpeg_path, "-i", output_path,
                "-c", "copy",
                "-movflags", "+faststart",
                "-y", tmp_path
            ], capture_output=True, text=True)
            if remux.returncode == 0 and os.path.exists(tmp_path):
                os.replace(tmp_path, output_path)

    def _spoof_photo(self, input_path, output_path):
        """Applique micro-transformations visuelles + metadata iPhone EXIF réalistes pour une photo."""
        meta = self._generate_variable_metadata()

        # ── 1. Altérations visuelles avec Pillow ──
        with Image.open(input_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(random.uniform(0.97, 1.03))
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(random.uniform(0.97, 1.03))
            
            width, height = img.size
            crop_pct = random.uniform(0.02, 0.04)
            left = int(width * crop_pct)
            top = int(height * crop_pct)
            right = int(width * (1 - crop_pct))
            bottom = int(height * (1 - crop_pct))
            img = img.crop((left, top, right, bottom))
            
            img.save(output_path, "JPEG", quality=95)

        # ── 2. Injection des attributs EXIF via ExifTool ──
        exiftool_path = self._find_tool("exiftool", ["/opt/homebrew/bin/exiftool", "/usr/local/bin/exiftool"])
        if not exiftool_path:
            raise Exception("ExifTool introuvable ! Ouvrez votre Terminal Mac et tapez : brew install exiftool")

        lat = meta["lat"]
        lon = meta["lon"]
        alt = meta["alt"]
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"
        
        focal_length = random.choice(["24", "48", "13", "120"])
        lens_model = f"{DEVICE_MODEL} back camera 6.86mm f/1.78"
        
        # Commande ExifTool en 2 passes :
        # 1) Strip tout mais recopier la structure JPEG de base (JFIF, ICC)
        # 2) Injecter les tags Apple iPhone
        # NOTE : "-all= -TagsFromFile @" supprime tout puis recopie la structure
        #        du fichier original. Ça garde les headers JFIF/ICC intacts
        #        pour que le MediaScanner Android reconnaisse le JPEG.
        cmd = [
            exiftool_path,
            "-overwrite_original",
            "-all=",
            "-TagsFromFile", "@",
            "-JFIF:ALL",
            "-ICC_Profile:ALL",

            # --- IDENTITÉ FIXE COMPTE (OpSec absolue) ---
            f"-Make=Apple",
            f"-Model={DEVICE_MODEL}",
            f"-Software={DEVICE_SOFTWARE}",
            f"-LensMake=Apple",
            f"-LensModel={lens_model}",

            # --- TEMPS ET SYNCHRO (Miami Strategy) ---
            f"-DateTimeOriginal={meta['datetime_original']}",
            f"-CreateDate={meta['datetime_original']}",
            f"-ModifyDate={meta['datetime_original']}",
            f"-OffsetTime={meta['offset_str']}",
            f"-OffsetTimeOriginal={meta['offset_str']}",
            f"-OffsetTimeDigitized={meta['offset_str']}",
            f"-SubSecTimeOriginal={meta['subsec']}",
            f"-SubSecTimeDigitized={meta['subsec']}",

            # --- GPS VARIABLES (Miami Strategy) ---
            f"-GPSLatitude={abs(lat)}",
            f"-GPSLatitudeRef={lat_ref}",
            f"-GPSLongitude={abs(lon)}",
            f"-GPSLongitudeRef={lon_ref}",
            f"-GPSAltitude={alt}",
            f"-GPSAltitudeRef=0",

            # --- STRUCTURE JPEG pour Android MediaStore ---
            f"-Orientation=Horizontal (normal)",
            f"-ColorSpace=sRGB",
            f"-ExifVersion=0232",
            f"-FlashpixVersion=0100",
            f"-SceneCaptureType=Standard",
            f"-MeteringMode=Multi-segment",
            f"-ExposureProgram=Program AE",
            f"-Flash=Off, Did not fire",
            f"-YCbCrPositioning=Centered",

            # --- MICRO-VARIATIONS PHOTO (Comportement humain naturel) ---
            f"-FocalLengthIn35mmFormat={focal_length}",
            f"-FNumber=1.78",
            f"-ExposureTime={meta['exposure_time']}",
            f"-ISO={meta['iso']}",
            f"-BrightnessValue={meta['brightness_val']}",

            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ExifTool error: {result.stderr[:500] if result.stderr else 'Unknown error'}")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()
