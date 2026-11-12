import csv
import io
import math
import unicodedata
import urllib.request
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# environment ce genereaza 125 de clienti random pe map_generator

NUM_CLIENTS = 125
CAPACITY_KG = 1500

# Același seed => aceiași clienți și aceleași cereri.
# Pune None dacă vrei o instanță nouă la fiecare rulare.
INSTANCE_SEED = 44

DEPOT_NAME = "Depozit București"
DEPOT_LAT = 44.4268
DEPOT_LON = 26.1025

SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "romania/localitati/master/orase.csv"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "date"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_FILE = DATA_DIR / "localitati_sursa.csv"
LOCALITIES_FILE = DATA_DIR / "localitati_romania.csv"
CLIENTS_FILE = DATA_DIR / "clienti_selectati.csv"
MATRIX_FILE = DATA_DIR / "matrice_distante_km.csv"
MAP_FILE = DATA_DIR / "harta_clienti.png"


# FUNCȚII PENTRU DATE

def normalize_name(text):
    text = text.lower().replace("ş", "ș").replace("ţ", "ț")
    text = unicodedata.normalize("NFD", text)
    return "".join(
        char for char in text
        if unicodedata.category(char) != "Mn"
    ).strip()


def download_source():
    """Descarcă sursa numai dacă nu există deja local."""
    if SOURCE_FILE.exists():
        print("Folosim baza de localități deja descărcată.")
        return

    print("Descărcăm baza de localități din România...")

    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Student-CVRP-Project/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()

        if not content:
            raise ValueError("Serverul a returnat un fișier gol.")

        SOURCE_FILE.write_bytes(content)

    except Exception as exc:
        raise RuntimeError(
            "Nu am putut descărca baza de localități. "
            "Verifică internetul și disponibilitatea sursei.\n"
            f"Sursa: {SOURCE_URL}\n"
            f"Detalii: {exc}"
        ) from exc


def load_localities():
    """
    Formatul sursei:
    longitudine, latitudine, denumire, județ, ...

    Rândurile fără coordonate valide sunt omise.
    """
    text = SOURCE_FILE.read_text(encoding="utf-8-sig")

    sample = text[:10000]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        reader = csv.reader(io.StringIO(text), dialect)
    except csv.Error:
        reader = csv.reader(io.StringIO(text))

    localities = []
    seen = set()
    skipped = 0

    for row in reader:
        if len(row) < 4:
            skipped += 1
            continue

        try:
            lon = float(row[0].strip())
            lat = float(row[1].strip())
        except ValueError:
            # De exemplu: un eventual antet.
            skipped += 1
            continue

        name = row[2].strip()
        county = row[3].strip()

        if (
            not name
            or not county
            or not math.isfinite(lat)
            or not math.isfinite(lon)
            or not (43.5 <= lat <= 48.5)
            or not (20.0 <= lon <= 30.0)
        ):
            skipped += 1
            continue

        key = (
            normalize_name(name),
            normalize_name(county),
            round(lat, 6),
            round(lon, 6),
        )

        if key in seen:
            continue

        seen.add(key)

        localities.append({
            "localitate": name,
            "judet": county,
            "latitudine": lat,
            "longitudine": lon,
        })

    if len(localities) < NUM_CLIENTS:
        raise RuntimeError(
            f"Au fost citite doar {len(localities)} locații valide. "
            "Formatul sursei poate să se fi schimbat."
        )

    print(f"Localități încărcate: {len(localities)}")
    print(f"Rânduri omise/nevalide: {skipped}")

    return localities


def save_localities(localities):
    with LOCALITIES_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "localitate",
                "judet",
                "latitudine",
                "longitudine",
            ],
        )
        writer.writeheader()
        writer.writerows(localities)


# HAVERSINE

def haversine(lat1, lon1, lat2, lon2):
    """
    Distanța geografică în kilometri.
    Acceptă atât numere, cât și array-uri NumPy.
    Nu reprezintă distanța pe șosea.
    """
    earth_radius_km = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        np.sin(delta_lat / 2.0) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(delta_lon / 2.0) ** 2
    )

    a = np.clip(a, 0.0, 1.0)

    return (
        2.0
        * earth_radius_km
        * np.arcsin(np.sqrt(a))
    )


def build_distance_matrix(nodes):
    latitudes = np.array(
        [node["latitudine"] for node in nodes]
    )
    longitudes = np.array(
        [node["longitudine"] for node in nodes]
    )

    matrix = haversine(
        latitudes[:, None],
        longitudes[:, None],
        latitudes[None, :],
        longitudes[None, :],
    )

    np.fill_diagonal(matrix, 0.0)
    return matrix


# GENERAREA INSTANȚEI

def generate_nodes(localities):
    rng = np.random.default_rng(INSTANCE_SEED) #constructor

    # Nu selectăm o localitate numită București drept client,
    # deoarece depozitul este deja amplasat acolo.
    candidates = [
        locality
        for locality in localities
        if normalize_name(locality["localitate"])
        not in {"bucuresti", "municipiul bucuresti", "bucharest"}
    ]

    indices = rng.choice(
        len(candidates),
        size=NUM_CLIENTS,
        replace=False,
    )

    demands = rng.integers(
        low=15,
        high=201,
        size=NUM_CLIENTS,
    )

    nodes = [{
        "id": 0,
        "tip": "depozit",
        "localitate": DEPOT_NAME,
        "judet": "București",
        "latitudine": DEPOT_LAT,
        "longitudine": DEPOT_LON,
        "cerere_kg": 0,
    }]

    for client_id, (index, demand) in enumerate(
        zip(indices, demands), start=1
    ):
        locality = candidates[int(index)]

        nodes.append({
            "id": client_id,
            "tip": "client",
            "localitate": locality["localitate"],
            "judet": locality["judet"],
            "latitudine": locality["latitudine"],
            "longitudine": locality["longitudine"],
            "cerere_kg": int(demand),
        })

    return nodes


