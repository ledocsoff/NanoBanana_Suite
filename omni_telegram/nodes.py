"""
omni_telegram — ComfyUI custom nodes for Telegram invite link management.

Nodes:
  1. Omni_TelegramBulkInviteLinks  — Bulk-create invite links via Bot API
  2. Omni_TelegramExportCSV        — Export link data to CSV
  3. Omni_TelegramLinkAnalytics    — Fetch live stats + generate report

All API calls use POST. Rate-limit (HTTP 429) is handled with automatic retry.
"""

import csv
import os
import time as _time
from datetime import datetime, timedelta, timezone

import requests


# ─────────────────────────────────────────────────────────────────
# Shared Helpers
# ─────────────────────────────────────────────────────────────────

def _validate_channel_id(channel_id: str) -> str:
    """Validate and normalize channel_id format."""
    channel_id = channel_id.strip()
    if not channel_id:
        raise ValueError("[OmniTelegram] ❌ channel_id est vide.")
    if channel_id.startswith("@"):
        return channel_id
    if channel_id.startswith("-100"):
        return channel_id
    # Try to fix common mistake: missing -100 prefix
    if channel_id.lstrip("-").isdigit() and not channel_id.startswith("-100"):
        raise ValueError(
            f"[OmniTelegram] ❌ channel_id invalide: '{channel_id}'. "
            "Format attendu: -100xxxxxxxxxx ou @username"
        )
    raise ValueError(
        f"[OmniTelegram] ❌ channel_id invalide: '{channel_id}'. "
        "Format attendu: -100xxxxxxxxxx ou @username"
    )


def _load_bot_token(bot_token: str) -> str:
    """Validate and return the bot token."""
    token = bot_token.strip()
    if not token:
        raise ValueError("[OmniTelegram] ❌ bot_token est vide.")
    return token


def _mask_token(url: str) -> str:
    """Mask bot token in URL for safe logging."""
    if "/bot" in url:
        parts = url.split("/bot", 1)
        if len(parts) == 2 and "/" in parts[1]:
            token, rest = parts[1].split("/", 1)
            masked = token[:5] + "..." + token[-4:] if len(token) > 12 else "***"
            return f"{parts[0]}/bot{masked}/{rest}"
    return url


def _api_post(url: str, params: dict, max_retries: int = 3) -> dict:
    """POST to Telegram Bot API with automatic 429 retry handling.

    429 rate-limits are retried indefinitely (not counted as failures).
    Only network errors consume the retry counter.
    Returns the parsed JSON response dict.
    Raises RuntimeError on persistent failure.
    """
    network_errors = 0

    while True:
        try:
            resp = requests.post(url, json=params, timeout=30)
        except requests.RequestException as e:
            network_errors += 1
            print(f"[OmniTelegram] ⚠️ Erreur réseau (tentative {network_errors}/{max_retries}): {e}")
            if network_errors >= max_retries:
                raise RuntimeError(
                    f"[OmniTelegram] ❌ Échec réseau après {max_retries} tentatives "
                    f"sur {_mask_token(url)}: {e}"
                )
            _time.sleep(2 * network_errors)
            continue

        if resp.status_code == 429:
            try:
                data = resp.json()
            except ValueError:
                data = {}
            retry_after = data.get("parameters", {}).get("retry_after", 5)
            print(f"[OmniTelegram] ⏳ Rate-limited (429). Attente de {retry_after}s...")
            _time.sleep(retry_after)
            continue

        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(
                f"[OmniTelegram] ❌ Réponse non-JSON (HTTP {resp.status_code}) "
                f"sur {_mask_token(url)}: {resp.text[:200]}"
            )

        if not data.get("ok"):
            error_desc = data.get("description", "Unknown error")
            raise RuntimeError(f"[OmniTelegram] API error: {error_desc}")

        return data


# ─────────────────────────────────────────────────────────────────
# Node 0: Global Configuration Hub
# ─────────────────────────────────────────────────────────────────

