from pathlib import Path
from typing import List, Tuple
import torch


torch.manual_seed(0)


################################################### Création de données synthétiques 
# centres "vrais"
true_centers = torch.tensor([
    [0.0, 0.0],
    [5.0, 5.0],
    [0.0, 5.0]
])

n = 50

cluster_1 = torch.randn(n, 2) * 0.5 + true_centers[0]
cluster_2 = torch.randn(n, 2) * 0.5 + true_centers[1]
cluster_3 = torch.randn(n, 2) * 0.5 + true_centers[2]

X = torch.cat([cluster_1, cluster_2, cluster_3], dim=0)

####################################################

K = 3  # nombre de clusters
indices = torch.randperm(X.shape[0])[:K] #mélange les indices des points
centers = X[indices] # initialisation aléatoire des centres




# X : [N, d]
# centers : [K, d]

# On "ajoute" des dimensions pour pouvoir comparer tous les points à tous les centres
diff = X[:, None, :] - centers[None, :, :]   # [N, K, d]

# Distance euclidienne au carré
distances = (diff ** 2).sum(dim=2)            # [N, K]

# Pour chaque point, indice du centre le plus proche
labels = torch.argmin(distances, dim=1)       # [N]




tol = 1e-4

for iteration in range(100):
    diff = X[:, None, :] - centers[None, :, :]
    distances = (diff ** 2).sum(dim=2)  
    labels = torch.argmin(distances, dim=1)
    
    new_centers = torch.zeros_like(centers)
    for k in range(K):
        points_k = X[labels ==k]  # points du cluster k

        if points_k.shape[0] == 0:
            new_centers[k] = centers[k]  # Cluster vide, on garde l'ancien centre

        else:
            new_centers[k] = points_k.mean(dim=0)  # nouveau centre = moyenne des points du cluster

    shift = torch.norm(new_centers - centers)
    centers = new_centers.clone()
    if shift < tol:
        print(f"Convergence atteinte après {iteration} itérations.")
        break
    

print("centers:", centers)
print("sizes:", torch.bincount(labels))