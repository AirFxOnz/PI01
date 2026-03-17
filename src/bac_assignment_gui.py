"""
Interface graphique pour assigner chaque classe détectée à un bac (1-4).
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2


class BacAssignmentGUI:
    #Fenêtre qui affiche l'image de détection et permet d'assigner chaque label détecté à un des 4 bacs.

    def __init__(self, parent, labels, bacs_y_mm, image):
        """
        Args:
            parent: fenêtre tkinter parente
            labels: liste des labels détectés (vis ,écrous, rondelles etc..)
            bacs_y_mm: dict {1: 270, 2: 200, 3: 120, 4: 50}
            image: image BGR (numpy) de la détection
        """
        self.result = None
        self.labels = sorted(labels)
        self.bacs_y_mm = bacs_y_mm
        self.combos = {}

        # Fenêtre 
        self.window = tk.Toplevel(parent)
        self.window.title("Assignation des bacs")
        self.window.transient(parent)
        self.window.grab_set()

        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        #Image de détection 
        img_frame = ttk.LabelFrame(main_frame, text="Détection")
        img_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.display_image(img_frame, image)

        # Panneau d'assignation 
        ctrl_frame = ttk.LabelFrame(main_frame, text="Assignation classe → bac")
        ctrl_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        #Description des bacs
        ttk.Label(ctrl_frame, text="Bacs physiques :",
                  font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(10, 5))

        for bac_num, y_pos in sorted(bacs_y_mm.items()):
            ttk.Label(ctrl_frame,
                      text=f"  Bac {bac_num} — Y={y_pos}mm",
                      font=("Arial", 9)).pack(anchor=tk.W, padx=15)

        ttk.Separator(ctrl_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        #Un combo par label
        ttk.Label(ctrl_frame, text="Choisissez le bac pour chaque classe :",
                  font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=10, pady=(0, 10))

        bac_choices = [f"Bac {n}" for n in sorted(bacs_y_mm.keys())]

        for label in self.labels:
            row = tk.Frame(ctrl_frame)
            row.pack(fill=tk.X, padx=10, pady=4)

            ttk.Label(row, text=f"{label} :", width=15,
                      font=("Arial", 10)).pack(side=tk.LEFT)

            combo = ttk.Combobox(row, values=bac_choices, state="readonly", width=10)
            combo.current(0)
            combo.pack(side=tk.LEFT, padx=5)
            self.combos[label] = combo

        ttk.Separator(ctrl_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        #Boutons
        btn_frame = tk.Frame(ctrl_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(btn_frame, text="Valider", font=("Arial", 11, "bold"),
                  bg="#4CAF50", fg="white", width=12,
                  command=self.validate).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Annuler", font=("Arial", 11),
                  width=12,
                  command=self.cancel).pack(side=tk.LEFT, padx=5)

        # Centrer la fenêtre
        self.window.update_idletasks()
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (w // 2)
        y = (self.window.winfo_screenheight() // 2) - (h // 2)
        self.window.geometry(f"+{x}+{y}")

    def display_image(self, frame, image_bgr):
        #Affiche l'image de détection redimensionnée dans le frame tkinter.
        # Conversion BGR → RGB
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)

        # Redimensionner pour tenir dans la fenêtre (max 600px de large)
        max_w = 600
        ratio = max_w / pil_img.width
        new_h = int(pil_img.height * ratio)
        pil_img = pil_img.resize((max_w, new_h), Image.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(pil_img)
        label = tk.Label(frame, image=self.tk_img)
        label.pack(padx=5, pady=5)

    def validate(self):
        #Récupère les assignations et ferme la fenêtre.
        self.result = {}
        for label, combo in self.combos.items():
            # Extraire le numéro du bac depuis "Bac N"
            bac_str = combo.get()
            bac_num = int(bac_str.split(" ")[1])
            self.result[label] = bac_num

        print(f"Assignation validée : {self.result}")
        self.window.destroy()

    def cancel(self):
        #Annule et ferme.
        self.result = None
        self.window.destroy()