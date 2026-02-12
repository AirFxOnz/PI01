import tkinter as tk
from tkinter import messagebox, ttk
import threading
from tronxy_control import TronxyController


class TronxyPixelGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Tronxy Control - Mode Pixels")
        self.root.geometry("700x500")

        GST_W = 2028 #definition largeur
        GST_H = 1520 #définition hauteur
        CUT_LEFT, CUT_RIGHT = 0.10, 0.16  #pourcentage de cropage des images
        CUT_TOP, CUT_BOTTOM = 0.0, 0.04 #pourcentage de cropage des images

        self.screen_width = float(int(GST_W * (1 - CUT_RIGHT)) - int(GST_W * CUT_LEFT))   # croppage des images
        self.screen_height = float(int(GST_H * (1 - CUT_BOTTOM)) - int(GST_H * CUT_TOP))  # croppage des images

        self.X_MIN, self.X_MAX = 0, 320  #définition des tailles plateau pour la tête
        self.Y_MIN, self.Y_MAX = 0, 320
        self.Z_MIN, self.Z_MAX = 0, 255

        self.current_x = 0.0 #position actuelle
        self.current_y = 0.0
        self.current_z = 0.0

        self.controller = TronxyController(port='/dev/ttyACM0', baud=115200)
        self.connected = False

        self.setup_ui()

    def setup_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(top_frame, text="Se connecter", command=self.connect).pack(side=tk.LEFT, padx=5) #bouton connection
        ttk.Button(top_frame, text="Déconnecter", command=self.disconnect).pack(side=tk.LEFT, padx=5) #bouton déconnection
        ttk.Button(top_frame, text="Home (G28)", command=self.home).pack(side=tk.LEFT, padx=5) #bouton homing

        self.status_label = ttk.Label(top_frame, text="Déconnecté", foreground="red")
        self.status_label.pack(side=tk.LEFT, padx=20)

        # Paramètres par défaut
        self.plate_width = 320.0 
        self.plate_height = 320.0
        self.screen_width = 1501.0
        self.screen_height = 1459.0

        input_frame = ttk.LabelFrame(self.root, text="Coordonnées pixels")
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(input_frame, text="Pixel X:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.pixel_x_var = tk.StringVar(value="0")
        ttk.Entry(input_frame, textvariable=self.pixel_x_var, width=15).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(input_frame, text="Pixel Y:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
        self.pixel_y_var = tk.StringVar(value="0")
        ttk.Entry(input_frame, textvariable=self.pixel_y_var, width=15).grid(row=0, column=3, sticky=tk.W)

        ttk.Label(input_frame, text="Z (mm):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.z_var = tk.StringVar(value="10")
        ttk.Entry(input_frame, textvariable=self.z_var, width=15).grid(row=1, column=1, sticky=tk.W)

        ttk.Label(input_frame, text="Vitesse (F):").grid(row=1, column=2, sticky=tk.W, padx=5, pady=3)
        self.speed_var = tk.StringVar(value="1500")
        ttk.Entry(input_frame, textvariable=self.speed_var, width=15).grid(row=1, column=3, sticky=tk.W)

        ttk.Button(input_frame, text="GO!", command=self.move_from_pixels, width=20).grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        info_frame = ttk.LabelFrame(self.root, text="Position convertie (mm)")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(info_frame, text="X (mm):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.x_label = ttk.Label(info_frame, text="0.0", foreground="blue", font=("Arial", 12, "bold"))
        self.x_label.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(info_frame, text="Y (mm):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=3)
        self.y_label = ttk.Label(info_frame, text="0.0", foreground="blue", font=("Arial", 12, "bold"))
        self.y_label.grid(row=0, column=3, sticky=tk.W)

    def pixels_vers_mm(self, px, py):
        mm_x = (1.0 - px / self.screen_width) * self.plate_width
        mm_y = (py / self.screen_height) * self.plate_height
        return round(mm_x, 2), round(mm_y, 2)

    def move_from_pixels(self):
        if not self.connected:
            messagebox.showwarning("Erreur", "Non connecté")
            return
        try:
            pixel_x = float(self.pixel_x_var.get())
            pixel_y = float(self.pixel_y_var.get())
            z = float(self.z_var.get())
            plate_x, plate_y = self.pixels_vers_mm(pixel_x, pixel_y)

            if not (self.X_MIN <= plate_x <= self.X_MAX):
                messagebox.showerror("Erreur", f"X hors limites"); return
            if not (self.Y_MIN <= plate_y <= self.Y_MAX):
                messagebox.showerror("Erreur", f"Y hors limites"); return
            if not (self.Z_MIN <= z <= self.Z_MAX):
                messagebox.showerror("Erreur", f"Z hors limites"); return

            self.x_label.config(text=f"{plate_x:.1f}")
            self.y_label.config(text=f"{plate_y:.1f}")
            self.move_to_position(plate_x, plate_y, z)
        except ValueError:
            messagebox.showerror("Erreur", "Coordonnées invalides")

    def move_to_position(self, x, y, z):
        speed = float(self.speed_var.get())
        thread = threading.Thread(target=self._move_thread, args=(x, y, z, speed))
        thread.daemon = True
        thread.start()

    def _move_thread(self, x, y, z, speed):
        try:
            self.controller.move_to(x, y, z, speed=int(speed))
            self.current_x = x
            self.current_y = y
            self.current_z = z
        except Exception as e:
            print(f"Erreur mouvement: {e}")

    def connect(self):
        if self.controller.connect():
            self.connected = True
            self.status_label.config(text="Connecté", foreground="green")
        else:
            messagebox.showerror("Erreur", "Impossible de se connecter")

    def disconnect(self):
        self.controller.disconnect()
        self.connected = False
        self.status_label.config(text="Déconnecté", foreground="red")

    def home(self):
        if not self.connected:
            messagebox.showwarning("Erreur", "Non connecté"); return
        def home_thread():
            self.controller.home_all()
            self.current_x = 200.0
            self.current_y = 170.0
            self.current_z = 12.0
            self.root.after(0, self.update_position_display)
        thread = threading.Thread(target=home_thread)
        thread.daemon = True
        thread.start()
        messagebox.showinfo("Info", "Homing en cours...")

    def update_position_display(self):
        self.x_label.config(text=f"{self.current_x:.1f}")
        self.y_label.config(text=f"{self.current_y:.1f}")


def main():
    root = tk.Tk()
    app = TronxyPixelGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()