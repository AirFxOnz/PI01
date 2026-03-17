"""
Main - Système de tri automatique de pièces

SYSTÈME DE COORDONNÉES :
  -La caméra est FIXE au-dessus du plateau 
  -La tête se place au coin (X=0, Y=320) pour ne pas gêner la photo.
  -Résolution capteur : 4056×3040 (Pi AI Camera).
  -L'image rognée fait ~3002×2918 pixels (dynamique selon crop).
  
  Conversion (dynamique) :
    mm_x = (pixel_x / crop_w) * 320
    mm_y = (1 - pixel_y / crop_h) * 320

  Les bacs sont sur le bord droit (X=320mm).
  
  Séquence de poussée pour chaque pièce :
    1.Approche XY au-dessus de la pièce (Z haute)
    2.Descente (Z basse, brosse touche le plateau)
    3.Alignement Y : pousser la pièce latéralement vers Y du bac
    4.Poussée X : pousser la pièce vers le bord droit (X=320)
    5.Remontée (Z haute)
    6.Aller et retour pour pousser les pièces qui seraient rester sur le bords
"""
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) #pour bien trouver les dépendences

import cv2
import tkinter as tk
from tkinter import messagebox

from src.detection import detecter_objets, GST_PIPELINE
from src.piece_priority import (
    Piece, Boite, Plateau,
    calculer_priorite, decrire_trajet
)
from src.tronxy_gui_pixel import TronxyPixelGUI
from src.bac_assignment_gui import BacAssignmentGUI

#  CONFIGURATION (tout en mm)

PLATE_W_MM = 320.0
PLATE_H_MM = 320.0
OFFSET_X_MM = 5.0 #pour que la brosse se pose bien au dessus des pièces (a regler en fonction de la position de la caméra)


LABEL_TO_BAC = {} # pour assigné les bacs

# Positions Y en mm des 4 bacs le long du bord droit
BACS_Y_MM = {
    1: 270,
    2: 200,
    3: 120,
    4: 50,
}
#6766767676767676676767676767667677667676767667676767676677676676767676767667676767676767676767
BORD_X_MM = 315.0

Z_HAUTE = 15
Z_BASSE = 2
Z_BASSE_VIS = 2

PLATEAU = Plateau(
    largeur=PLATE_W_MM,
    hauteur=PLATE_H_MM,
    boites={
        1: Boite(classe=1, position=270),
        2: Boite(classe=2, position=200),
        3: Boite(classe=3, position=120),
        4: Boite(classe=4, position=50),
    }
)

#Vitesse (mm/min)
F_RAPIDE = 6000
F_POUSSEE = 6000
F_Z = 1500
F_BALAYAGE = 6000

#Re-scan
RESCAN_EVERY_N = 3 # Reprends une photo toutes les n poussée de pièces


def pixels_vers_mm(px, py, crop_w, crop_h):
    mm_x = (1.0 - px / crop_w) * PLATE_W_MM
    mm_y = (py / crop_h) * PLATE_H_MM
    return round(mm_x, 2), round(mm_y, 2)

