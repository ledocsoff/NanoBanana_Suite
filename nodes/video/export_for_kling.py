import os
import shutil
from ...core import image_utils, file_manager

class NB_ExportForKling:
    OUTPUT_NODE = True
    CATEGORY = "NanaBanana/Video"
    FUNCTION = "export"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("image_path", "video_path")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "video_path": ("STRING", {"forceInput": True}),
                "video_filename": ("STRING", {"forceInput": True}),
                "output_folder": ("STRING", {"forceInput": True}),
                "done_folder": ("STRING", {"forceInput": True}),
                "source_video_path": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "auto_move_source": ("BOOLEAN", {"default": True}),
                "image_format": (["png", "jpg"], {"default": "png"}),
                "copy_video": ("BOOLEAN", {"default": True}),
            }
        }

    def export(self, image, video_path, video_filename, output_folder, done_folder, source_video_path,
               auto_move_source=True, image_format="png", copy_video=True):
        
        file_manager.ensure_folder(output_folder)
        
        # 1. Sauvegarder l'image
        pil_img = image_utils.tensor_to_pil(image)
        img_ext = f".{image_format}"
        image_out_path = os.path.join(output_folder, f"{video_filename}_face{img_ext}")
        
        if image_format == "jpg":
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGB")
            pil_img.save(image_out_path, format="JPEG", quality=95)
        else:
            pil_img.save(image_out_path, format="PNG")
            
        print(f"[NanaBanana] 🖼️ Image sauvegardée : {image_out_path}")

        # 2. Copier la vidéo (optionnel)
        video_out_path = ""
        # The user's input variables have some duplication (video_path vs source_video_path) 
        # so we default to using source_video_path if it exists, else video_path.
        target_video = source_video_path if source_video_path and os.path.exists(source_video_path) else video_path
        
        if copy_video and target_video and os.path.exists(target_video):
            video_ext = os.path.splitext(target_video)[1]
            if not video_ext:
                video_ext = ".mp4"
            video_out_path = os.path.join(output_folder, f"{video_filename}{video_ext}")
            shutil.copy2(target_video, video_out_path)
            print(f"[NanaBanana] 🎞️ Vidéo copiée : {video_out_path}")
            
        # 3. Déplacer la source originale
        if auto_move_source and done_folder and target_video and os.path.exists(target_video):
            file_manager.ensure_folder(done_folder)
            try:
                file_manager.move_file(target_video, done_folder)
                print(f"[NanaBanana] 📦 Source déplacée vers : {done_folder}")
            except Exception as e:
                print(f"[NanaBanana] ⚠️ Erreur lors du déplacement de la source : {e}")
                
        # 4. Logs finaux
        print(f"[NanaBanana] ✅ Export prêt : {video_filename}")
        print(f"   Image → {image_out_path}")
        print(f"   Vidéo → {video_out_path if video_out_path else 'Non copiée'}")
        print(f"   → Upload manuellement sur klingai.com")

        return (image_out_path, video_out_path)
