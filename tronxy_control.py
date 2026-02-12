import serial
import time

"""programme permettant la connection et l'envoie de commande G-code pour les mouvements de l'imprimante, peut fonctionner en stand-alone
sur un terminal pour vérifier les connections  """

class TronxyController:
    def __init__(self, port='/dev/ttyACM0', baud=115200, timeout=1): #changer le port et baud rate en fonction des specs du périphérique
        self.port = port<sdf
        self.baud = baud
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout) #connection à l'imprimante
            time.sleep(2)
            self._drain_input() #élimine les potentiels messages résiduels
            print(f"Connecté à {self.port} @ {self.baud}")
            return True
        except Exception as e:
            print("Erreur connexion:", e)
            return False

    def _drain_input(self):
        """Vide le buffer série de tous les messages en attente."""
        if not self.ser:
            return
        time.sleep(0.1) #pour attendre les possibles message retardataires
        while self.ser.in_waiting:
            try:
                line = self.ser.readline().decode(errors='ignore').strip() #decode converti les octets en caractères, strip enlève les espaces
                if line:
                    print("RCV (drain):", line)
            except:
                break

    def send_command(self, command, wait_ok=True, timeout_s=15): # envoie commande Gcode
        if not self.ser or not self.ser.is_open: # vérifie la connection
            print("Non connecté")
            return False

        line = (command.strip() + '\n').encode() # met les caractères en UTF-8
        try:
            self.ser.write(line) #envoie la commande en série
            self.ser.flush()  #force l'envoie des données
            print("SND:", command)
        except Exception as e:
            print("Erreur envoi:", e)
            return False

        if wait_ok:
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                try:
                    resp = self.ser.readline().decode(errors='ignore').strip() #recupère la réponse de l'imprimante
                except:
                    resp = ''  #si erreur de lecture
                if resp:
                    print("RCV:", resp)
                    if 'ok' in resp.lower(): #si la réponse est 'ok' on répond True
                        return True
            print(f"Timeout attente OK ({timeout_s}s) pour: {command}")
            return False
        return True

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close() #ferme la connection
            print("Déconnecté")

    def home_all(self):
        return self.send_command("G28", timeout_s=60) #envoie la commande de homing par le port série

    def move_x(self, distance, speed=1500):
        self.send_command("G91", wait_ok=True) #passage en mode coordonnées relatives
        ok = self.send_command(f"G1 X{distance} F{speed}") #commande mouvement avec position et vitesse
        self.send_command("G90", wait_ok=True) #passage en mode coordonnées absolues
        return ok

    def move_y(self, distance, speed=1500):
        self.send_command("G91", wait_ok=True)
        ok = self.send_command(f"G1 Y{-float(distance)} F{speed}")
        self.send_command("G90", wait_ok=True)
        return ok

    def move_z(self, distance, speed=300):
        self.send_command("G91", wait_ok=True)
        ok = self.send_command(f"G1 Z{distance} F{speed}")
        self.send_command("G90", wait_ok=True)
        return ok

    def move_to(self, x, y, z, speed=1500):
        self.send_command("G90", wait_ok=True)
        return self.send_command(f"G1 X{x} Y{y} Z{z} F{speed}")

    def set_home_offset(self, z_offset):
        self.send_command(f"M206 Z{z_offset}") #applique un décalage sur la position de homing
        self.send_command("M500") #sauvegarde les changements dans l'eeprom
        print(f"Offset Z home défini à {z_offset}mm")


if __name__ == "__main__":
    ctrl = TronxyController(port='/dev/ttyACM0', baud=115200)
    if not ctrl.connect():
        exit(1)

    try: #control manuel si le programme n'est pas incorporé dans un main ou gui, pour le débug et autre
        while True:
            print("\n1: Home  2: Move X  3: Move Y  4: Move Z  5: Move to  6: Send raw  0: Quit")
            choice = input("Choix: ").strip()
            if choice == '1':
                ctrl.home_all()
            elif choice == '2':
                d = input("Distance X (mm): ")
                ctrl.move_x(d)
            elif choice == '3':
                d = input("Distance Y (mm): ")
                ctrl.move_y(d)
            elif choice == '4':
                d = input("Distance Z (mm): ")
                ctrl.move_z(d)
            elif choice == '5':
                x = input("X: "); y = input("Y: "); z = input("Z: ")
                ctrl.move_to(x, y, z)
            elif choice == '6':
                cmd = input("G-code: ")
                ctrl.send_command(cmd)
            elif choice == '0':
                break
            else:
                print("Choix invalide")
    finally:
        ctrl.disconnect()