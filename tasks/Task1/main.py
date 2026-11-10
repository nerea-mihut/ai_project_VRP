import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

# ==========================================================
# 1. Setări generale
# ==========================================================

NUM_CLIENTS = 125
CAPACITY = 1500
SEED = 42

rng = np.random.default_rng(SEED)

# ==========================================================
# 2. Coordonate geografice
# ==========================================================

# Depozit central: București
DEPOT_LAT = 44.4268
DEPOT_LON = 26.1025

# Limite aproximative ale României
ROMANIA_LAT_MIN = 43.6
ROMANIA_LAT_MAX = 48.3
ROMANIA_LON_MIN = 20.2
ROMANIA_LON_MAX = 29.7

# Generare aleatoare a celor 125 de clienți
client_lat = rng.uniform(ROMANIA_LAT_MIN, ROMANIA_LAT_MAX, NUM_CLIENTS)
client_lon = rng.uniform(ROMANIA_LON_MIN, ROMANIA_LON_MAX, NUM_CLIENTS)

# Cereri aleatoare între 15 și 200 kg
demands = rng.integers(15, 201, size=NUM_CLIENTS)

# ==========================================================
# 3. Formula Haversine
# ==========================================================

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculează distanța în kilometri dintre două puncte
    definite prin latitudine și longitudine.
    """
    R = 6371.0  # raza medie a Pământului, în km

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(a))

    return R * c

# ==========================================================
# 4. Matricea distanțelor
# ==========================================================

# Toate locațiile: depozit + clienți
latitudes = np.concatenate([[DEPOT_LAT], client_lat])
longitudes = np.concatenate([[DEPOT_LON], client_lon])

n_locations = len(latitudes)

distance_matrix = np.zeros((n_locations, n_locations))

for i in range(n_locations):
    for j in range(n_locations):
        distance_matrix[i, j] = haversine(
            latitudes[i],
            longitudes[i],
            latitudes[j],
            longitudes[j]
        )

print("Dimensiunea matricei de distanțe:", distance_matrix.shape)
print("Distanța depozit-client 1:", round(distance_matrix[0, 1], 2), "km")
print("Cererea totală:", demands.sum(), "kg")
print("Număr minim teoretic de dube:", int(np.ceil(demands.sum() / CAPACITY)))

# ==========================================================
# 5. Harta 2D simplificată a României
# ==========================================================

# Contur aproximativ al României
romania_outline = np.array([
    [22.2, 47.9],
    [24.0, 47.9],
    [26.0, 47.9],
    [28.2, 47.5],
    [29.6, 46.5],
    [29.0, 45.4],
    [28.0, 44.8],
    [27.0, 44.2],
    [25.5, 43.7],
    [23.5, 43.7],
    [22.5, 44.1],
    [21.0, 44.8],
    [20.2, 45.5],
    [20.7, 46.5],
    [22.2, 47.9]
])

fig, ax = plt.subplots(figsize=(10, 8))

# Desenăm conturul României
romania_polygon = Polygon(
    romania_outline,
    closed=True,
    facecolor="#eaf3ea",
    edgecolor="#2f6f3f",
    linewidth=2
)

ax.add_patch(romania_polygon)

# Depozitul
ax.scatter(
    DEPOT_LON,
    DEPOT_LAT,
    color="red",
    s=140,
    marker="*",
    label="Depozit central",
    zorder=5
)

# Clienții
ax.scatter(
    client_lon,
    client_lat,
    color="blue",
    s=45,
    label="Clienți",
    zorder=4
)

ax.set_title("Distribuția clienților pe teritoriul României")
ax.set_xlabel("Longitudine")
ax.set_ylabel("Latitudine")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig("harta_romania_clienti.png", dpi=300)
plt.show()