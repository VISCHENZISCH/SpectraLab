# SpectraLab

Studio desktop (Windows et Linux) d'analyse, de restauration et de protection de médias : image, audio et vidéo.
Tous les traitements s'exécutent en local, sans rien envoyer sur Internet.

## Fonctionnalités actuelles

- **Métadonnées** : lecture complète (EXIF, IPTC, XMP, ID3, conteneurs vidéo), rapport de confidentialité (GPS, numéros de série, auteur…), modification d'un champ, nettoyage d'une copie, de l'original ou d'une liste entière.
- **Image** : conversion (PNG, JPEG, WEBP, TIFF, GIF, BMP, ICO…) et redimensionnement, sans recopier les métadonnées par défaut.
- **Audio et vidéo** : durée, taille, débit, codecs et détail de chaque flux.
- **Accueil** : activité des 7 derniers jours et état des moteurs installés.

## Prérequis

- Python 3.10 ou plus récent
- [ExifTool](https://exiftool.org) et [FFmpeg](https://ffmpeg.org), installés sur le système ou placés dans un dossier `bin/` à la racine du projet

## Installation et lancement

```bash
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -e ".[dev]"
spectralab                        # ou : python -m spectralab
```

Tests : `pytest`

## Structure

```
spectralab/
├── core/   # Logique métier, sans dépendance à Qt (métadonnées, images, médias, outils externes)
└── ui/     # Interface PySide6 : thème, composants, pages
tests/      # Tests du cœur
```

## Sécurité

- Les outils externes sont lancés sans shell. Le dossier courant et les entrées relatives du `PATH` sont ignorés, et seuls les `.exe` sont acceptés sous Windows.
- Les arguments sont transmis à ExifTool par l'entrée standard. Les noms de champs sont validés et les retours à la ligne refusés : aucune valeur ne peut devenir une option.
- FFmpeg reçoit les chemins préfixés par `file:`, ce qui empêche l'interprétation de protocoles.
- Les fichiers produits ne remplacent jamais un fichier existant. Le nettoyage de l'original demande une confirmation.
- Les images géantes (« bombes de décompression ») sont refusées. Le texte venu des fichiers est affiché en texte brut, jamais interprété comme du HTML.

Développé par **VISCHENZISCH**.
