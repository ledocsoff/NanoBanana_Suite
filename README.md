# 🍌 NanoBanana Suite

NanoBanana Suite est une extension puissante et professionnelle pour **ComfyUI**, conçue pour automatiser et améliorer les workflows créatifs, de la génération d'images avancée à l'automatisation de vidéos pour les réseaux sociaux.

Ce dossier est prêt pour la production (Public-Ready). Les clés API sont traitées de manière sécurisée et les chemins sont multiplateformes.

---

## 📋 Sommaire

1. [⚙️ Installation & Pré-requis](#1-️-installation--pré-requis)
2. [🤖 Génération & Direction (Gemini)](#2--génération--direction-gemini)
3. [👤 Traitement Visage & Post-process](#3--traitement-visage--post-process)
4. [🎬 Vidéo & API Kling](#4--vidéo--api-kling)
5. [🚀 Outils & Automatisation (Social Media)](#5--outils--automatisation-social-media)
6. [📐 Architecture Technique](#6--architecture-technique)

---

## 1. ⚙️ Installation & Pré-requis

### Installation classique
Clonez ou copiez ce dossier directement dans `ComfyUI/custom_nodes/`.
```bash
cd ComfyUI/custom_nodes
git clone <url-du-repo> NanoBanana_Suite
```

### Dépendances Python
L'extension installe normalement ses dépendances, mais vous pouvez forcer l'installation :
```bash
pip install -r requirements.txt
```
*(Packages principaux : `google-generativeai`, `openpyxl`, `Pillow`, `numpy`...)*

### Pré-requis externes
- **Outil Video Spoofer** : Nécessite que `FFmpeg` soit installé sur votre machine et accessible dans votre `PATH`.

---

## 2. 🤖 Génération & Direction (Gemini)

Ces nœuds exploitent la puissance de **Google Gemini 1.5/2.0** pour diriger la génération d'images avec une précision "Directeur Artistique".

### Nœud de Configuration partagé
* `🍌 Gemini Config` : Nœud central pour entrer votre clé API Google de façon sécurisée. À relier aux autres nœuds Gemini.

### Nœuds Directeurs (Direction)
* `🍌 IA Director` : Agrège des consignes complexes (Sujet, Style, Action, Caméra) pour pondre un prompt parfait.
* `🍌 Matrix Builder` : Conçu pour tester un prompt avec plusieurs variables sous forme de grille mathématique expérimentale.
* `🍌 Vision API` : Analyse et décrit le contenu visuel d'une ou plusieurs images passées en entrée.
* `🍌 Variant Director` & `🍌 Variant API` : Génèrent des variations contextuelles fluides d'un prompt initial (ex: pour de la vidéo ou des keyframes).
* `🍌 Chooser` : Utilisé pour faire un tri ou sélectionner des éléments précis suite aux générations de Matrix ou Variants.

### Nœuds de Génération Native
* `🍌 Prompt to Image` : Connexion directe Text-to-Image (dépendant des modèles supportés).
* `🍌 Image to Image` : Modification d'images existantes.

---

## 3. 👤 Traitement Visage & Post-process

Des outils ciblés pour préserver l'identité et exporter proprement le résultat.

* `🍌 Swap` : Remplace ou combine des visages/identités sur une image cible tout en respectant l'éclairage et la direction du regard (nécessite les modèles Reactor/FaceID sous-jacents).

* `🍌 Quality Gate` : **Validation intelligente des face swaps via Gemini Vision.** Le nœud analyse le résultat du swap selon 3 critères (identité, préservation de la scène, artefacts) et retourne un verdict binaire PASS/FAIL. En cas d'échec, il **re-génère automatiquement un nouveau swap** (retry interne) jusqu'à `max_retries` tentatives (défaut: 2). Si tous les retries échouent, il retourne un tensor vide que Kling MC détecte automatiquement pour skipper l'appel API et déplacer la vidéo dans le dossier `/failed`.

* `🍌 Preview` : Permet de prévisualiser l'image en direct dans le flow, avant la sauvegarde, sans l'écrire définitivement.

* `🍌 Clean Save` : **(Important)** Sauvegarde l'image finale sur votre disque dur (dans le dossier natif de sortie de ComfyUI), en *supprimant intégralement toutes les balises EXIF et métadonnées invisibles* injectées par ComfyUI. Idéal pour partager des images pures sans révéler le workflow.

---

## 4. 🎬 Vidéo & API Kling

Ces nœuds font le pont direct entre ComfyUI et les API de génération vidéo externes comme **Kling AI** (via PiAPI).

* `🍌 PiAPI Kling Auth` : Nœud d'authentification pour se connecter à PiAPI de manière sécurisée.
* `🍌 PiAPI Kling Motion Control` : Permet d'envoyer vos images générées dans ComfyUI à l'IA vidéo Kling pour leur donner vie, avec un contrôle avancé du mouvement (Motion Brush, Camera Path, etc).

* `🍌 Batch Video Queue` : Gère une file d'attente pour traiter, charger ou lister plusieurs vidéos en lot dans le workflow. Supporte le **mode récursif** : si activé, il scanne les sous-dossiers et préserve la structure dans `output/`, `done/` et `failed/`. La détection de vidéos déjà traitées utilise le chemin relatif complet (pas seulement le nom de fichier), ce qui évite les collisions entre sous-dossiers.
* `🍌 Video First Frame` : Extrait instantanément la première frame (image 1) d'une vidéo pour s'en servir de référence Image-to-Video.
* `🍌 Export for Kling` : Formatte la taille et prépare les métadonnées optimales de l'image pour l'API Kling.

---

## 5. 🚀 Outils & Automatisation (Social Media)

Un pipeline complet dédié au **scheduling Instagram à grande échelle** (100+ comptes) via **GeeLark**. Le système fonctionne en mode **batch offline** : on remplit des fichiers Excel (.xlsx) exportés depuis GeeLark, puis on les réimporte. Aucune API de réseau social n'est appelée directement — c'est GeeLark qui exécute.

### Concept clé : Architecture "Paris-Centric"

Toutes les heures sont en **heure locale de Paris**, écrites directement dans les fichiers Excel. Il n'y a **aucune conversion de timezone** dans le code. Ce que vous voyez dans le fichier = ce que GeeLark exécute. Cela élimine totalement les bugs liés au changement d'heure été/hiver (DST).

### Les 3 Time Blocks disponibles

| Bloc | Heures (Paris) | Usage typique |
|------|----------------|--------------|
| ☀️ Matin (08h-16h) | 08:00 → 16:00 | Warmup matinal des comptes |
| 🌆 Après-midi (16h-22h) | 16:00 → 22:00 | Maintenance, posts EU |
| 🌙 Soir (22h-04h) | 22:00 → 04:00 | **Prime Time US** — bloc overnight |

Le bloc Soir est un **bloc overnight** : il commence à 22h et finit à 04h du matin le lendemain. Le code gère automatiquement le passage de minuit.

---

### 🍌 Video Spoofer

**But** : Rendre chaque copie d'une vidéo techniquement unique pour éviter la détection de doublons par les algorithmes Instagram/TikTok.

**Comment ça marche** :
1. Vous placez vos vidéos sources dans un dossier (supporte les sous-dossiers : `dance/`, `talking/`, etc.)
2. Le nœud génère N **lots complets** de copies spoofées dans des sous-dossiers numérotés (`1/`, `2/`, `3/`...)
3. Les lots sont isolés dans un dossier `_SPOOFED_BATCHES/` à la racine du dossier source
4. L'arborescence des sous-dossiers est parfaitement conservée dans chaque lot
5. Chaque copie a un hash unique → les plateformes les voient comme des vidéos différentes

**Transformations appliquées (imperceptibles à l'œil nu)** :
- Luminosité ±3%, Contraste ±3%, Saturation ±3%
- Crop aléatoire 2-4% (puis re-scale 1080x1920 via Lanczos)
- Vitesse modifiée de +1% à +7%
- Volume audio ±5%
- CRF 25-28 (sweet spot Instagram — 2-3x plus léger, qualité identique sur mobile)
- Preset `medium` ou `slow` uniquement (compression optimale)
- Profil x264 `main` ou `high` (pas de `baseline`)
- Métadonnées entièrement remplacées (faux encoder, fausse date de création)
- Nom de fichier aléatoire avec préfixe variable : `CapCut_`, `IMG_`, `VID_`, `Snapchat_`, `InShot_`, `WhatsApp_Video_`

**Paramètres** :
| Paramètre | Description |
|-----------|-------------|
| `input_folder` | Dossier contenant les vidéos sources (.mp4, .mov, .webm) — parcours récursif |
| `number_of_folders` | Nombre de lots (sous-dossiers 1, 2, 3...) à générer (1-50) |

**Structure de sortie** :
```
mes_videos/
├── dance/          ← sources (intactes)
├── talking/        ← sources (intactes)
└── _SPOOFED_BATCHES/
    ├── 1/
    │   ├── dance/   ← copies spoofées
    │   └── talking/ ← copies spoofées
    └── 2/
        ├── dance/
        └── talking/
```

**Nécessite** : FFmpeg installé sur la machine.

---

### 🍌 GeeLark Scheduler

**But** : Remplir automatiquement les fichiers Excel de planification GeeLark avec des horaires aléatoires répartis intelligemment sur plusieurs jours.

**Comment ça marche** :
1. Exportez un fichier `.xlsx` depuis GeeLark (Edit Table → Export)
2. Branchez le chemin du fichier dans le nœud
3. Le nœud détecte automatiquement le type de template (Post Reel, Carousel, Edit Profile)
4. Il remplit la colonne "Release Time" avec des horaires distribués via **Segmented Jitter** (couverture uniforme de toute la plage horaire)
5. Il remplit la colonne "Caption" avec les captions fournies (ou des captions par défaut)
6. Il génère 2 fichiers : `_scheduled.xlsx` (à réimporter dans GeeLark) + `_calendar.html` (planning visuel)
7. Si l'input provient d'un Profile Filler (`_filled.xlsx`), le fichier intermédiaire est **auto-supprimé** après succès

**Auto-détection du type de template** :
Le nœud lit les en-têtes Excel pour savoir automatiquement quel type de template vous utilisez :
- Si colonne 5 contient "nickname" → `edit_profile`
- Si colonne 5 contient "video" → `account_warmup`
- Sinon → `post_video/carousel`

**Segmented Jitter (Phase 0)** :
Au lieu de tirer des créneaux au hasard (risque de clustering temporel), le Scheduler découpe la fenêtre horaire en N segments égaux et place un post aléatoirement dans chaque segment. Résultat : une distribution organique et uniforme sur toute la plage, crédible comme un pattern de publication humain.

**Anti-collision cross-account** :
Quand vous avez 100 comptes sur le même bloc horaire, le Scheduler respecte strictement `max_simultaneous` :
- `max_simultaneous=1` : aucun chevauchement, chaque post est isolé dans sa propre fenêtre de `min_gap_minutes`
- `max_simultaneous=3` : jusqu'à 3 posts autorisés dans le même rayon temporel

**Capacité dynamique** :
Le Scheduler calcule automatiquement la capacité réelle par jour (`total_minutes / min_gap × max_simultaneous`). Si `days_spread` est trop court pour le volume de tâches, il s'ajuste automatiquement avec un warning explicatif.

**Distribution Bresenham (Edit Profile)** :
Pour les templates "1 tâche par compte", les comptes sont distribués uniformément sur les jours via un algorithme de type Bresenham (ex: 29 comptes / 7 jours = 5-4-4-4-4-4-4).

**Paramètres** :
| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `template_file` | Chemin du .xlsx exporté de GeeLark | — |
| `block_matin` | ☀️ Activer le bloc Matin (04h-16h) | ✅ |
| `block_apresmidi` | 🌆 Activer le bloc Après-midi (16h-22h) | ✅ |
| `block_soir` | 🌙 Activer le bloc Soir (22h-04h) | ❌ |
| `start_days_from_now` | Début dans X jours (0=aujourd'hui) | 1 |
| `captions` | Captions (optionnel, depuis StaticCaptioner) | Auto-générées |
| `days_spread` | Nombre de jours de répartition | 7 |
| `min_gap_minutes` | Espacement minimum entre 2 posts | 30 |
| `max_simultaneous` | Tolérance de chevauchement (1 = strict) | 3 |

**Calendrier HTML** :
Le fichier `_calendar.html` généré est un dashboard dark mode responsive qui affiche :
- Chaque jour avec ses événements (affiche "nuits actives" pour les blocs overnight)
- Code couleur par compte (couleurs HSL dynamiques, supporte 100+ comptes)
- Statistiques par compte (nombre de posts, moyenne par jour)
- Badge compteur par jour

---

### 🍌 Static Captioner

**But** : Générer instantanément des centaines de captions textuelles génériques sans aucun appel API.

**Comment ça marche** :
1. Le nœud contient des pools internes de captions courtes au style Gen Z / Instagram
2. Il supporte 2 types de contenu : `reel` (captions courtes) et `carousel` (captions "swipe-friendly")
3. Chaque caption est en minuscules (esthétique Instagram)
4. 30% du temps, il ajoute 1-2 hashtags aléatoires du pool interne

**Paramètres** :
| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `count` | Nombre de captions à générer | 50 |
| `content_type` | `reel` ou `carousel` | reel |

**Sortie** : Les captions sont séparées par `---` et peuvent être branchées directement sur le GeeLark Scheduler.

---

### 🍌 Emoji Bio Generator

**But** : Générer automatiquement des bios Instagram uniques composées d'émojis et de mots courts pour la personnalisation de masse des profils.

**Comment ça marche** :
1. Le nœud charge un fichier JSON de fragments (`emoji_fragments.json`) contenant des catégories d'émojis et de mots
2. Il génère 200 bios uniques (via un `set` interne qui garantit l'unicité)
3. Chaque bio fait max 150 caractères (limite Instagram)
4. Chaque bio est un mélange aléatoire de 2 à 5 fragments (émojis + mots courts)
5. Le nœud a un toggle `enabled` : si désactivé, il passe les bios sans les écrire

**Paramètres** :
| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `enabled` | Active/désactive la génération de bios | True |

**Sortie** : 200 bios uniques séparées par `---`, prêtes à être branchées sur le Profile Filler.

**Guard-rail** : Si le nœud n'arrive pas à générer assez de bios uniques après `200 × 3` tentatives, il s'arrête (évite boucle infinie).

---

### 🍌 Profile Filler

**But** : Remplir en masse les fichiers Excel GeeLark "Edit Profile" pour modifier les profils Instagram de nombreux comptes en une seule opération.

**Comment ça marche** :
1. Chargez le template GeeLark "Edit Profile" exporté en .xlsx
2. Fournissez les données à écrire (bios, nicknames, usernames, etc.)
3. Le nœud remplit les colonnes correspondantes du fichier Excel
4. Exportez le fichier `_filled.xlsx` résultant et réimportez-le dans GeeLark

**Champs supportés (tous optionnels)** :
| Champ | Colonne Excel | Description |
|-------|--------------|-------------|
| `bios` | 7 (Biography) | Bios séparées par `---` (depuis Emoji Bio Generator) |
| `nicknames` | 5 (Nickname) | Noms d'affichage, un par ligne |
| `usernames` | 6 (Username) | Noms d'utilisateur @, un par ligne |
| `link_url` | 8 (Link URL) | URL du lien bio (même pour tous) |
| `link_title` | 9 (Link Title) | Titre du lien bio (même pour tous) |

**Auto-distribution** : Si vous fournissez 10 bios pour 50 comptes, les bios sont recyclées et mélangées aléatoirement pour que chaque compte ait une bio.

---

### 🍌 Account Warmup Filler

**But** : Remplir le template GeeLark "Instagram AI account warmup" pour automatiser le réchauffement séquentiel des comptes neufs.

**Comment ça marche** :
1. Exportez le template warmup depuis GeeLark en .xlsx
2. Le nœud calcule l'espacement optimal entre chaque compte en fonction du nombre de comptes et de la durée du bloc horaire
3. Il remplit pour chaque compte : l'heure de lancement, le nombre de vidéos à scroller, un mot-clé de recherche aléatoire
4. Les comptes sont espacés séquentiellement (compte 1 à 22h00, compte 2 à 22h36, compte 3 à 23h12, etc.)

**Calcul de l'espacement** :
```
Espacement = Durée du bloc (en minutes) / Nombre de comptes
```
Exemple : bloc Soir (360 min) avec 10 comptes = 36 min entre chaque compte (±15% de variation + guard-rail minimum de 15 min).

Si l'espacement calculé est inférieur à 15 minutes (trop de comptes pour le bloc), le nœud affiche un warning et les tâches débordent automatiquement sur les jours suivants.

**Paramètres** :
| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `template_file` | Chemin du .xlsx warmup exporté de GeeLark | — |
| `time_block` | Plage horaire Paris | ☀️ Matin (08h-16h) |
| `keywords_pool` | Mots-clés de recherche (un par ligne) | Pool par défaut |
| `min_scroll_videos` | Min vidéos à scroller par compte | 7 |
| `max_scroll_videos` | Max vidéos à scroller par compte | 10 |
| `start_days_from_now` | Début dans X jours | 0 |

---

### 🔄 Workflows type

#### Workflow 1 : Warmup de nouveaux comptes
```
📄 Template warmup.xlsx
        │
  ┌─────▼──────────┐
  │ Warmup Filler   │ → timing séquentiel + keywords + scroll count
  └─────┬──────────┘
        │
  📄 _scheduled.xlsx → Import GeeLark
```

#### Workflow 2 : Personnalisation des profils
```
  ┌──────────────┐
  │ Emoji Bio Gen │ → 200 bios uniques (toggle on/off)
  └──────┬───────┘
         │ bios (séparateur ---)
  ┌──────▼──────────┐
  │ Profile Filler   │ ← nicknames, usernames, link_url, link_title
  └──────┬──────────┘
         │
  ┌──────▼──────────────┐
  │ GeeLark Scheduler    │ → scheduling + 🧹 auto-suppression du _filled.xlsx
  └──────┬──────────────┘
         │
  📄 _scheduled.xlsx + 📊 _calendar.html → Import GeeLark
```

#### Workflow 3 : Publication de Reels/Carousel
```
  ┌─────────────────┐
  │ Static Captioner │ → captions Gen Z + hashtags
  └──────┬──────────┘
         │ captions (séparateur ---)
  ┌──────▼──────────────┐
  │ GeeLark Scheduler    │ ← template + blocs horaires + days_spread
  └──────┬──────────────┘
         │
  📄 _scheduled.xlsx + 📊 _calendar.html
```

#### Workflow 4 : Pipeline complet Face Swap → Kling MC
```
  ┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
  │ Batch Video Queue │ ──→ │ Video 1st    │ ──→ │ 🍌 Swap      │
  │  (recursive: on)  │     │ Frame        │     └──────┬───────┘
  └──────┬───────────┘     └──────────────┘            │
         │                                              │
         │ relative_subfolder                ┌──────────▼───────────┐
         │                                   │ 🍌 Quality Gate       │
         │                                   │ (PASS/FAIL + retry)   │
         │                                   └──────────┬───────────┘
         │                                              │ image (ou vide)
         └──────────────────────────────────────────────▼
                                              ┌──────────────────────┐
                                              │ 🍌 PiAPI Kling MC     │
                                              │ ← relative_subfolder  │
                                              └──────────┬───────────┘
                                                         │
                                              output/Peak Reels/video_mc.mp4
                                              done/Peak Reels/video.mp4
```

#### Workflow 5 : Vidéo unique → Copies spoofées
```
  ┌──────────────┐     ┌───────────────┐
  │ Export Kling  │ ──→ │ PiAPI Kling MC │ ──→ vidéo .mp4
  └──────────────┘     └───────┬───────┘
                               │
  ┌────────────────────────────▼──┐
  │ Video Spoofer                  │ → lots numérotés dans _SPOOFED_BATCHES/
  └────────────┬──────────────────┘
               │
  📁 _SPOOFED_BATCHES/1/, 2/, 3/... → Upload GeeLark
```

---

## 6. 📐 Architecture Technique

### Structure des fichiers

```
NanoBanana_Suite/
├── __init__.py              # Point d'entrée ComfyUI (24 nœuds enregistrés)
├── core/                    # Utilitaires bas niveau
│   ├── image_utils.py       # tensor↔PIL, base64
│   ├── video_utils.py       # FFmpeg, extraction frames, scan récursif
│   └── file_manager.py      # Gestion fichiers/dossiers
├── shared/                  # Modules partagés (scheduling)
│   ├── gemini_client.py     # Client Google Gemini (retry, safety handling)
│   ├── gemini_config.py     # Nœud config API
│   ├── xlsx_utils.py        # Source de vérité : TIME_BLOCKS, schemas, helpers Excel
│   └── calendar_html.py     # Générateur de calendrier HTML (couleurs HSL dynamiques)
├── nodes/
│   ├── api/                 # PiAPI Kling Auth + Motion Control (subfolder-aware)
│   ├── direction/           # IA Director, Matrix, Variant, Chooser, Vision
│   ├── face/                # Swap, Quality Gate (validation + retry)
│   ├── generation/          # Prompt-to-Image, Image-to-Image
│   ├── postprocess/         # Preview, Clean Save
│   ├── tools/               # Video Spoofer, GeeLark Scheduler, Captioner, Bio Gen, Profile Filler, Warmup
│   │   └── data/            # emoji_fragments.json
│   └── video/               # Batch Queue (recursive), First Frame, Export for Kling
├── web/                     # Scripts JS pour l'UI ComfyUI
└── tests/                   # Tests automatisés
```

### Source de vérité unique

Le fichier `shared/xlsx_utils.py` centralise :
- **TIME_BLOCKS** : les 3 plages horaires (Paris) utilisées par tous les nœuds
- **GEELARK_SCHEMAS** : les positions de colonnes pour chaque type de template
- **Helpers** : `load_template()`, `save_template()`, `fill_column()`, `block_duration_minutes()`

### Conventions de séparateur

Tous les nœuds qui produisent des listes (bios, captions) utilisent le séparateur `---` entre les éléments. Cela permet de chaîner les nœuds : Bio Gen → Profile Filler, Static Captioner → Scheduler.

---

## 💡 Notes sur le développement

- **Sécurité** : Aucune donnée personnelle, chemin d'ordinateur local ou clé API n'est hardcodée dans cette suite. Les noms de comptes dans le calendrier HTML sont échappés (XSS).
- **Ergonomie** : Conçue avec peu d'inputs "Texte" et beaucoup de curseurs (Sliders) et de Menus déroulants (Dropdowns). Les fichiers intermédiaires (`_filled.xlsx`) sont auto-supprimés après traitement.
- **Support** : L'extension s'adapte automatiquement à son emplacement (tous les imports des classes sont relatifs (`.nodes.api...`)).
- **Anti-DST** : Le système est insensible aux changements d'heure saisonniers car il travaille en heure locale de Paris constante, sans conversion de timezone.
- **Anti-Bot** : Distribution temporelle Segmented Jitter, noms de fichiers à préfixes aléatoires, métadonnées falsifiées, crop/compression variables.
- **Scalabilité** : Testé et conçu pour gérer 100+ comptes simultanément sur les workflows de scheduling avec calcul dynamique de capacité.
