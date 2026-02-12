import serial
import time


class TronxyController:
    def __init__(self, port='/dev/ttyACM0', baud=115200, timeout=1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            time.sleep(2)
            self._drain_input()
            print(f"Connecté à {self.port} @ {self.baud}")
            return True
        except Exception as e:
            print("Erreur connexion:", e)
            return False

    def _drain_input(self):
        """Vide le buffer série de tous les messages en attente."""
        if not self.ser:
            return
        time.sleep(0.1)
        while self.ser.in_waiting:
            try:
                line = self.ser.readline().decode(errors='ignore').strip()
                if line:
                    print("RCV (drain):", line)
            except:
                break

    def send_command(self, command, wait_ok=True, timeout_s=15):
        """Envoie une commande G-code et attend 'ok'."""
        if not self.ser or not self.ser.is_open:
            print("Non connecté")
            return False

        line = (command.strip() + '\n').encode()
        try:
            self.ser.write(line)
            self.ser.flush()
            print("SND:", command)
        except Exception as e:
            print("Erreur envoi:", e)
            return False

        if wait_ok:
            deadline = time.time() + timeout_s
            while time.time() < deadline:
                try:
                    resp = self.ser.readline().decode(errors='ignore').strip()
                except:
                    resp = ''
                if resp:
                    print("RCV:", resp)
                    if 'ok' in resp.lower():
                        return True
            print(f"Timeout attente OK ({timeout_s}s) pour: {command}")
            return False
        return True

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Déconnecté")

    def home_all(self):
        return self.send_command("G28", timeout_s=60)

    def move_x(self, distance, speed=1500):
        self.send_command("G91", wait_ok=True)
        ok = self.send_command(f"G1 X{distance} F{speed}")
        self.send_command("G90", wait_ok=True)
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
        self.send_command(f"M206 Z{z_offset}")
        self.send_command("M500")
        print(f"Offset Z home défini à {z_offset}mm")


if __name__ == "__main__":
    ctrl = TronxyController(port='/dev/ttyACM0', baud=115200)
    if not ctrl.connect():
        exit(1)

    try:
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