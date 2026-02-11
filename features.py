from skimage import io
import numpy as np
import matplotlib.pyplot as plt

count = 0

def square_centered():
    L = np.zeros((2048,1542))
    L[999:1049 , 746:796] = 1
    plt.imshow(L, cmap='gray')
    return L


def count_pixels(A):
    a,b = L.shape
    for i in range(a):
        for j in range(b):
            if (A[i,j] == 1):
                count+=1
    print(count)

count_pixels(square_centered())

