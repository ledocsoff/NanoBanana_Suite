import json
import time
import sys
import requests

APIFY_BASE = "https://api.apify.com/v2"

class Omni_ApifyCollector:
    """Scrape Instagram profiles via Apify (apify/instagram-profile-scraper) and return structured stats."""

    CATEGORY = "Omni/Collect"
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("stats_json", "accounts_count")
    FUNCTION = "collect"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "handles": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Un @ Instagram par ligne",
                }),
                "target_media": (["Tous (Automatique)", "Dernier Reel / Vidéo", "Dernière Image / Carrousel"], {
                    "default": "Tous (Automatique)",
                    "tooltip": "Sélectionne le type de média à analyser",
                }),
                "apify_token": ("STRING", {
                    "default": "",
                    "tooltip": "Token API Apify",
                }),
            },
            "optional": {
                "poll_interval": ("INT", {
                    "default": 5,
                    "min": 1,
                    "max": 30,
                    "tooltip": "Secondes entre chaque vérification du statut",
                }),
                "timeout_s": ("INT", {
                    "default": 1200,
                    "min": 10,
                    "max": 10800,
                    "tooltip": "Timeout en secondes (100 cpts = 1200 / 1000 cpts = 7200)",
                }),
            },
        }

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def collect(
        self,
        handles: str,
        target_media: str,
        apify_token: str,
        poll_interval: int = 5,
        timeout_s: int = 1200,
    ):
        if not apify_token or not apify_token.strip():
            raise RuntimeError("[Omni_Collect] ❌ Erreur : apify_token est vide.")

        usernames = self._parse_handles(handles)
        total_requested = len(usernames)
        if total_requested == 0:
            raise RuntimeError("[Omni_Collect] ❌ Erreur : Aucun handle valide fourni.")

        print(f"\n[Omni_Collect] 🚀 Lancement d'Apify (instagram-profile-scraper)...")
        print(f"[Omni_Collect] 📊 Cible : {total_requested} compte(s) | Filtre : {target_media}")

        run_id = self._start_run(apify_token, usernames)
        dataset_id = self._poll_until_done(apify_token, run_id, poll_interval, timeout_s)
        items = self._fetch_dataset(apify_token, dataset_id)
        
        stats = self._extract_stats(items, target_media)
        total_recovered = len(stats)

        print(f"[Omni_Collect] ✅ Collecte terminée !")
        print(f"[Omni_Collect] 📈 Taux de réussite : {total_recovered} comptes récupérés sur {total_requested} demandés.")
        
        if total_recovered < total_requested:
            print(f"[Omni_Collect] ⚠️ {total_requested - total_recovered} compte(s) n'ont pas renvoyé de données (introuvables ou privés).")

        # Inject the chosen filter globally in the JSON for the Report node
        output_data = {
            "metadata": {"filter_applied": target_media},
            "stats": stats
        }

        stats_json = json.dumps(output_data, indent=2, ensure_ascii=False)
        return (stats_json, total_recovered)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_handles(raw: str) -> list[str]:
        cleaned = []
        for line in raw.splitlines():
            h = line.strip().lstrip("@").strip()
            if h:
                cleaned.append(h)
        return cleaned

    @staticmethod
    def _start_run(token: str, usernames: list[str]) -> str:
        actor_id = "apify~instagram-profile-scraper"
        url = f"{APIFY_BASE}/acts/{actor_id}/runs"
        
        payload = {
            "usernames": usernames,
        }
        
        try:
            resp = requests.post(
                url,
                json=payload,
                params={"token": token},
                timeout=30,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_msg = getattr(e.response, "text", str(e))
            raise RuntimeError(f"[Omni_Collect] ❌ Échec du lancement Apify : {error_msg[:300]}")
            
        data = resp.json().get("data", {})
        run_id = data.get("id")
        if not run_id:
            raise RuntimeError(f"[Omni_Collect] ❌ Réponse inattendue, pas d'ID de tâche Apify retourné.")
            
        print(f"[Omni_Collect] 🔌 Tâche Apify initiée [Run ID: {run_id}]")
        return run_id

    @staticmethod
    def _poll_until_done(token: str, run_id: str, interval: int, timeout: int) -> str:
        url = f"{APIFY_BASE}/actor-runs/{run_id}"
        start_time = time.time()
        deadline = start_time + timeout
        terminal_fail = {"FAILED", "ABORTED", "TIMED-OUT"}

        print("[Omni_Collect] ⏳ En attente de la récolte de données (Cela peut prendre plusieurs minutes)...")

        while True:
            current_time = time.time()
            elapsed_s = int(current_time - start_time)
            
            if current_time > deadline:
                raise RuntimeError(
                    f"\n[Omni_Collect] ❌ Timeout métier ({timeout}s) dépassé pour la tâche {run_id}. Pensez à l'augmenter pour les longues listes."
                )
                
            try:
                resp = requests.get(url, params={"token": token}, timeout=15)
                resp.raise_for_status()
            except requests.exceptions.RequestException:
                time.sleep(interval) 
                continue
                
            data = resp.json().get("data", {})
            status = data.get("status", "UNKNOWN")

            sys.stdout.write(f"\r[Omni_Collect] ⏱️ Durée : {elapsed_s}s | Statut Apify : {status.ljust(15)}")
            sys.stdout.flush()

            if status == "SUCCEEDED":
                print() 
                dataset_id = data.get("defaultDatasetId")
                if not dataset_id:
                    raise RuntimeError("\n[Omni_Collect] ❌ Tâche réussie mais le Dataset est introuvable.")
                return dataset_id

            if status in terminal_fail:
                print() 
                raise RuntimeError(f"\n[Omni_Collect] ❌ Échec définitif de la tâche Apify : {status}")

            time.sleep(interval)

    @staticmethod
    def _fetch_dataset(token: str, dataset_id: str) -> list[dict]:
        url = f"{APIFY_BASE}/datasets/{dataset_id}/items"
        resp = requests.get(url, params={"token": token, "format": "json"}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _extract_stats(items: list[dict], target_media: str) -> list[dict]:
        stats = []
        for item in items:
            if "error" in item and not "username" in item:
                continue

            username = item.get("username") or item.get("ownerUsername", "Inconnu")
            followers = item.get("followersCount", 0)
            
            latest_posts = item.get("latestPosts", [])
            valid_post = None
            
            if latest_posts and isinstance(latest_posts, list):
                # 1. On trie tous les posts récupérés par timestamp DESCENDANT de force !
                # Ça ignore totalement l'ordre de l'API et repousse les "épinglés" à leur vraie place temporelle.
                try:
                    # On trie seulement ceux qui ont un timestamp
                    sorted_posts = sorted(
                        [p for p in latest_posts if p.get("timestamp")],
                        key=lambda x: x["timestamp"], 
                        reverse=True
                    )
                except Exception:
                    # Sécurité si un timestamp est manquant/bancal, on garde la liste
                    sorted_posts = latest_posts

                # 2. Filtrage selon le format demandé
                for p in sorted_posts:
                    post_type = p.get("type", "")
                    # Si c'est "Tous", on prend le premier qui passe (donc le plus récent)
                    if target_media == "Tous (Automatique)":
                        valid_post = p
                        break
                    # Si on veut un Reel / Vidéo
                    elif target_media == "Dernier Reel / Vidéo":
                        if post_type == "Video" or p.get("isVideo", False):
                            valid_post = p
                            break
                    # Si on veut une Image / Carrousel
                    elif target_media == "Dernière Image / Carrousel":
                        if post_type in ("Image", "Sidecar") and not p.get("isVideo", False):
                            valid_post = p
                            break

            if valid_post:
                url = valid_post.get("url")
                if not url and valid_post.get("shortCode"):
                    url = f"https://www.instagram.com/p/{valid_post.get('shortCode')}/"
                    
                stats.append({
                    "username": username,
                    "post_url": url or "",
                    "likes": valid_post.get("likesCount", 0),
                    "comments": valid_post.get("commentsCount", 0),
                    "videoViewCount": valid_post.get("videoViewCount", 0),
                    "videoPlayCount": valid_post.get("videoPlayCount", 0),
                    "timestamp": valid_post.get("timestamp", ""),
                    "type": valid_post.get("type", "Post"),
                    "followersCount": followers,
                })
            else:
                stats.append({
                    "username": username,
                    "post_url": f"https://instagram.com/{username}",
                    "likes": 0,
                    "comments": 0,
                    "videoViewCount": 0,
                    "videoPlayCount": 0,
                    "timestamp": "",
                    "type": "Aucun Média Trouvé",
                    "followersCount": followers,
                })

        return stats

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()


NODE_CLASS_MAPPINGS = {
    "Omni_ApifyCollector": Omni_ApifyCollector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Omni_ApifyCollector": "Apify Collector",
}