#GESTION CAMÉRA
class CameraManager:
    def __init__(self):
        self.cap = None

    def start(self): #démarre le truc
        if self.cap is None or not self.cap.isOpened():
            print("Démarrage de la caméra (GStreamer)...")
            self.cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER) #prends un photo avec le setup gst
            if not self.cap.isOpened():
                print("Erreur GStreamer. Tentative webcam standard (0)...")
                self.cap = cv2.VideoCapture(0)
            time.sleep(2)

    def get_frame(self): #prend la photo
        if self.cap is None or not self.cap.isOpened():
            self.start()
        if self.cap and self.cap.isOpened():
            for _ in range(5):
                self.cap.grab()
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None

    def stop(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            print("Caméra arrêtée.")


camera = CameraManager()

#faits touts le processus

def lancer_detection_seule():
    """Bouton 'Capturer + Détecter'."""
    frame = camera.get_frame() #prend photo
    if frame is not None:
        objets, crop_w, crop_h = lancer_detection(frame) # prends tout les résultats
    else:
        print("Erreur: Impossible de récupérer une image.")


def lancer_detection(frame):
    """Détecte et affiche. Retourne (objets, crop_w, crop_h)."""
    objets, img_result, img_debug, crop_w, crop_h = detecter_objets(frame) 
    cv2.imshow("Detection - Resultat", img_result)
    cv2.imshow("Detection - Debug", img_debug)
    print(f"{len(objets)} pièce(s) détectée(s) : {objets}")
    print(f"Image rognée : {crop_w}×{crop_h} px")
    return objets, crop_w, crop_h


def capturer_et_detecter(gui):
    """
    Déplace la tête hors champ, capture une photo, détecte les pièces.
    Retourne (objets, crop_w, crop_h, img_result) ou None si échec.
    """
    # Tête hors champ
    print("-> Déplacement tête hors champ...")
    gui.controller.send_command("G90")
    gui.controller.send_command(f"G1 X0 Y{PLATE_H_MM} Z{Z_HAUTE} F{F_RAPIDE}")
    gui.controller._drain_input()
    gui.controller.send_command("M400", timeout_s=60)
    time.sleep(0.5)

    # Capture
    frame = camera.get_frame()
    if frame is None:
        print("ERREUR : Image vide")
        return None

    # Détection
    objets, img_result, img_debug, crop_w, crop_h = detecter_objets(frame)
    cv2.imshow("Detection - Resultat", img_result)
    cv2.imshow("Detection - Debug", img_debug)
    cv2.waitKey(1)

    print(f"{len(objets)} pièce(s) détectée(s)")
    return objets, crop_w, crop_h, img_result


def convertir_en_pieces(objets_detectes, crop_w, crop_h):
    """
    Convertit les dicts de détection en Pieces (mm).
    Utilise le mapping dynamique LABEL_TO_BAC pour la classe (= numéro de bac).
    """
    pieces = [] #liste de toutes les pièces
    for i, obj in enumerate(objets_detectes, 1):
        bac_num = LABEL_TO_BAC.get(obj['classe']) #asigne les pièces a un bac
        if bac_num is None:
            print(f"  Pièce {i}: label '{obj['classe']}' sans bac assigné, ignorée.")
            continue

        mm_x, mm_y = pixels_vers_mm(obj['x'], obj['y'], crop_w, crop_h) #converti position des pièces
        print(f"  Pièce {i}: pixel({obj['x']}, {obj['y']}) "
              f"→ mm({mm_x}, {mm_y}) [{obj['classe']}→bac {bac_num}]")
        pieces.append(Piece(id=i, x=mm_x, y=mm_y, classe=bac_num)) #crée objet pièces
    return pieces


def calculer_ordre(pieces):
    """Calcule et affiche l'ordre de priorité."""
    ordre = calculer_priorite(pieces, PLATEAU)

    print("\n" + "=" * 50)
    print("  ORDRE DE PRIORITÉ")
    print("=" * 50)
    for rang, entry in enumerate(ordre, 1):
        p = entry["piece"]
        trajet = decrire_trajet(p, PLATEAU) #reçoit le trajet a faire à la pièce
        print(f"  {rang}. {p} | dist_bord={entry['dist_bord']:.1f}mm "
              f"| collisions={entry['collisions']} | {trajet}")

    return ordre


def deplacer_une_piece(gui, p):
    """Déplace une pièce vers son bac."""
    piece_mm_x = p.x
    piece_mm_y = p.y
    bac_y = BACS_Y_MM[p.classe]

    print(f"  Position pièce : ({piece_mm_x:.1f}, {piece_mm_y:.1f}) mm")
    print(f"  Bac cible : {p.classe} → (X={BORD_X_MM}, Y={bac_y})")

    # ÉTAPE 1:Approche avec offset X
    approche_x = max(piece_mm_x - OFFSET_X_MM, 0)
    gui.controller.send_command(f"G1 X{approche_x} Y{piece_mm_y} F{F_RAPIDE}")
    gui.controller.send_command("M400", timeout_s=15)

    # ÉTAPE 2:Descente
    gui.controller.send_command(f"G1 Z{Z_BASSE} F{F_Z}")
    gui.controller.send_command("M400", timeout_s=15)

    # ÉTAPE 3: Poussée X vers le bord
    gui.controller.send_command(f"G1 X{BORD_X_MM - 15} F{F_POUSSEE}") # 1cm du bord pour ne pas tomber dans le bon bac
    gui.controller.send_command("M400", timeout_s=15)

    # ÉTAPE 4: Alignement Y
    if abs(piece_mm_y - bac_y) > 1.0: #la pièce est devant le bon bac, au centre (marge de 1mm)
        gui.controller.send_command(f"G1 Y{bac_y} F{F_POUSSEE}")
        gui.controller.send_command("M400", timeout_s=15)

    # ÉTAPE 5:Balayage dans le bac
    gui.controller.send_command(f"G1 X{BORD_X_MM} F{F_POUSSEE}") #On pousse la pièce dans le bac
    gui.controller.send_command("M400", timeout_s=15)

    gui.controller.send_command(f"G1 X{BORD_X_MM-20} Z{Z_HAUTE} F{F_Z}") #On recule en montant pour faire le rebalayage
    gui.controller.send_command("M400", timeout_s=15)

    gui.controller.send_command(f"G1 Z{Z_BASSE} F{F_Z}") #Redescente
    gui.controller.send_command("M400", timeout_s=15)

    gui.controller.send_command(f"G1 X{BORD_X_MM} F{F_POUSSEE}") #repoussage
    gui.controller.send_command("M400", timeout_s=15)
    # ÉTAPE 6:Remontée
    gui.controller.send_command(f"G1 Z{Z_HAUTE} F{F_Z}")
    gui.controller.send_command("M400", timeout_s=15)


def pipeline_complet(gui):
    """Pipeline : Homing → Capture → Détection → Assignation bacs → Tri avec re-scan."""
    global LABEL_TO_BAC

    # 1.Homing
    gui.controller.send_command("G28", timeout_s=60)
    gui.controller.send_command("G90")

    # 2.Première capture + détection
    result = capturer_et_detecter(gui)
    if result is None:
        messagebox.showerror("Erreur", "Image vide (problème caméra)")
        return

    objets, crop_w, crop_h, img_result = result
    if not objets:
        messagebox.showinfo("Info", "Aucune pièce détectée.")
        return

    # 3.GUI d'assignation des bacs (bloquant)
    labels_trouves = list(set(obj['classe'] for obj in objets))
    print(f"Labels détectés : {labels_trouves}")

    assignment_gui = BacAssignmentGUI(
        parent=gui.root,
        labels=labels_trouves,
        bacs_y_mm=BACS_Y_MM,
        image=img_result
    )
    gui.root.wait_window(assignment_gui.window)

    if not assignment_gui.result:
        print("Assignation annulée.")
        return

    LABEL_TO_BAC = assignment_gui.result
    print(f"Mapping label → bac : {LABEL_TO_BAC}")

    # 4.Boucle de tri avec re-scan
    pieces_triees_total = 0

    while True:  #while pièce
        # Conversion + priorité
        print("\n--- Conversion pixels → mm ---")
        pieces = convertir_en_pieces(objets, crop_w, crop_h)
        if not pieces:
            print("Plus de pièces à trier.")
            break

        ordre = calculer_ordre(pieces)
        if not ordre:
            break

        print(f"\n--- Tri de {len(ordre)} pièce(s) ---")

        for i, entry in enumerate(ordre, 1):
            p = entry["piece"]
            print(f"\n--- Pièce {i}/{len(ordre)} ---")

            deplacer_une_piece(gui, p)
            pieces_triees_total += 1

            # Re-scan périodique
            if RESCAN_EVERY_N > 0 and i < len(ordre) and (pieces_triees_total % RESCAN_EVERY_N == 0):
                print(f"\n*** RE-SCAN après {pieces_triees_total} pièces ***")
                result = capturer_et_detecter(gui)
                if result is not None:
                    new_objets, crop_w, crop_h, img_result = result
                    if new_objets:
                        objets = new_objets
                        # On casse la boucle interne pour recalculer les priorités
                        break
                    else:
                        print("Plus de pièces détectées après re-scan.")
                        objets = []
                        break
        else:
            # Boucle for terminée sans break → toutes les pièces triées
            # Un dernier scan pour vérifier
            print(f"\n*** Scan final de vérification ***")
            result = capturer_et_detecter(gui)
            if result is not None:
                objets, crop_w, crop_h, img_result = result
                if not objets:
                    print("Plateau vide. Tri terminé !")
                    break
                else:
                    print(f"Encore {len(objets)} pièce(s) détectée(s), on continue.")
                    continue
            break

    # Retour position parking
    print(f"\n=== TRI TERMINÉ ({pieces_triees_total} pièces) ===")
    gui.controller.send_command(f"G1 X0 Y0 F{F_RAPIDE}")
    gui.controller.send_command("M400", timeout_s=30)

    gui.controller.send_command(f"G1 Z75 F{F_Z}")
    gui.controller.send_command("M400", timeout_s=15)

    messagebox.showinfo("Terminé", f"Cycle fini ! {pieces_triees_total} pièce(s) triée(s).")


def main():
    root = tk.Tk() #ensuite c'est la partie graphique

    def on_close():
        camera.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    gui = TronxyPixelGUI(root)

    btn_frame = tk.Frame(root)
    btn_frame.pack(fill=tk.X, padx=5, pady=10)

    tk.Button(
        btn_frame, text="📷 Capturer + Détecter",
        font=("Arial", 11), width=25,
        command=lancer_detection_seule
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        btn_frame, text=" Pipeline Complet (Auto)",
        font=("Arial", 11, "bold"), width=30,
        bg="#4CAF50", fg="white",
        command=lambda: pipeline_complet(gui)
    ).pack(side=tk.LEFT, padx=5)

    root.mainloop()


if __name__ == "__main__":
    main()
