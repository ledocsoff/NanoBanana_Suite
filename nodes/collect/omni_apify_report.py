import os
import json
import time
from datetime import datetime


class Omni_ApifyReport:
    """Transform Apify JSON stats into a professional HTML dashboard report."""

    CATEGORY = "Omni/Collect"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("report_path",)
    FUNCTION = "generate_report"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "stats_json": ("STRING", {
                    "forceInput": True,
                    "tooltip": "Le JSON sortant de l'Omni_ApifyCollector",
                }),
                "save_directory": ("STRING", {
                    "default": "/Users/quentin/Desktop/Omni_Reports",
                    "tooltip": "Chemin du dossier où le rapport HTML sera sauvegardé",
                }),
            }
        }

    def generate_report(self, stats_json: str, save_directory: str):
        if not stats_json or not stats_json.strip():
            raise RuntimeError("[Omni_ApifyReport] Le stats_json fourni est vide.")

        try:
            data = json.loads(stats_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"[Omni_ApifyReport] Impossible de parser le JSON : {e}")

        stats_list = []
        filter_text = "Standard"
        if isinstance(data, dict) and "stats" in data:
            stats_list = data["stats"]
            filter_text = data.get("metadata", {}).get("filter_applied", "Standard")
        elif isinstance(data, list):
            stats_list = data

        if not isinstance(stats_list, list):
            raise RuntimeError("[Omni_ApifyReport] Le format des statistiques est invalide.")

        # Déduplication par username (garde le plus récent)
        latest_posts = {}
        for item in stats_list:
            user = item.get("username", "Inconnu")
            if user in latest_posts:
                if item.get("timestamp", "") > latest_posts[user].get("timestamp", ""):
                    latest_posts[user] = item
            else:
                latest_posts[user] = item

        posts = list(latest_posts.values())

        # Nom de fichier avec format lisible
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%Hh%Mm%S")
        file_name = f"report_instagram_{timestamp_str}.html"

        os.makedirs(save_directory, exist_ok=True)
        file_path = os.path.join(save_directory, file_name)

        html_content = self._build_html(posts, now, filter_text)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[Omni_ApifyReport] ✅ Rapport généré : {file_path}")
        return (file_path,)

    # ------------------------------------------------------------------

    def _build_html(self, posts: list, gen_date: datetime, filter_text: str) -> str:
        date_str = gen_date.strftime("%d/%m/%Y à %H:%M:%S")
        total = len(posts)

        # KPIs
        total_likes = sum(self._safe_int(p.get("likes", 0)) for p in posts)
        total_comments = sum(self._safe_int(p.get("comments", 0)) for p in posts)
        video_posts = [p for p in posts if self._safe_int(p.get("videoViewCount", 0)) > 0]
        total_views = sum(self._safe_int(p.get("videoViewCount", 0)) for p in video_posts)

        avg_likes = round(total_likes / total) if total else 0
        avg_comments = round(total_comments / total) if total else 0
        avg_views = round(total_views / len(video_posts)) if video_posts else 0

        # Build table rows
        rows_html = ""
        for i, post in enumerate(posts, 1):
            user = post.get("username", "N/A")
            followers = self._safe_int(post.get("followersCount", 0))
            likes = self._safe_int(post.get("likes", 0))
            comments = self._safe_int(post.get("comments", 0))
            views = self._safe_int(post.get("videoViewCount", 0))
            plays = self._safe_int(post.get("videoPlayCount", 0))
            post_type = post.get("type", "Post")
            timestamp = post.get("timestamp", "")[:10] if post.get("timestamp") else "—"
            url = post.get("post_url", "#")

            type_badge = "🎬" if post_type in ("Video", "Reel") else "📷" if post_type in ("Image", "Sidecar") else "❓"
            likes_class = "val-high" if likes >= 100000 else "val-mid" if likes >= 10000 else ""
            views_class = "val-high" if views >= 100000 else "val-mid" if views >= 10000 else ""

            rows_html += f"""
            <tr data-user="{user.lower()}" data-likes="{likes}" data-comments="{comments}" data-views="{views}" data-followers="{followers}">
                <td class="col-rank">{i}</td>
                <td class="col-user"><a href="https://instagram.com/{user}" target="_blank">@{user}</a></td>
                <td class="col-followers" data-sort="{followers}">{self._fmt(followers)}</td>
                <td class="col-type">{type_badge} {post_type}</td>
                <td class="col-likes {likes_class}" data-sort="{likes}">{self._fmt(likes)}</td>
                <td class="col-comments" data-sort="{comments}">{self._fmt(comments)}</td>
                <td class="col-views {views_class}" data-sort="{views}">{self._fmt(views)}</td>
                <td class="col-plays" data-sort="{plays}">{self._fmt(plays)}</td>
                <td class="col-date">{timestamp}</td>
                <td class="col-link"><a href="{url}" target="_blank" class="link-btn">↗</a></td>
            </tr>"""

        # CSV data (JSON embedded for JS export)
        csv_headers = "Rang,Compte,Followers,Type,Likes,Commentaires,Vues,Plays,Date,URL"
        csv_rows_js = json.dumps([
            [i+1, p.get("username",""), self._safe_int(p.get("followersCount",0)), p.get("type",""),
             self._safe_int(p.get("likes",0)), self._safe_int(p.get("comments",0)),
             self._safe_int(p.get("videoViewCount",0)), self._safe_int(p.get("videoPlayCount",0)),
             (p.get("timestamp","")[:10] if p.get("timestamp") else ""), p.get("post_url","")]
            for i, p in enumerate(posts)
        ])

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Omni Intelligence Report</title>
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
    --green-dim: rgba(52,211,153,0.12);
}}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.5;
}}

