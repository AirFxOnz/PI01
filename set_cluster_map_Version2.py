"""
Utilitaire pour définir le mapping cluster → label.

Après avoir inspecté les dossiers resultats_kmeans/cluster_X/,
lancez ce script pour enregistrer l'association.

Utilisation :
  python set_cluster_map.py
"""

import os
import joblib

MODEL_DIR = "models"
CLUSTER_MAP_PATH = os.path.join(MODEL_DIR, "cluster_map.joblib")
KMEANS_PATH = os.path.join(MODEL_DIR, "kmeans.joblib")

LABELS_DISPONIBLES = ["Grande Vis", "Petite Vis", "Ecrou", "Rondelle", "Autre"]


def main():
    if not os.path.exists(KMEANS_PATH):
        print(f"ERREUR : KMeans introuvable ({KMEANS_PATH}).")
        print("Lancez d'abord train_classifier.py")
        return

    kmeans = joblib.load(KMEANS_PATH)
    n_clusters = kmeans.n_clusters

    print("=" * 50)
    print("  ASSOCIATION CLUSTER → LABEL")
    print("=" * 50)
    print(f"\nLabels disponibles : {LABELS_DISPONIBLES}")
    print(f"Nombre de clusters : {n_clusters}")
    print("\nInspectez les dossiers resultats_kmeans/cluster_X/ pour identifier les pièces.\n")

    cluster_map = {}
    for cid in range(n_clusters):
        while True:
            print(f"Cluster {cid} :")
            for i, lab in enumerate(LABELS_DISPONIBLES):
                print(f"  {i}: {lab}")
            choix = input(f"  Choix pour cluster {cid} (0-{len(LABELS_DISPONIBLES)-1}) : ").strip()
            try:
                idx = int(choix)
                if 0 <= idx < len(LABELS_DISPONIBLES):
                    cluster_map[cid] = LABELS_DISPONIBLES[idx]
                    print(f"  → Cluster {cid} = {LABELS_DISPONIBLES[idx]}\n")
                    break
                else:
                    print("  Index hors limites, réessayez.")
            except ValueError:
                print("  Entrée invalide, réessayez.")

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(cluster_map, CLUSTER_MAP_PATH)

    print("\n" + "=" * 50)
    print(f"Mapping sauvegardé dans '{CLUSTER_MAP_PATH}' :")
    for cid, lab in sorted(cluster_map.items()):
        print(f"  Cluster {cid} → {lab}")
    print("=" * 50)


if __name__ == "__main__":
    main()