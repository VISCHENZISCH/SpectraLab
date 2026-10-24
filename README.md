# SpectraLab

Studio desktop (Windows et Linux) d'analyse, de restauration et de protection de médias : image, audio et vidéo.
Tous les traitements s'exécutent en local, sans rien envoyer sur Internet.

## Fonctionnalités actuelles

- **Métadonnées** : lecture complète (EXIF, IPTC, XMP, ID3, conteneurs vidéo), rapport de confidentialité (GPS, numéros de série, auteur…), modification d'un champ, nettoyage d'une copie, de l'original ou d'une liste entière.
- **Image** : conversion (PNG, JPEG, WEBP, TIFF, GIF, BMP, ICO…) et redimensionnement, sans recopier les métadonnées par défaut.
- **Spectre (audio et vidéo)** : lecture avec spectrogramme qui défile sous une tête de lecture fixe (zoom à la molette, clic pour se déplacer), trois vues (niveau en dBFS, phase, phase gauche/droite), forme d'onde, spectre instantané avec maintien des crêtes, phase par fréquence, goniomètre, corrélation stéréo, crêtes et RMS par canal, rapport audio forensique (sonie EBU R128 en LUFS, plage de sonie, crête réelle en dBTP, saturations, silences, ruptures cliquables, coupure spectrale révélant un passage par un codec avec perte, fausse stéréo, opposition de phase, décalage continu), détection des tonalités DTMF, export du spectrogramme en image (pour révéler une image cachée dans un son). Les vidéos AV1, que le lecteur de Qt ne sait pas décoder sans accélération matérielle, sont lues via une copie H.264 préparée par le FFmpeg du système et gardée 30 jours en cache.
- **Expertise audio** (page Spectre) : fréquence du réseau électrique (ENF, 50/60 Hz) suivie au fil du temps pour dater un enregistrement et repérer les coupes ou collages ; détection des passages de parole ; copie « voix claire » débruitée.
- **Comparer** : deux enregistrements alignés automatiquement (décalage à l'échantillon près), similarité dans le temps, passages modifiés, ajoutés ou retirés, et spectrogramme des différences.
- **Expertise vidéo** : changements de plan, images isolées (éclair, insertion), images dupliquées, images manquantes (trous dans les horodatages), estimation du décalage son/image, vignettes des plans et extraction d'une image en pleine résolution.
- **Expertise d'image** (page Forensique) : carte du bruit (zones collées ou lissées), détection des zones copiées-collées, comparaison avec la miniature EXIF (recadrage, retouche), contrôle de cohérence des métadonnées (logiciel de retouche, dates impossibles, fuseau horaire incompatible avec le GPS, dimensions).
- **Forensique** : empreintes (MD5, SHA-1, SHA-2, SHA-3, BLAKE2, CRC32), type réel et extension trompeuse, entropie globale et par bloc, signatures de fichiers dissimulés, données ajoutées après la fin d'un PNG, JPEG, GIF, PDF ou ZIP, extraction de ces données, chaînes ASCII et UTF-16 avec indicateurs (URL, e-mails, IP, clés, drapeaux CTF…), vue hexadécimale, plans de bits, attaque du khi-deux sur les LSB, lecture des LSB, analyse du niveau d'erreur (ELA) et qualité JPEG estimée d'après les tables de quantification (tables standard ou propres à un logiciel, sous-échantillonnage, mode progressif).
- **Rapports** : export JSON des analyses audio et forensiques, à côté du fichier examiné.
- **Accueil** : tendances des 7 derniers jours avec variation sur la semaine précédente, activité sur 14 jours, analyse rapide par glisser-déposer. La barre latérale liste les fichiers de la session (gardés en mémoire seulement, jamais écrits sur le disque).

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
├── core/   # Logique métier, sans dépendance à Qt (métadonnées, images, audio, spectre, forensique)
└── ui/     # Interface PySide6 : thème, composants, instruments (scope.py), pages
tests/      # Tests par traitement et tests de fichiers malformés
```

## Sécurité

- Les outils externes sont lancés sans shell. Le dossier courant et les entrées relatives du `PATH` sont ignorés, et seuls les `.exe` sont acceptés sous Windows.
- Les arguments sont transmis à ExifTool par l'entrée standard. Les noms de champs sont validés et les retours à la ligne refusés : aucune valeur ne peut devenir une option.
- FFmpeg reçoit les chemins préfixés par `file:`, ce qui empêche l'interprétation de protocoles.
- Chaque appel à un outil externe a un délai maximal et peut être annulé : le processus est alors tué. Fermer la fenêtre annule les traitements en cours.
- Les fichiers produits sont écrits sous un nom temporaire, relus et vérifiés (format, lisibilité), puis publiés sans jamais remplacer un fichier existant. Un traitement interrompu ou en échec ne laisse rien derrière lui.
- Le nettoyage de l'original demande une confirmation, et l'original n'est remplacé que par une copie vérifiée.
- Les images géantes (« bombes de décompression ») et les fichiers corrompus sont refusés avec un message clair ; `tests/test_malformed.py` couvre les fichiers tronqués, aléatoires, piégés et les réponses inattendues des outils. Le texte venu des fichiers est affiché en texte brut, jamais interprété comme du HTML.

Développé par **VISCHENZISCH**.