def save_instance(nodes, distance_matrix):
    with CLIENTS_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "tip",
                "localitate",
                "judet",
                "latitudine",
                "longitudine",
                "cerere_kg",
            ],
        )
        writer.writeheader()
        writer.writerows(nodes)

    # Rândul/coloana i corespunde nodului cu ID i.
    np.savetxt(
        MATRIX_FILE,
        distance_matrix,
        delimiter=",",
        fmt="%.6f",
    )


# VIZUALIZARE 2D


def plot_instance(localities, nodes):
    fig, ax = plt.subplots(figsize=(14, 9))

    # Toate localitățile formează un fundal de puncte reale.
    # Nu desenăm o graniță inventată a României.
    ax.scatter(
        [item["longitudine"] for item in localities],
        [item["latitudine"] for item in localities],
        s=2,
        color="#b8c5b5",
        alpha=0.35,
        linewidths=0,
        label="Localități disponibile",
        zorder=1,
    )

    clients = nodes[1:]

    ax.scatter(
        [node["longitudine"] for node in clients],
        [node["latitudine"] for node in clients],
        s=35,
        color="royalblue",
        edgecolors="white",
        linewidths=0.4,
        label=f"Clienți selectați ({NUM_CLIENTS})",
        zorder=3,
    )

    depot = nodes[0]

    ax.scatter(
        depot["longitudine"],
        depot["latitudine"],
        marker="*",
        s=240,
        color="red",
        edgecolors="darkred",
        label=DEPOT_NAME,
        zorder=5,
    )

    ax.annotate(
        "Depozit București",
        (depot["longitudine"], depot["latitudine"]),
        xytext=(8, -15),
        textcoords="offset points",
        fontsize=9,
        color="darkred",
        zorder=6,
    )

    # ID-urile sunt afișate permanent.
    for node in clients:
        ax.annotate(
            str(node["id"]),
            (node["longitudine"], node["latitudine"]),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=6,
            zorder=4,
        )

    # La click lângă un client, se afișează numele și cererea.
    annotation = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(15, 15),
        textcoords="offset points",
        bbox={
            "boxstyle": "round",
            "fc": "white",
            "ec": "gray",
            "alpha": 0.95,
        },
        arrowprops={"arrowstyle": "->"},
        fontsize=9,
        zorder=10,
    )
    annotation.set_visible(False)

    def on_click(event):
        if event.inaxes != ax:
            return

        if event.x is None or event.y is None:
            return

        coordinates = np.array([
            [node["longitudine"], node["latitudine"]]
            for node in nodes
        ])

        screen_coordinates = ax.transData.transform(coordinates)

        distances = np.linalg.norm(
            screen_coordinates - np.array([event.x, event.y]),
            axis=1,
        )

        nearest = int(np.argmin(distances))

        if distances[nearest] > 15:
            annotation.set_visible(False)
        else:
            node = nodes[nearest]
            annotation.xy = (
                node["longitudine"],
                node["latitudine"],
            )
            annotation.set_text(
                f'ID {node["id"]}: {node["localitate"]}\n'
                f'Județ: {node["judet"]}\n'
                f'Cerere: {node["cerere_kg"]} kg'
            )
            annotation.set_visible(True)

        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_click)

    mean_latitude = np.mean([
        node["latitudine"] for node in nodes
    ])
    ax.set_aspect(
        1.0 / np.cos(np.radians(mean_latitude))
    )

    ax.set_xlim(20.0, 30.0)
    ax.set_ylim(43.4, 48.6)
    ax.set_xlabel("Longitudine (grade)")
    ax.set_ylabel("Latitudine (grade)")
    ax.set_title(
        "Instanță CVRP — 125 de clienți în localități reale\n"
        "Click pe un punct pentru nume, județ și cerere"
    )
    ax.legend(loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.3)

    fig.tight_layout()
    fig.savefig(MAP_FILE, dpi=300, bbox_inches="tight")
    plt.show()


# PROGRAM PRINCIPAL

def main():
    download_source()

    localities = load_localities()
    save_localities(localities)

    nodes = generate_nodes(localities)
    distance_matrix = build_distance_matrix(nodes)

    assert distance_matrix.shape == (
        NUM_CLIENTS + 1,
        NUM_CLIENTS + 1,
    )
    assert np.allclose(
        distance_matrix,
        distance_matrix.T,
    )

    save_instance(nodes, distance_matrix)

    print("\n--- INSTANȚA GENERATĂ ---")
    print("Număr de clienți:", NUM_CLIENTS)
    print("Depozit:", DEPOT_NAME)
    print("Seed:", INSTANCE_SEED)
    print("Capacitate dubă:", CAPACITY_KG, "kg")
    print(
        "Cerere totală:",
        sum(node["cerere_kg"] for node in nodes),
        "kg",
    )
    print("Matrice distanțe:", distance_matrix.shape)

    print("\nPrimii 10 clienți:")
    for node in nodes[1:11]:
        print(
            f'{node["id"]:3d}. '
            f'{node["localitate"]}, {node["judet"]} | '
            f'{node["cerere_kg"]} kg | '
            f'Depozit-client: '
            f'{distance_matrix[0, node["id"]]:.2f} km'
        )

    print("\nFișiere salvate în:", DATA_DIR)
    print("-", LOCALITIES_FILE.name)
    print("-", CLIENTS_FILE.name)
    print("-", MATRIX_FILE.name)
    print("-", MAP_FILE.name)

    plot_instance(localities, nodes)


if __name__ == "__main__":
    main()