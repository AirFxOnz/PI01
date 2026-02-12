"""
Ce script :
  1. Charge toutes les images edge du dataset
  2. Extrait les features avec DINOv2
  3. Entraîne PCA + KMeans
  4. Sauvegarde les modèles dans un dossier
  5. Affiche les clusters pour permettre l'association cluster → label
"""

import os
import shutil
import numpy as np
import torch
from pathlib import Path
from PIL import Image
from tqdm import tqdm
from torchvision import transforms
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import joblib


DATASET_PATH = "dataset_edge_new" #Dataset edge généré par preprocessing.py
OUTPUT_DIR = "resultats_kmeans"
MODEL_DIR = "models"
N_CLUSTERS = 5 # Avec 4 clusters les résultats sont moins bons, 5 semble mieux séparer les pièces (nous n'avons que 4 bacs pour rappel)
PCA_COMPONENTS = 50


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    #1 Charger DINOv2
    device = "cuda" if torch.cuda.is_available() else "cpu" #Nous l'avons fait tourner sur CPU, la vitesse était acceptable
    print(f"Device : {device}")

    model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vitb14')
    model.to(device)
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225])
    ])

    #2 Lister les images
    image_paths = []
    for root, dirs, files in os.walk(DATASET_PATH):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_paths.append(os.path.join(root, file))

    print(f"Nombre d'images trouvées : {len(image_paths)}")
    if len(image_paths) == 0:
        print(f"ERREUR : Aucune image dans '{DATASET_PATH}/'.")
        print("Lancez d'abord preprocessing.py pour générer le dataset edge.")
        return

    #3 Extraction des features avec DINOv2
    features = []
    for img_path in tqdm(image_paths, desc="Extraction features"):
        img = Image.open(img_path).convert("RGB")
        img_tensor = transform(img).unsqueeze(0).to(device)
        with torch.no_grad():
            feat = model(img_tensor)
        features.append(feat.cpu().numpy().flatten())

    X = np.array(features)
    print(f"Shape des features : {X.shape}")

    #4 PCA (réduction de dimension)
    pca = PCA(n_components=PCA_COMPONENTS)
    X_reduced = pca.fit_transform(X)
    print(f"Shape après PCA : {X_reduced.shape}")
    print(f"Variance expliquée cumulée : {pca.explained_variance_ratio_.sum():.2%}")

    #5 KMeans
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    kmeans.fit(X_reduced)
    labels = kmeans.labels_
    print("Clustering terminé.")

    #6 Sauvegarder les modèles
    joblib.dump(pca, os.path.join(MODEL_DIR, "pca.joblib"))
    joblib.dump(kmeans, os.path.join(MODEL_DIR, "kmeans.joblib"))
    print(f"Modèles sauvegardés dans '{MODEL_DIR}/'")

    #7 Copier les images dans les dossiers par cluster 
    for cluster_id in range(N_CLUSTERS):
        cluster_dir = os.path.join(OUTPUT_DIR, f"cluster_{cluster_id}")
        os.makedirs(cluster_dir, exist_ok=True)

    cluster_counts = {i: 0 for i in range(N_CLUSTERS)}
    for img_path, label in zip(image_paths, labels):
        dest_folder = os.path.join(OUTPUT_DIR, f"cluster_{label}")
        shutil.copy2(img_path, os.path.join(dest_folder, os.path.basename(img_path)))
        cluster_counts[label] += 1

    print(f"\nImages classées dans '{OUTPUT_DIR}/'")


if __name__ == "__main__":
    main()
