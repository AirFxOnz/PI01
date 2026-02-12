import cv2
import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from skimage import color, filters, feature, util
import joblib
import os

# ==========================================
# CONFIGURATION
# ==========================================
CANNY_LOW = 50
CANNY_HIGH = 70
CUT_TOP_PCT, CUT_BOTTOM_PCT = 0, 0.03
CUT_LEFT_PCT, CUT_RIGHT_PCT = 0.13, 0.105

GST_PIPELINE = (
    "libcamerasrc ! video/x-raw, format=NV12, width=2028, height=1520, framerate=1/1 "
    "! videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
)

# Chemins vers les modèles pré-entraînés
MODEL_DIR = "models"
PCA_PATH = os.path.join(MODEL_DIR, "pca.joblib")
KMEANS_PATH = os.path.join(MODEL_DIR, "kmeans.joblib")
CLUSTER_MAP_PATH = os.path.join(MODEL_DIR, "cluster_map.joblib")

# Mapping par défaut cluster → label
DEFAULT_CLUSTER_MAP = {
    0: "Grande Vis",
    1: "Petite Vis",
    2: "Ecrou",
    3: "Rondelle",
    4: "Autre",
}

# Couleurs par label pour le dessin
COULEURS_LABEL = {
    "Grande Vis": (255, 0, 0),
    "Petite Vis": (255, 150, 0),
    "Ecrou": (0, 255, 0),
    "Rondelle": (0, 255, 255),
    "Autre": (128, 128, 128),
}


class Classifier:
    """
    Classifieur basé sur DINOv2 + PCA + KMeans.
    Charge les modèles pré-entraînés au démarrage.
    """

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.pca = None
        self.kmeans = None
        self.cluster_map = None
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])
        self._loaded = False

    def load(self):
        """Charge DINOv2 et les modèles PCA/KMeans sauvegardés."""
        if self._loaded:
            return

        print("Chargement de DINOv2...")
        self.model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vits14')
        self.model.to(self.device)
        self.model.eval()

        if os.path.exists(PCA_PATH) and os.path.exists(KMEANS_PATH):
            print("Chargement PCA + KMeans pré-entraînés...")
            self.pca = joblib.load(PCA_PATH)
            self.kmeans = joblib.load(KMEANS_PATH)
        else:
            print(f"ATTENTION : Modèles PCA/KMeans introuvables dans '{MODEL_DIR}/'.")
            print("Lancez d'abord train_classifier.py pour entraîner et sauvegarder les modèles.")
            self.pca = None
            self.kmeans = None

        if os.path.exists(CLUSTER_MAP_PATH):
            self.cluster_map = joblib.load(CLUSTER_MAP_PATH)
            print(f"Mapping clusters chargé : {self.cluster_map}")
        else:
            self.cluster_map = DEFAULT_CLUSTER_MAP
            print(f"Mapping clusters par défaut : {self.cluster_map}")

        self._loaded = True
        print("Classifieur prêt.")

    def preprocess_edge(self, crop_bgr):
        """
        Applique le même prétraitement que preprocessing.py sur un crop BGR.
        Retourne une image edges en uint8 (0 ou 255).
        """
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        gray = color.rgb2gray(rgb)
        gray = util.img_as_float(gray)

        # Seuillage hard (nettoie le fond bruité)
        gray[gray < 0.15] = 0

        # Flou + Canny (scikit-image)
        gaussian = filters.gaussian(gray, sigma=2)
        edges = feature.canny(gaussian, sigma=2)

        return (edges * 255).astype(np.uint8)

    def classify_crop(self, crop_bgr):
        """
        Classifie un crop BGR d'une pièce individuelle.
        1. Prétraitement edges (comme preprocessing.py)
        2. Conversion en image RGB 3 canaux (edges répliqué)
        3. Extraction features DINOv2
        4. PCA → KMeans → label

        Retourne (label_str, cluster_id) ou ("Inconnu", -1) si modèles non chargés.
        """
        if self.pca is None or self.kmeans is None:
            return "Inconnu", -1

        # 1. Prétraitement : même pipeline que preprocessing.py
        edges = self.preprocess_edge(crop_bgr)

        # 2. Convertir edges mono-canal en image RGB 3 canaux pour DINOv2
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        pil_img = Image.fromarray(edges_rgb)

        # 3. Extraction features DINOv2
        img_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            feat = self.model(img_tensor)
        feat_np = feat.cpu().numpy().flatten().reshape(1, -1)

        # 4. PCA + KMeans
        feat_reduced = self.pca.transform(feat_np)
        cluster_id = int(self.kmeans.predict(feat_reduced)[0])

        label = self.cluster_map.get(cluster_id, "Autre")
        return label, cluster_id


