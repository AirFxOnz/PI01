#!/usr/bin/env python3
"""
sort_screws.py
Script monofichier pour détecter et trier des vis avec une "imprimante 3D / bras"
Usage: adapter CONFIG en haut du fichier, tester en dry_run, calibrer conversion pixels->mm.
"""

import cv2
import numpy as np
import time
import math
import serial  # pour G-code via port série
from collections import namedtuple

# ----------------------------
# CONFIGURATION (à adapter)
# ----------------------------
DRY_RUN = True  # True = pas de mouvement réel (tester la vision & la logique)
BACKEND = "gcode"  # "gcode" ou "ros"
SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 115200

# caméra
CAMERA_ID = 0  # ou chemin RTSP / fichier
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# conversion pixels -> mm (à calibrer)
PIXEL_TO_MM = 0.2  # exemple: 0.2 mm par pixel (calibrer avec motif)

# Hauteurs Z (en mm)
Z_SAFE = 50      # hauteur de transit
Z_PICK = 5       # hauteur de préhension (au-dessus du plateau)
Z_DEPOSIT = 10   # hauteur de dépôt

# positions de tri (en mm dans repère machine) : à calibrer
BIN_COORDS = {
    "small": (150, 20, Z_DEPOSIT),
    "medium": (150, 60, Z_DEPOSIT),
    "large": (150, 100, Z_DEPOSIT),
    "unknown": (150, 140, Z_DEPOSIT),
}

# force/temps de préhension (si gripper pneumatique / servo)
GRIPPER_CLOSE_TIME = 0.5
GRIPPER_OPEN_TIME = 0.3

# seuils de classification (en mm) : adapter
THRESHOLD_LENGTH_MM = 10.0
THRESHOLD_DIAMETER_MM = 3.0

# ----------------------------
# Structures simples
# ----------------------------
Screw = namedtuple("Screw", ["cx_px", "cy_px", "length_mm", "diameter_mm", "label"])

# ----------------------------
# Robot controller abstraction
# ----------------------------
class RobotController:
    def move_to(self, x_mm, y_mm, z_mm, feedrate=3000):
        raise NotImplementedError

    def open_gripper(self):
        raise NotImplementedError

    def close_gripper(self):
        raise NotImplementedError

    def home(self):
        raise NotImplementedError

    def flush(self):
        pass

class GCodeRobot(RobotController):
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.ser = None
        if not DRY_RUN:
            self.ser = serial.Serial(port, baud, timeout=2)
            # give the board time to reset
            time.sleep(2)
            self._read_all()

    def _send(self, line):
        print("[GCODE] ->", line.strip())
        if DRY_RUN:
            return
        self.ser.write((line + "\n").encode('utf-8'))
        self.ser.flush()
        time.sleep(0.05)
        self._read_all()

    def _read_all(self):
        if not DRY_RUN:
            time.sleep(0.05)
            while self.ser.in_waiting:
                s = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if s:
                    print("[GCODE] <-", s)

    def move_to(self, x_mm, y_mm, z_mm, feedrate=3000):
        cmd = f"G0 X{x_mm:.2f} Y{y_mm:.2f} Z{z_mm:.2f} F{feedrate}"
        self._send(cmd)

    def open_gripper(self):
        # exemple: commande servo sur pin (dépend du firmware). Ici envoi M280 P0 S0 comme exemple.
        self._send("M280 P0 S10")  # à adapter
        time.sleep(GRIPPER_OPEN_TIME)

    def close_gripper(self):
        self._send("M280 P0 S90")  # à adapter
        time.sleep(GRIPPER_CLOSE_TIME)

    def home(self):
        self._send("G28")

class MockRobot(RobotController):
    def move_to(self, x_mm, y_mm, z_mm, feedrate=3000):
        print(f"[MOCK] move_to X{ x_mm } Y{ y_mm } Z{ z_mm }")

    def open_gripper(self):
        print("[MOCK] open gripper")

    def close_gripper(self):
        print("[MOCK] close gripper")

    def home(self):
        print("[MOCK] home")

# ----------------------------
# Vision utilities
# ----------------------------
def capture_frame(cap):
    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("Impossible de lire la caméra")
    return frame

def preprocess(frame):
    # placer au besoin une correction d'éclairage, filtre
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th

