# 🍌 NanoBanana Suite

NanoBanana Suite est une extension puissante et professionnelle pour **ComfyUI**, conçue pour automatiser et améliorer les workflows créatifs, de la génération d'images avancée à l'automatisation de vidéos pour les réseaux sociaux.

Ce dossier est prêt pour la production (Public-Ready). Les clés API sont traitées de manière sécurisée et les chemins sont multiplateformes.

---

## 📋 Sommaire

1. [⚙️ Installation & Pré-requis](#1-⚙️-installation--pré-requis)
2. [🤖 Génération & Direction (Gemini)](#2-🤖-génération--direction-gemini)
3. [👤 Traitement Visage & Post-process](#3-👤-traitement-visage--post-process)
4. [🎬 Vidéo & API Kling](#4-🎬-vidéo--api-kling)
5. [🚀 Outils & Automatisation (Social Media)](#5-🚀-outils--automatisation-social-media)

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

* `🍌 Preview` : Permet de prévisualiser l'image en direct dans le flow, avant la sauvegarde, sans l'écrire définitivement.

* `🍌 Clean Save` : **(Important)** Sauvegarde l'image finale sur votre disque dur (dans le dossier natif de sortie de ComfyUI), en *supprimant intégralement toutes les balises EXIF et métadonnées invisibles* injectées par ComfyUI. Idéal pour partager des images pures sans révéler le workflow.

---

## 4. 🎬 Vidéo & API Kling

Ces nœuds font le pont direct entre ComfyUI et les API de génération vidéo externes comme **Kling AI** (via PiAPI).

* `🍌 PiAPI Kling Auth` : Nœud d'authentification pour se connecter à PiAPI de manière sécurisée.
* `🍌 PiAPI Kling Motion Control` : Permet d'envoyer vos images générées dans ComfyUI à l'IA vidéo Kling pour leur donner vie, avec un contrôle avancé du mouvement (Motion Brush, Camera Path, etc).

* `🍌 Batch Video Queue` : Gère une file d'attente pour traiter, charger ou lister plusieurs vidéos en lot dans le workflow.
* `🍌 Video First Frame` : Extrait instantanément la première frame (image 1) d'une vidéo pour s'en servir de référence Image-to-Video.
* `🍌 Export for Kling` : Formatte la taille et prépare les métadonnées optimales de l'image pour l'API Kling.

---

## 5. 🚀 Outils & Automatisation (Social Media)

Un pipeline dédié à la manipulation en masse ("Bulk Upload") pour TikTok, Reels et Shorts (GeeLark).

### 🍌 Video Spoofer
Modifie furtivement les vidéos avant de les poster pour contourner les algorithmes de détection de doublons (TikFusion / Meta).
* **Nettoyage profond** : Supprime intégralement les métadonnées vidéo.
* **Bypass Visuel & Audio** : Modifie imperceptiblement la colorimétrie (contraste, sats), randomize très légèrement la vitesse (1.01x à 1.03x), ajoute du grain/bruit invisible, et modifie la fréquence audio pour garantir une empreinte digitale 100% unique à chaque exécution.
* (Nécessite *FFmpeg* sur le système).

### 🍌 GeeLark Scheduler
Remplit automatiquement les tableaux Excel d'import massif de l'application **GeeLark** (multicomptes).
* Prend en entrée un tableau de base vide (modèle exporté).
* Répartit intelligemment les vidéos sur les jours souhaités via le slider `start_days_from_now` et `days_spread`. 
* Assure le respect d'un temps de repos (gap minimal) entre 2 vidéos du même compte le même jour.
* **Dashboard HTML inclus** : Génère automatiquement une magnifique Timeline couleur au format page Web (`.html`) à côté du `.xlsx` de sortie pour visualiser le planning complet en 1 clic.

### 🍌 Static Captioner
Génère instantanément des centaines de "captions" textuelles *ultra-génériques*, prêtes à être ingérées par le GeeLark Scheduler.
* Déterministe : Ne fait aucun appel à Internet, zéro lag, zéro API Keys.
* Esthétisme de niche : Force toutes les phrases en minuscules (*lowercased*).
* Système de Hashtag aléatoire pondéré (ex: 30% du temps, il rajoute aléatoirement 1 à 2 hashtags provenant de votre pool perso).

---

## 💡 Notes sur le développement

- **Sécurité** : Aucune donnée personnelle, chemin d'ordinateur local ou clé API n'est hardcodée dans cette suite. 
- **Ergonomie** : Conçue avec peu d'inputs "Texte" et beaucoup de curseurs (Sliders) et de Menus déroulants (Dropdowns) pour éviter toute erreur de syntaxe côté utilisateur.
- **Support** : L'extension s'adapte automatiquement à son emplacement (tous les imports des classes sont relatifs (`.nodes.api...`)).