# Instance globale du classifieur (chargement paresseux)
_classifier = Classifier()


def detecter_objets(frame):
    """
    Analyse la frame et retourne (données_objets, image_dessinée, image_debug, crop_w, crop_h).

    Pipeline :
      1. Rognage (ROI)
      2. Détection de contours (localisation des pièces)
      3. Pour chaque contour : extraction du crop → classification DINOv2
      4. Dessin des résultats
    """
    # Chargement paresseux du classifieur
    _classifier.load()

    donnees_objets = []

    # 1. ROGNAGE (ROI)
    height, width, _ = frame.shape
    y_start = int(height * CUT_TOP_PCT)
    y_end = int(height * (1 - CUT_BOTTOM_PCT))
    x_start = int(width * CUT_LEFT_PCT)
    x_end = int(width * (1 - CUT_RIGHT_PCT))
    cropped = frame[y_start:y_end, x_start:x_end]

    crop_h, crop_w = cropped.shape[:2]

    # 2. PRÉ-TRAITEMENT POUR DÉTECTION DE CONTOURS (localisation uniquement)
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (13, 13), 0)
    edges = cv2.Canny(blur, CANNY_LOW, CANNY_HIGH)
    kernel = np.ones((7, 7), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=1)

    # Exclusion zone morte bas-droite
    h_d, w_d = dilated.shape
    exclude_w = int(w_d * 0.02)
    exclude_h = int(h_d * 0.03)
    dilated[h_d - exclude_h: h_d, w_d - exclude_w: w_d] = 0

    # Exclusion des bords
    b = 100
    dilated[0:b, :] = 0
    dilated[h_d - b:h_d, :] = 0
    dilated[:, 0:b] = 0
    dilated[:, w_d - b:w_d] = 0

    # 3. EXTRACTION DES CONTOURS
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    area_min = int(100 * (crop_w * crop_h) / (474 * 461))

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < area_min:
            continue

        M = cv2.moments(cnt)
        if M['m00'] == 0:
            continue
        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])

        # 4. EXTRACTION DU CROP pour classification
        x_bb, y_bb, w_bb, h_bb = cv2.boundingRect(cnt)

        # Marge autour du bounding box (20%)
        margin_x = int(w_bb * 0.2)
        margin_y = int(h_bb * 0.2)
        x1 = max(0, x_bb - margin_x)
        y1 = max(0, y_bb - margin_y)
        x2 = min(crop_w, x_bb + w_bb + margin_x)
        y2 = min(crop_h, y_bb + h_bb + margin_y)

        piece_crop = cropped[y1:y2, x1:x2]

        if piece_crop.size == 0:
            continue

        # 5. CLASSIFICATION par DINOv2 + PCA + KMeans
        label, cluster_id = _classifier.classify_crop(piece_crop)
        couleur = COULEURS_LABEL.get(label, (128, 128, 128))

        # 6. DESSIN
        cv2.drawContours(cropped, [cnt], -1, couleur, 2)
        cv2.circle(cropped, (cx, cy), 5, (0, 0, 255), -1)
        cv2.putText(cropped, f"{label} (C:{cluster_id})", (cx - 30, cy - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        donnees_objets.append({
            'classe': label,
            'x': cx,
            'y': cy
        })

    return donnees_objets, cropped, dilated, crop_w, crop_h


if __name__ == "__main__":
    cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        liste_pieces, img_resultat, img_debug, crop_w, crop_h = detecter_objets(frame)

        if len(liste_pieces) > 0:
            print(f"Détection : {liste_pieces}")

        cv2.imshow('Multi-Detection (Resultat)', img_resultat)
        cv2.imshow('DEBUG (Dilatation)', img_debug)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()