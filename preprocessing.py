import os
import numpy as np
import cv2
from tqdm import tqdm
from skimage import io, color, filters, feature, util

#Configuratin des dossiers
DOSSIER_ENTREE = "dataset_vanilla"  
DOSSIER_SORTIE = "dataset_edge"                    

def ma_fonction_magique(image_path):
    #1. Lecture
    img = io.imread(image_path)
    
    #2. Conversion en niveau de gris 
    if len(img.shape) == 3:
        img = color.rgb2gray(img)
    elif len(img.shape) == 4: # Cas des images PNG avec transparence
        img = color.rgb2gray(img[:, :, :3])

    #3. LE SEUILLAGE "HARD" (Crucial pour ton fond bruité)
    #Si les images sont en float (0.0 à 1.0), on coupe sous 0.15
    #Si elles sont en int (0 à 255), on coupe sous 40
    #Par sécurité, on utilise img_as_float pour normaliser
    img = util.img_as_float(img)
    img[img < 0.15] = 0  # <--- C'est ça qui nettoie le fond !

    #4. Flou + Canny
    gaussian = filters.gaussian(img, sigma=2)
    edges = feature.canny(gaussian, sigma=2)

    #5. Conversion immédiate en 0-255 (uint8)
    return (edges * 255).astype(np.uint8)

def traiter_tout_le_dataset():
    #1. Créer le dossier de sortie
    if not os.path.exists(DOSSIER_SORTIE):
        os.makedirs(DOSSIER_SORTIE)
        print(f"Dossier créé : {DOSSIER_SORTIE}")

    #2. Lister les images
    extensions_valides = ('.png', '.jpg', '.jpeg', '.bmp', '.tif')
    fichiers = [f for f in os.listdir(DOSSIER_ENTREE) if f.lower().endswith(extensions_valides)]
    
    print(f"Traitement de {len(fichiers)} images en cours...")

    #3. Boucle de traitement
    compteur_reussite = 0
    
    for nom_fichier in tqdm(fichiers):
        chemin_complet = os.path.join(DOSSIER_ENTREE, nom_fichier)
        chemin_sortie = os.path.join(DOSSIER_SORTIE, nom_fichier)
        
        try:
            #A. Traitement
            image_traitee = ma_fonction_magique(chemin_complet)
            
            #B. Sauvegarde (on utilise OpenCV car c'est plus robuste pour sauvegarder du Noir et Blanc pur)
            cv2.imwrite(chemin_sortie, image_traitee)
            compteur_reussite += 1

        except Exception as e:
            print(f"ERREUR sur {nom_fichier} : {e}")

    print(f"\nTerminé ! {compteur_reussite}/{len(fichiers)} images traitées.")
    print(f"Dossier de sortie : {DOSSIER_SORTIE}")

if __name__ == "__main__":
    traiter_tout_le_dataset()