def detect_screws(frame):
    """
    Retourne une liste de Screw avec centre en pixels et mesures estimées en mm.
    Méthode simple basée sur contours : on approxime length ~ boundingRect height,
    diameter ~ équivalent diameter du contour.
    """
    th = preprocess(frame)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    screws = []
    vis = frame.copy()
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 80:  # bruit
            continue
        x,y,w,h = cv2.boundingRect(cnt)
        cx = x + w/2
        cy = y + h/2
        # estimer longueur/diamètre (utiles si vis posées horizontalement)
        length_px = max(w,h)
        diameter_px = math.sqrt(area / math.pi) * 2
        length_mm = length_px * PIXEL_TO_MM
        diameter_mm = diameter_px * PIXEL_TO_MM
        label = classify_screw(length_mm, diameter_mm)
        screws.append(Screw(cx, cy, length_mm, diameter_mm, label))
        # dessin pour debug
        cv2.rectangle(vis, (x,y), (x+w, y+h), (0,255,0), 1)
        cv2.putText(vis, f"{label:.>7}", (int(cx), int(cy)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,0,255), 1)
    return screws, vis

def classify_screw(length_mm, diameter_mm):
    # règle simple : small/medium/large
    if length_mm < THRESHOLD_LENGTH_MM and diameter_mm < THRESHOLD_DIAMETER_MM:
        return "small"
    if length_mm < 2*THRESHOLD_LENGTH_MM:
        return "medium"
    return "large"

# conversion pixel coords -> machine coords (X,Y in mm)
def pixel_to_machine(cx_px, cy_px, frame_shape, origin_machine=(0,0), offset_mm=(0,0)):
    # simple centering: assume camera centered over a known origin.
    # frame_shape: (h, w, ...)
    h, w = frame_shape[:2]
    # pixel offset from center
    dx_px = (cx_px - w/2)
    dy_px = (cy_px - h/2)
    # convert
    dx_mm = dx_px * PIXEL_TO_MM
    dy_mm = dy_px * PIXEL_TO_MM
    # machine coords: origin_machine + offset
    mx = origin_machine[0] + offset_mm[0] + dx_mm
    my = origin_machine[1] + offset_mm[1] + dy_mm
    return mx, my

# ----------------------------
# High-level pick & place
# ----------------------------
def pick_and_place(robot: RobotController, screw: Screw, frame_shape, origin_machine=(100,50), offset_mm=(0,0)):
    # calculer coord machine pour le centre détecté
    x_mm, y_mm = pixel_to_machine(screw.cx_px, screw.cy_px, frame_shape, origin_machine, offset_mm)
    # approche safe
    robot.move_to(x_mm, y_mm, Z_SAFE)
    robot.move_to(x_mm, y_mm, Z_PICK)
    robot.close_gripper()
    robot.move_to(x_mm, y_mm, Z_SAFE)
    # destination
    dest = BIN_COORDS.get(screw.label, BIN_COORDS["unknown"])
    dx, dy, dz = dest
    robot.move_to(dx, dy, Z_SAFE)
    robot.move_to(dx, dy, dz)
    robot.open_gripper()
    robot.move_to(dx, dy, Z_SAFE)

# ----------------------------
# Main
# ----------------------------
def main():
    # initialiser robot
    if DRY_RUN:
        robot = MockRobot()
    else:
        if BACKEND == "gcode":
            robot = GCodeRobot(SERIAL_PORT, BAUDRATE)
        elif BACKEND == "ros":
            # Placeholder: implémentation ROS/MoveIt requiert rospy, moveit_commander
            raise NotImplementedError("Backend ROS non implémenté dans ce script monofichier.")
        else:
            raise ValueError("Backend inconnu.")

    print("Home robot")
    robot.home()
    time.sleep(1)

    cap = cv2.VideoCapture(CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    try:
        while True:
            frame = capture_frame(cap)
            screws, vis = detect_screws(frame)
            print(f"Detected {len(screws)} screws")
            # tri simple: itérer sur chaque vis détectée, pick & place
            # IMPORTANT: pourrait vouloir choisir la vis la plus proche d'abord pour éviter collisions
            for s in screws:
                print(f"-> screw at px ({s.cx_px:.1f},{s.cy_px:.1f}) len {s.length_mm:.1f}mm dia {s.diameter_mm:.1f}mm -> {s.label}")
                pick_and_place(robot, s, frame.shape, origin_machine=(100,50), offset_mm=(0,0))
                # petitr délai pour stabiliser
                time.sleep(0.5)

            # affichage debug
            cv2.imshow("vis_detection", vis)
            key = cv2.waitKey(100) & 0xFF
            if key == ord('q'):
                break
            # relancer boucle ; dans un vrai sys on voudra repérer uniquement nouvelles vis
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if not DRY_RUN and isinstance(robot, GCodeRobot):
            robot._send("M84")  # disable motors
            robot._read_all()

if __name__ == "__main__":
    main()
