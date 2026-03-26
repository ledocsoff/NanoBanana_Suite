"""
NB_ProfileFiller — GeeLark "Edit Instagram Profile" template filler
====================================================================
Reads a GeeLark-exported XLSX for profile editing, fills in Biography
(from NB_EmojiBioGen), Nickname, LinkURL, LinkTitle columns.
Outputs a ready-to-reimport XLSX.
"""

from __future__ import annotations

import os
import random
import importlib.util

# Direct import of xlsx_utils to avoid shared/__init__.py (which pulls in torch via gemini_client)
_xlsx_utils_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "shared", "xlsx_utils.py"
)
_spec = importlib.util.spec_from_file_location("xlsx_utils", _xlsx_utils_path)
_xlsx_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_xlsx_utils)

GEELARK_SCHEMAS = _xlsx_utils.GEELARK_SCHEMAS
load_template = _xlsx_utils.load_template
fill_column = _xlsx_utils.fill_column
fill_column_single = _xlsx_utils.fill_column_single
save_template = _xlsx_utils.save_template
get_account_names = _xlsx_utils.get_account_names


class NB_ProfileFiller:
    CATEGORY = "NanaBanana/Tools"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_file",)
    FUNCTION = "fill"
    OUTPUT_NODE = True

    DESCRIPTION = (
        "Fills a GeeLark 'Edit Instagram Profile' XLSX template with biographies, "
        "nicknames, usernames, link URLs and titles. Connect bios from NB_EmojiBioGen."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "template_file": ("STRING", {
                    "default": "",
                    "tooltip": "Chemin du fichier .xlsx 'Edit Instagram profile' exporté depuis GeeLark"
                }),
            },
            "optional": {
                "bios": ("STRING", {
                    "default": "",
                    "forceInput": True,
                    "tooltip": "Bios générées par NB_EmojiBioGen (séparées par ---)"
                }),
                "nicknames": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Pool de nicknames (un par ligne). Vide = pas de changement."
                }),
                "usernames": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Pool de usernames (un par ligne). Vide = pas de changement."
                }),
                "link_url": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Pool d'URL à mettre dans le profil (une par ligne). Vide = pas de changement."
                }),
                "link_title": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Pool de titres de lien (un par ligne). Vide = pas de changement."
                }),
            }
        }

    def fill(self, template_file: str,
             bios: str = "", nicknames: str = "", usernames: str = "",
             link_url: str = "", link_title: str = "") -> tuple[str]:

        schema = GEELARK_SCHEMAS["edit_profile"]

        wb, rows = load_template(template_file, expected_type="edit_profile")
        total = len(rows)

        # Auto-generate output filename
        base_name = os.path.splitext(template_file.strip().strip("'\""))[0]
        output_file = f"{base_name}_filled.xlsx"

        if total == 0:
            print("[NB_ProfileFiller] ⚠ Template vide, rien à remplir.")
            output_path = save_template(wb, output_file)
            return (output_path,)

        accounts = get_account_names(rows)
        print(f"[NB_ProfileFiller] 📝 {total} comptes détectés: {', '.join(accounts[:5])}{'...' if total > 5 else ''}")

        # Fill Biography (col 7)
        if bios and bios.strip():
            bio_list = [b.strip() for b in bios.split("---") if b.strip()]
            if bio_list:
                fill_column(rows, schema["biography"], bio_list, randomize=True)
                print(f"[NB_ProfileFiller] ✓ Bios remplies ({len(bio_list)} disponibles → {total} comptes)")

        # Fill Nickname (col 5)
        if nicknames and nicknames.strip():
            nick_list = [n.strip() for n in nicknames.split('\n') if n.strip()]
            if nick_list:
                fill_column(rows, schema["nickname"], nick_list, randomize=True)
                print(f"[NB_ProfileFiller] ✓ Nicknames remplis ({len(nick_list)} disponibles)")

        # Fill Username (col 6)
        if usernames and usernames.strip():
            user_list = [u.strip() for u in usernames.split('\n') if u.strip()]
            if user_list:
                fill_column(rows, schema["username"], user_list, randomize=True)
                print(f"[NB_ProfileFiller] ✓ Usernames remplis ({len(user_list)} disponibles)")

        # Fill LinkURL (col 8)
        if link_url and link_url.strip():
            url_list = [u.strip() for u in link_url.split('\n') if u.strip()]
            if url_list:
                fill_column(rows, schema["link_url"], url_list, randomize=True)
                print(f"[NB_ProfileFiller] ✓ LinkURLs remplis ({len(url_list)} disponibles)")

        # Fill LinkTitle (col 9)
        if link_title and link_title.strip():
            title_list = [t.strip() for t in link_title.split('\n') if t.strip()]
            if title_list:
                fill_column(rows, schema["link_title"], title_list, randomize=True)
                print(f"[NB_ProfileFiller] ✓ LinkTitles remplis ({len(title_list)} disponibles)")

        output_path = save_template(wb, output_file)
        print(f"[NB_ProfileFiller] ✅ Fichier prêt: {output_path}")
        return (output_path,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()