/* ── Layout ── */
.wrap {{ max-width:1440px; margin:0 auto; padding:32px 24px; }}

/* ── Header ── */
header {{ text-align:center; margin-bottom:32px; }}
h1 {{
    font-size:2rem; font-weight:800; letter-spacing:-0.5px;
    background: linear-gradient(135deg, #fff 0%, #888 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}}
.meta {{ color:var(--text-dim); margin-top:6px; font-size:0.9rem; }}
.filter-badge {{
    display:inline-block; margin-top:10px;
    background: var(--accent-glow); color:#8b98f7;
    padding:4px 14px; border-radius:20px; font-size:0.8rem;
    border:1px solid rgba(94,106,210,0.25);
}}

/* ── KPIs ── */
.kpis {{
    display:grid; grid-template-columns:repeat(4,1fr); gap:16px;
    margin-bottom:24px;
}}
.kpi {{
    background:var(--surface); border:1px solid var(--border);
    border-radius:12px; padding:20px; text-align:center;
}}
.kpi .num {{ font-size:1.75rem; font-weight:800; color:#fff; }}
.kpi .lbl {{ font-size:0.75rem; color:var(--text-dim); text-transform:uppercase; letter-spacing:1px; margin-top:4px; }}

/* ── Toolbar ── */
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

/* ── Table ── */
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
.col-user a {{ color:var(--text); text-decoration:none; font-weight:600; }}
.col-user a:hover {{ color:var(--accent); }}
.col-followers {{ color:var(--text-dim); }}
.col-type {{ font-size:0.8rem; }}
.col-date {{ color:var(--text-dim); font-size:0.85rem; }}

.val-high {{ color:var(--green); font-weight:700; }}
.val-mid {{ color:#facc15; }}

.link-btn {{
    display:inline-flex; align-items:center; justify-content:center;
    width:28px; height:28px; border-radius:6px;
    background:rgba(255,255,255,0.06); color:var(--text-dim);
    text-decoration:none; font-size:0.8rem; transition:all 0.15s;
}}
.link-btn:hover {{ background:var(--accent); color:#fff; }}

/* ── Responsive ── */
@media (max-width:768px) {{
    .kpis {{ grid-template-columns:repeat(2,1fr); }}
    .wrap {{ padding:16px 12px; }}
}}
</style>
</head>
<body>
<div class="wrap">
    <header>
        <h1>Omni Intelligence Report</h1>
        <div class="meta">Généré le {date_str} • {total} comptes analysés</div>
        <div class="filter-badge">🎯 {filter_text}</div>
    </header>

    <div class="kpis">
        <div class="kpi"><div class="num">{total}</div><div class="lbl">Comptes</div></div>
        <div class="kpi"><div class="num">{self._fmt(avg_likes)}</div><div class="lbl">Moy. Likes / Post</div></div>
        <div class="kpi"><div class="num">{self._fmt(avg_comments)}</div><div class="lbl">Moy. Commentaires</div></div>
        <div class="kpi"><div class="num">{self._fmt(avg_views)}</div><div class="lbl">Moy. Vues (Vidéos)</div></div>
    </div>

    <div class="toolbar">
        <input type="text" class="search-box" id="search" placeholder="🔍 Rechercher un compte..." autocomplete="off">
        <button class="btn-csv" onclick="exportCSV()">📥 Export CSV</button>
        <span class="counter" id="counter">{total} / {total} comptes</span>
    </div>

    <div class="table-wrap">
        <table id="dataTable">
            <thead>
                <tr>
                    <th data-col="0" data-type="num"># <span class="arrow"></span></th>
                    <th data-col="1" data-type="str">Compte <span class="arrow"></span></th>
                    <th data-col="2" data-type="num">Followers <span class="arrow"></span></th>
                    <th data-col="3" data-type="str">Type <span class="arrow"></span></th>
                    <th data-col="4" data-type="num">Likes <span class="arrow"></span></th>
                    <th data-col="5" data-type="num">Commentaires <span class="arrow"></span></th>
                    <th data-col="6" data-type="num">Vues <span class="arrow"></span></th>
                    <th data-col="7" data-type="num">Plays <span class="arrow"></span></th>
                    <th data-col="8" data-type="str">Date <span class="arrow"></span></th>
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
// ── Search ──
const searchInput = document.getElementById('search');
const tableBody = document.getElementById('tableBody');
const counter = document.getElementById('counter');
const totalRows = {total};

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
    counter.textContent = visible + ' / ' + totalRows + ' comptes';
}});

// ── Sort ──
let currentSort = {{ col: -1, asc: true }};
document.querySelectorAll('thead th[data-col]').forEach(th => {{
    th.addEventListener('click', function() {{
        const col = parseInt(this.dataset.col);
        const type = this.dataset.type;
        const asc = currentSort.col === col ? !currentSort.asc : true;
        currentSort = {{ col, asc }};

        // Clear arrows
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

        // Re-rank
        rows.forEach((row, i) => {{
            row.children[0].textContent = i + 1;
            tableBody.appendChild(row);
        }});
    }});
}});

// ── CSV Export ──
const csvData = {csv_rows_js};
function exportCSV() {{
    let csv = "{csv_headers}\\n";
    csvData.forEach(row => {{
        csv += row.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',') + '\\n';
    }});
    const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'omni_export_{gen_date.strftime("%Y%m%d")}.csv';
    link.click();
}}
</script>
</body>
</html>"""

    @staticmethod
    def _safe_int(val) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def _fmt(self, num) -> str:
        try:
            val = int(num)
            if val >= 1_000_000:
                return f"{val / 1_000_000:.1f}M"
            elif val >= 1_000:
                return f"{val / 1_000:.1f}k"
            return str(val)
        except (ValueError, TypeError):
            return "0"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()


NODE_CLASS_MAPPINGS = {
    "Omni_ApifyReport": Omni_ApifyReport,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Omni_ApifyReport": "📋 Apify HTML Report",
}
