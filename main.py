#!/usr/bin/env python3
# Imports
import sys
from time import sleep
from PIL import Image
from pathlib import Path

# Les fonctions

def get_supported_formats():
    """Récupère dynamiquement les formats supportés par Pillow."""
    extensions = Image.registered_extensions()
    # On enlève le point devant l'extension pour l'affichage
    return sorted(list(set(ext.lstrip('.').lower() for ext in extensions)))

def conversionFormatImage():
    try:
        formats = get_supported_formats()
        
        chemin_input = input("\tEntrer le chemin de l'image : ").strip()
        if not chemin_input:
            return
            
        cheminImg = Path(chemin_input)
        
        if not cheminImg.exists():
            print(f"\r[!] Erreur : Le fichier {cheminImg} n'existe pas.")
            return

        print(f"\nFormats supportés : {', '.join(formats[:10])}... (et bien d'autres)")
        formatImg = input("\tEntrer le format de sortie (ex: png, webp, jpg) : ").strip().lower()

        # Validation du format (on accepte même si pas dans la liste courte si PIL le peut)
        print("\r[+] Traitement en cours...")
        Img = Image.open(cheminImg)
        nouveauCheminImg = cheminImg.with_suffix("." + formatImg)
        Img.save(nouveauCheminImg)
        
        print(f"\r[+] Image convertie avec succès de {cheminImg.suffix} en .{formatImg}")
        print(f"\r[+] Fichier de sortie : {nouveauCheminImg}")

    except Exception as e:
        print(f"\r[!] Une erreur est survenue : {e}")

def redimensionnerImage():
    try:
        chemin_input = input("\tEntrer le chemin de l'image à redimensionner : ").strip()
        if not chemin_input:
            return
            
        cheminImg = Path(chemin_input)
        
        if not cheminImg.exists():
            print(f"\r[!] Erreur : Le fichier {cheminImg} n'existe pas.")
            return

        Img = Image.open(cheminImg)
        largeur_orig, hauteur_orig = Img.size
        print(f"\tDimensions actuelles : {largeur_orig}x{hauteur_orig}")

        # Optionnel : Maintenir le ratio
        keep_ratio = input("\tMaintenir le ratio d'aspect ? (O/n) : ").strip().lower() != 'n'
        largeurImg = int(input("\tEntrer la nouvelle largeur : ").strip())
        
        if keep_ratio:
            ratio = largeurImg / float(largeur_orig)
            hauteurImg = int(float(hauteur_orig) * float(ratio))
            print(f"\tHauteur calculée pour le ratio : {hauteurImg}")
        else:
            hauteurImg = int(input("\tEntrer la nouvelle hauteur : ").strip())

        imgResize = Img.resize((largeurImg, hauteurImg), Image.Resampling.LANCZOS)
        
        nomSortie = f"{cheminImg.stem}_resized_{largeurImg}x{hauteurImg}{cheminImg.suffix}"
        cheminSortie = cheminImg.parent / nomSortie
        
        imgResize.save(cheminSortie, quality=95, optimize=True)
        
        tailleOrig = cheminImg.stat().st_size / 1024  # Ko
        tailleNew = cheminSortie.stat().st_size / 1024  # Ko

        print(f"\r[+] L'image est redimensionnée avec succès ({largeurImg}x{hauteurImg})")
        print(f"\r[+] Taille : {tailleOrig:.2f} Ko -> {tailleNew:.2f} Ko")
        print(f"\r[+] Fichier : {cheminSortie}")

    except ValueError:
        print(f"\r[!] Erreur : Veuillez entrer des nombres entiers pour les dimensions.")
    except Exception as e:
        print(f"\r[!] Désolé... Une erreur est survenue : {e}")

def menu():
    while True:
        print("\n" + ":"*40)
        print("      CONVERTISSEUR D'IMAGES PRO")
        print(":"*40)
        print("1. Convertir le format d'une image")
        print("2. Redimensionner une image (Resize)")
        print("Q. Quitter")
        print(":" * 40)
        
        choix = input("Votre choix : ").strip().lower()
        
        if choix == '1':
            conversionFormatImage()
        elif choix == '2':
            redimensionnerImage()
        elif choix == 'q':
            print("\rMerci d'avoir utilisé le convertisseur. À bientôt !")
            break
        else:
            print("\r[!] Choix invalide. Veuillez réessayer.")

# Appel principal
if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print("\n\rInterruption du programme. Fermeture...")
        sys.exit(0)