class Omni_TelegramConfig:
    """Central Configuration for all Telegram nodes."""

    CATEGORY = "Omni/Telegram"
    INPUT_IS_LIST = False
    RETURN_TYPES = ("TELEGRAM_CONFIG",)
    RETURN_NAMES = ("config",)
    FUNCTION = "get_config"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "bot_token": ("STRING", {
                    "default": "",
                    "tooltip": "Token global du bot Telegram."
                }),
                "channel_id": ("STRING", {
                    "default": "",
                    "tooltip": "ID global du channel (-100xxxxxxxxxx ou @username)"
                }),
                "db_directory": ("STRING", {
                    "default": "/Users/quentin/Desktop/Omni_Databases",
                    "tooltip": "Dossier central de la base de données SQL"
                }),
            }
        }

    def get_config(self, bot_token, channel_id, db_directory):
        return ({"bot_token": bot_token.strip(), "channel_id": channel_id.strip(), "db_dir": db_directory.strip()},)


# ─────────────────────────────────────────────────────────────────
# Node 1: Bulk Invite Link Generator
# ─────────────────────────────────────────────────────────────────

class Omni_TelegramBulkInviteLinks:
    """Create one invite link per account name via Telegram Bot API."""

    CATEGORY = "Omni/Telegram"
    INPUT_IS_LIST = False
    RETURN_TYPES = ("TELEGRAM_LINKS_DATA", "STRING")
    RETURN_NAMES = ("links_data", "summary")
    FUNCTION = "generate_links"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config": ("TELEGRAM_CONFIG", {
                    "tooltip": "Reliez à la sortie de Omni_TelegramConfig"
                }),
                "account_names": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Un nom de compte par ligne. Chaque nom sera associé à un lien unique."
                }),
            },
            "optional": {
                "member_limit": ("INT", {
                    "default": 0,
                    "min": 0,
                    "tooltip": "Limite de membres par lien. 0 = illimité. ⚠️ 1 = lien à usage unique."
                }),
                "expire_days": ("INT", {
                    "default": 0,
                    "min": 0,
                    "tooltip": "Expiration en jours. 0 = pas d'expiration."
                }),
                "request_approval": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Si True, l'utilisateur devra être approuvé manuellement par un admin."
                }),
            },
        }

    def generate_links(self, config, account_names,
                       member_limit=0, expire_days=0, request_approval=False):
        token = _load_bot_token(config.get("bot_token", ""))
        chat_id = _validate_channel_id(config.get("channel_id", ""))

        names = [n.strip() for n in account_names.strip().splitlines() if n.strip()]
        if not names:
            raise ValueError("[OmniTelegram] ❌ Aucun nom de compte fourni (account_names vide).")

        if member_limit == 1:
            print("[OmniTelegram] ⚠️ member_limit=1 : chaque lien sera à usage unique (grillé après 1 join).")

        url = f"https://api.telegram.org/bot{token}/createChatInviteLink"
        results = []
        errors = 0

        for i, name in enumerate(names):
            params = {"chat_id": chat_id, "name": name}

            if request_approval:
                params["creates_join_request"] = True
            elif member_limit > 0:
                # Telegram API interdit d'avoir member_limit ET creates_join_request en même temps
                params["member_limit"] = member_limit

            if expire_days > 0:
                expire_ts = int((datetime.now(timezone.utc) + timedelta(days=expire_days)).timestamp())
                params["expire_date"] = expire_ts

            try:
                data = _api_post(url, params)
                link_info = data.get("result", {})
                results.append({
                    "account_name": name,
                    "invite_link": link_info.get("invite_link", ""),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                print(f"[OmniTelegram] ✅ [{i+1}/{len(names)}] {name}: {link_info.get('invite_link', '???')}")
            except Exception as e:
                errors += 1
                print(f"[OmniTelegram] ❌ [{i+1}/{len(names)}] {name}: {e}")

            if i < len(names) - 1:
                _time.sleep(0.5)

        # Auto-persist to SQLite DB
        if results:
            import sqlite3
            db_directory = config.get("db_dir", "/Users/quentin/Desktop/Omni_Databases")
            os.makedirs(db_directory, exist_ok=True)
            db_path = os.path.join(db_directory, "telegram_master.db")
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS links (
                        account_name TEXT PRIMARY KEY,
                        invite_link TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        joins INTEGER DEFAULT 0,
                        last_checked TEXT
                    )
                ''')
                for r in results:
                    cursor.execute('''
                        INSERT INTO links (account_name, invite_link, created_at, status)
                        VALUES (?, ?, ?, 'active')
                        ON CONFLICT(account_name) DO UPDATE SET
                            invite_link = excluded.invite_link,
                            status = 'active'
                    ''', (r["account_name"], r["invite_link"], r["created_at"]))
                conn.commit()
            print(f"[OmniTelegram] 💾 {len(results)} liens sauvegardés automatiquement dans la DB.")

        # Build summary
        lines = [f"[OmniTelegram] Résumé: {len(results)} liens créés, {errors} erreurs."]
        for r in results:
            lines.append(f"  {r['account_name']}: {r['invite_link']}")
        summary = "\n".join(lines)

        print(f"[OmniTelegram] 📊 Terminé: {len(results)}/{len(names)} liens créés.")
        return (results, summary)


# ─────────────────────────────────────────────────────────────────
# Node 2: CSV Export
# ─────────────────────────────────────────────────────────────────

class Omni_TelegramExportCSV:
    """Export TELEGRAM_LINKS_DATA to a CSV file in the specified directory."""

    CATEGORY = "Omni/Telegram"
    INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filepath",)
    FUNCTION = "export_csv"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config": ("TELEGRAM_CONFIG",),
                "links_data": ("TELEGRAM_LINKS_DATA",),
                "save_directory": ("STRING", {
                    "default": "/Users/quentin/Desktop/Omni_Reports/Telegram_Exports",
                    "tooltip": "Dossier où le fichier CSV sera généré."
                }),
            },
        }

    def export_csv(self, config, links_data, save_directory):
        if not links_data:
            print("[OmniTelegram] ⚠️ links_data vide, aucun CSV généré.")
            return ("",)

        timestamp_str = datetime.now().strftime("%Y-%m-%d_%Hh%Mm%S")
        filename = f"telegram_export_{timestamp_str}.csv"
        
        os.makedirs(save_directory, exist_ok=True)
        filepath = os.path.join(save_directory, filename)

        # Détection dynamique des colonnes de données pour être 100% universel
        fieldnames = []
        for row in links_data:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in links_data:
                writer.writerow(row)

        print(f"[OmniTelegram] 📁 CSV exporté: {filepath} ({len(links_data)} lignes)")
        return (filepath,)


# ─────────────────────────────────────────────────────────────────
# Node 3: Link Analytics
# ─────────────────────────────────────────────────────────────────

class Omni_TelegramLinkAnalytics:
    """Fetch live stats for each invite link and generate a report."""

    CATEGORY = "Omni/Telegram"
    INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING", "TELEGRAM_LINKS_DATA")
    RETURN_NAMES = ("report_path", "analytics_data")
    FUNCTION = "fetch_analytics"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config": ("TELEGRAM_CONFIG",),
                "links_data": ("TELEGRAM_LINKS_DATA",),
                "save_directory": ("STRING", {
                    "default": "/Users/quentin/Desktop/Omni_Reports",
                    "tooltip": "Chemin du dossier où le rapport HTML sera sauvegardé",
                }),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return _time.time()

    def fetch_analytics(self, config, links_data, save_directory):
        token = _load_bot_token(config.get("bot_token", ""))
        chat_id = _validate_channel_id(config.get("channel_id", ""))

        if not links_data:
            return ("[OmniTelegram] Aucune donnée de liens à analyser.", [])

        # editChatInviteLink retourne l'objet ChatInviteLink avec usage stats
        # sans modifier le lien. On renvoie le même name pour ne rien changer.
        url = f"https://api.telegram.org/bot{token}/editChatInviteLink"
        analytics = []

        for i, link_entry in enumerate(links_data):
            account_name = link_entry.get("account_name", "unknown")
            invite_link = link_entry.get("invite_link", "")

            if not invite_link:
                print(f"[OmniTelegram] ⚠️ [{i+1}/{len(links_data)}] {account_name}: lien vide, ignoré.")
                continue

            params = {
                "chat_id": chat_id,
                "invite_link": invite_link,
                "name": account_name,
            }

            try:
                data = _api_post(url, params)
                result = data.get("result", {})
                analytics.append({
                    "account_name": account_name,
                    "invite_link": invite_link,
                    "joins": result.get("usage", 0) or 0,
                    "pending_requests": result.get("pending_join_request_count", 0) or 0,
                    "is_revoked": result.get("is_revoked", False),
                    "expire_date": result.get("expire_date", ""),
                    "created_at": link_entry.get("created_at", ""),
                })
                print(f"[OmniTelegram] 📊 [{i+1}/{len(links_data)}] {account_name}: "
                      f"{result.get('usage', 0)} joins")
            except Exception as e:
                print(f"[OmniTelegram] ❌ [{i+1}/{len(links_data)}] {account_name}: {e}")
                analytics.append({
                    "account_name": account_name,
                    "invite_link": invite_link,
                    "joins": 0,
                    "pending_requests": 0,
                    "is_revoked": False,
                    "expire_date": "",
                    "created_at": link_entry.get("created_at", ""),
                })

            if i < len(links_data) - 1:
                _time.sleep(0.3)

        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%Hh%Mm%S")
        file_name = f"telegram_analytics_{timestamp_str}.html"

        os.makedirs(save_directory, exist_ok=True)
        file_path = os.path.join(save_directory, file_name)

        html_content = self._build_html(analytics, now)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[OmniTelegram] 📁 Analytics HTML Report généré: {file_path}")
        return (file_path, analytics)

    def _build_html(self, analytics: list, gen_date: datetime) -> str:
        date_str = gen_date.strftime("%d/%m/%Y à %H:%M:%S")
        total_links = len(analytics)
        total_joins = sum(a["joins"] for a in analytics)
        avg_joins = round(total_joins / total_links) if total_links else 0
        active_links = sum(1 for a in analytics if not a["is_revoked"])

        # Top converter
        top_name = "N/A"
        if analytics:
            best = max(analytics, key=lambda x: x["joins"])
            if best["joins"] > 0:
                top_name = best["account_name"]

        # Build table rows
        rows_html = ""
        for i, a in enumerate(analytics, 1):
            acc = a["account_name"]
            link = a["invite_link"]
            joins = a["joins"]
            pending = a["pending_requests"]
            is_revoked = a["is_revoked"]
            created = a["created_at"][:10] if a.get("created_at") else "—"

            status_badge = '<span class="badge badge-error">Révoqué</span>' if is_revoked else '<span class="badge badge-success">Actif</span>'
            joins_class = "val-high" if joins >= 100 else "val-mid" if joins >= 10 else ""

            # Secure the HTML content
            import html as html_module
            safe_acc = html_module.escape(acc)

            rows_html += f"""
            <tr data-user="{safe_acc.lower()}" data-joins="{joins}" data-pending="{pending}">
                <td class="col-rank">{i}</td>
                <td class="col-user">{safe_acc}</td>
                <td class="col-joins {joins_class}" data-sort="{joins}">{joins}</td>
                <td class="col-pending" data-sort="{pending}">{pending}</td>
                <td class="col-status">{status_badge}</td>
                <td class="col-date">{created}</td>
                <td class="col-link"><a href="{link}" target="_blank" class="link-btn">↗</a></td>
            </tr>"""

        # Prepare CSV data for Javascript export
        import json as json_module
        csv_headers = "Rang,Compte,Lien,Joins,Pending,Status,Date_Creation"
        csv_rows = []
        for idx, a in enumerate(analytics, 1):
            status = "Révoqué" if a["is_revoked"] else "Actif"
            csv_rows.append([
                idx, a["account_name"], a["invite_link"],
                a["joins"], a["pending_requests"], status,
                (a.get("created_at", "")[:10] if a.get("created_at") else "")
            ])
        csv_rows_js = json_module.dumps(csv_rows)

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Omni Telegram Analytics</title>
<style>
:root {{
    --bg: #0b0d10;
    --surface: #14171e;
    --surface-alt: #191d27;
    --border: #252a35;
    --text: #e8eaed;
    --text-dim: #8b919a;
    --accent: #5e6ad2;
    --accent-glow: rgba(94,106,210,0.15);
    --green: #34d399;
    --red: #ef4444;
}}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.5;
}}
.wrap {{ max-width:1440px; margin:0 auto; padding:32px 24px; }}

header {{ text-align:center; margin-bottom:32px; }}
h1 {{
    font-size:2rem; font-weight:800; letter-spacing:-0.5px;
    background: linear-gradient(135deg, #fff 0%, #888 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.meta {{ color:var(--text-dim); margin-top:6px; font-size:0.9rem; }}

.kpis {{
    display:grid; grid-template-columns:repeat(5,1fr); gap:16px;
    margin-bottom:24px;
}}
.kpi {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:12px; padding:20px; text-align:center;
}}
.kpi .num {{ font-size:1.75rem; font-weight:800; color:#fff; }}
.kpi .lbl {{ font-size:0.75rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:1px; margin-top:4px; }}

.toolbar {{
    display:flex; align-items:center; gap:12px;
    margin-bottom:16px; flex-wrap:wrap;
}}
.search-box {{
    flex:1; min-width:200px; padding:10px 14px;
    background:var(--surface); border:1px solid var(--border);
    border-radius:8px; color:var(--text); font-size:0.9rem;
    outline:none; transition:border 0.2s;
}}
.search-box:focus {{ border-color:var(--accent); }}
.search-box::placeholder {{ color:var(--text-dim); }}
.btn-csv {{
    padding:10px 18px; background:var(--accent); color:#fff;
    border:none; border-radius:8px; cursor:pointer;
    font-size:0.85rem; font-weight:600; transition:opacity 0.2s;
}}
.btn-csv:hover {{ opacity:0.85; }}
.counter {{ color:var(--text-dim); font-size:0.85rem; margin-left:auto; }}

.table-wrap {{
    overflow-x:auto; border:1px solid var(--border);
    border-radius:12px; background:var(--surface);
}}
table {{ width:100%; border-collapse:collapse; }}
thead th {{
    position:sticky; top:0; z-index:2;
    background:var(--surface-alt); color:var(--text-dim);
    font-size:0.7rem; font-weight:600; text-transform:uppercase;
    letter-spacing:0.8px; padding:12px 14px; text-align:left;
    border-bottom:1px solid var(--border); cursor:pointer;
    user-select:none; white-space:nowrap;
}}
thead th:hover {{ color:var(--text); }}
thead th .arrow {{ margin-left:4px; font-size:0.6rem; }}
tbody tr {{
    border-bottom:1px solid rgba(255,255,255,0.03);
    transition: background 0.15s;
}}
tbody tr:nth-child(even) {{ background:rgba(255,255,255,0.015); }}
tbody tr:hover {{ background:rgba(94,106,210,0.08); }}
td {{ padding:10px 14px; white-space:nowrap; }}

.col-rank {{ color:var(--text-dim); font-size:0.8rem; width:40px; text-align:center; }}
.col-user {{ font-weight:600; }}
.col-date {{ color:var(--text-dim); font-size:0.85rem; }}

.val-high {{ color:var(--green); font-weight:700; }}
.val-mid {{ color:#facc15; }}

.badge {{
    padding: 2px 8px; border-radius: 999px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
}}
.badge-success {{ background: rgba(52,211,153,0.15); color: var(--green); }}
.badge-error {{ background: rgba(239,68,68,0.15); color: var(--red); }}

.link-btn {{
    display:inline-flex; align-items:center; justify-content:center;
    width:28px; height:28px; border-radius:6px;
    background:rgba(255,255,255,0.06); color:var(--text-dim);
    text-decoration:none; font-size:0.8rem; transition:all 0.15s;
}}
.link-btn:hover {{ background:var(--accent); color:#fff; }}

@media (max-width:768px) {{
    .kpis {{ grid-template-columns:repeat(2,1fr); }}
    .wrap {{ padding:16px 12px; }}
}}
</style>
</head>
<body>
<div class="wrap">
    <header>
        <h1>Omni Telegram Analytics</h1>
        <div class="meta">Généré le {date_str} • Analyse des liens d'invitation</div>
    </header>

    <div class="kpis">
        <div class="kpi"><div class="num">{total_joins}</div><div class="lbl">Joins Totaux</div></div>
        <div class="kpi"><div class="num">{total_links}</div><div class="lbl">Liens suivis</div></div>
        <div class="kpi"><div class="num">{active_links}</div><div class="lbl">Liens Actifs</div></div>
        <div class="kpi"><div class="num">{avg_joins}</div><div class="lbl">Moy. Joins / Lien</div></div>
        <div class="kpi"><div class="num" style="font-size:1.2rem; padding-top:10px;">{top_name[:12]}</div><div class="lbl">Top Conversion</div></div>
    </div>

    <div class="toolbar">
        <input type="text" class="search-box" id="search" placeholder="🔍 Rechercher un compte..." autocomplete="off">
        <button class="btn-csv" onclick="exportCSV()">📥 Export CSV</button>
        <span class="counter" id="counter">{total_links} / {total_links} liens</span>
    </div>

    <div class="table-wrap">
        <table id="dataTable">
            <thead>
                <tr>
                    <th data-col="0" data-type="num"># <span class="arrow"></span></th>
                    <th data-col="1" data-type="str">Compte <span class="arrow"></span></th>
                    <th data-col="2" data-type="num">Joins <span class="arrow"></span></th>
                    <th data-col="3" data-type="num">Pending <span class="arrow"></span></th>
                    <th data-col="4" data-type="str">Statut <span class="arrow"></span></th>
                    <th data-col="5" data-type="str">Date <span class="arrow"></span></th>
                    <th>Lien</th>
                </tr>
            </thead>
            <tbody id="tableBody">
                {rows_html}
            </tbody>
        </table>
    </div>
</div>

<script>
// Search
const searchInput = document.getElementById('search');
const tableBody = document.getElementById('tableBody');
const counter = document.getElementById('counter');
const totalRows = {total_links};

searchInput.addEventListener('input', function() {{
    const q = this.value.toLowerCase();
    let visible = 0;
    const rows = tableBody.querySelectorAll('tr');
    rows.forEach(row => {{
        const user = row.getAttribute('data-user') || '';
        const show = user.includes(q);
        row.style.display = show ? '' : 'none';
        if (show) visible++;
    }});
    counter.textContent = visible + ' / ' + totalRows + ' liens';
}});

// Sort
let currentSort = {{ col: -1, asc: true }};
document.querySelectorAll('thead th[data-col]').forEach(th => {{
    th.addEventListener('click', function() {{
        const col = parseInt(this.dataset.col);
        const type = this.dataset.type;
        const asc = currentSort.col === col ? !currentSort.asc : true;
        currentSort = {{ col, asc }};

        document.querySelectorAll('thead th .arrow').forEach(a => a.textContent = '');
        this.querySelector('.arrow').textContent = asc ? ' ▲' : ' ▼';

        const rows = Array.from(tableBody.querySelectorAll('tr'));
        rows.sort((a, b) => {{
            let va, vb;
            if (type === 'num') {{
                const cellA = a.children[col];
                const cellB = b.children[col];
                va = parseFloat(cellA.dataset.sort || cellA.textContent) || 0;
                vb = parseFloat(cellB.dataset.sort || cellB.textContent) || 0;
            }} else {{
                va = a.children[col].textContent.toLowerCase();
                vb = b.children[col].textContent.toLowerCase();
            }}
            if (va < vb) return asc ? -1 : 1;
            if (va > vb) return asc ? 1 : -1;
            return 0;
        }});

        rows.forEach((row, i) => {{
            row.children[0].textContent = i + 1;
            tableBody.appendChild(row);
        }});
    }});
}});

// Export CSV
const csvData = {csv_rows_js};
function exportCSV() {{
    let csv = "{csv_headers}\\n";
    csvData.forEach(row => {{
        csv += row.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',') + '\\n';
    }});
    const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'telegram_analytics_{gen_date.strftime("%Y%m%d")}.csv';
    link.click();
}}
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────
# Node 4: Revoke Invite Links
# ─────────────────────────────────────────────────────────────────

class Omni_TelegramRevokeLinks:
    """Revoke invite links by name — reads from Master DB, revokes via API, updates DB automatically."""

    CATEGORY = "Omni/Telegram"
    INPUT_IS_LIST = False
    RETURN_TYPES = ("STRING", "TELEGRAM_LINKS_DATA")
    RETURN_NAMES = ("summary", "revoked_data")
    FUNCTION = "revoke_links"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config": ("TELEGRAM_CONFIG",),
                "account_names": ("STRING", {
                    "multiline": True,
                    "default": "mia_tinder_1\nmia_bumble_2",
                    "tooltip": "Liste des noms de comptes à révoquer (un par ligne)."
                }),
            },
        }

    def revoke_links(self, config, account_names):
        import sqlite3
        token = _load_bot_token(config.get("bot_token", ""))
        chat_id = _validate_channel_id(config.get("channel_id", ""))
        db_directory = config.get("db_dir", "/Users/quentin/Desktop/Omni_Databases")

        target_names = [n.strip() for n in account_names.replace(",", "\n").split("\n") if n.strip()]
        if not target_names:
            return ("[OmniTelegram] Aucun nom de compte fourni.",)

        db_path = os.path.join(db_directory, "telegram_master.db")
        links_data = []

        if os.path.exists(db_path):
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' for _ in target_names)
                cursor.execute(f"SELECT account_name, invite_link FROM links WHERE status = 'active' AND account_name IN ({placeholders})", target_names)
                rows = cursor.fetchall()
                links_data = [{"account_name": r[0], "invite_link": r[1]} for r in rows]

        if not links_data:
            not_found = [n for n in target_names]
            return (f"[OmniTelegram] ⚠️ Aucun compte actif trouvé dans la DB pour: {', '.join(not_found)}",)

        url = f"https://api.telegram.org/bot{token}/revokeChatInviteLink"
        revoked_count = 0
        error_count = 0
        csv_results = []
        revoked_invite_links = []

        for i, link_entry in enumerate(links_data):
            account_name = link_entry.get("account_name", "unknown")
            invite_link = link_entry.get("invite_link", "")

            if not invite_link:
                continue

            params = {"chat_id": chat_id, "invite_link": invite_link}
            status = "FAILED"

            try:
                _api_post(url, params)
                revoked_count += 1
                status = "REVOKED_SUCCESSFULLY"
                revoked_invite_links.append(invite_link)
                print(f"[OmniTelegram] 🗑️ [{i+1}/{len(links_data)}] {account_name}: Lien révoqué.")
            except Exception as e:
                error_count += 1
                status = f"ERROR: {e}"
                print(f"[OmniTelegram] ❌ [{i+1}/{len(links_data)}] {account_name}: {e}")

            csv_results.append({
                "account_name": account_name,
                "invite_link": invite_link,
                "status": status,
                "revoked_at": datetime.now(timezone.utc).isoformat()
            })

            if i < len(links_data) - 1:
                _time.sleep(0.3)

        # Auto-update de la DB : marquer les liens révoqués avec succès
        if revoked_invite_links and os.path.exists(db_path):
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                for inv_link in revoked_invite_links:
                    cursor.execute("UPDATE links SET status = 'revoked' WHERE invite_link = ?", (inv_link,))
                conn.commit()
            print(f"[OmniTelegram] 💾 DB mise à jour automatiquement: {len(revoked_invite_links)} liens marqués 'revoked'.")

        summary = (
            f"═══ Telegram Revoke Summary ═══\n"
            f"Comptes ciblés: {len(links_data)}\n"
            f"✅ Révoqués + DB mise à jour: {revoked_count}\n"
            f"❌ Erreurs: {error_count}\n"
        )
        print(f"[OmniTelegram] 🧹 Révocation terminée. {revoked_count} liens détruits et DB synchronisée.")
        return (summary, csv_results)


# ─────────────────────────────────────────────────────────────────
# Node 5: DB Reader (lecture seule)
# ─────────────────────────────────────────────────────────────────

class Omni_TelegramDBReader:
    """Read-only access to the Telegram Master DB. Outputs all active links for Analytics or Export."""

    CATEGORY = "Omni/Telegram"
    INPUT_IS_LIST = False
    RETURN_TYPES = ("TELEGRAM_LINKS_DATA", "STRING")
    RETURN_NAMES = ("links_data", "summary")
    FUNCTION = "read_db"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "config": ("TELEGRAM_CONFIG",),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return _time.time()

    def read_db(self, config):
        import sqlite3

        db_directory = config.get("db_dir", "/Users/quentin/Desktop/Omni_Databases")
        db_path = os.path.join(db_directory, "telegram_master.db")

        if not os.path.exists(db_path):
            return ([], f"[OmniTelegram] ⚠️ Base introuvable: {db_path}")

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT account_name, invite_link, created_at, status FROM links WHERE status = 'active'")
            rows = cursor.fetchall()
            out_data = [{"account_name": r[0], "invite_link": r[1], "created_at": r[2]} for r in rows]

        summary = (
            f"═══ Telegram DB Reader ═══\n"
            f"Base: {db_path}\n"
            f"Liens actifs: {len(out_data)}\n"
        )
        print(f"[OmniTelegram] 📚 DB Reader: {len(out_data)} liens actifs chargés.")

        return (out_data, summary)

