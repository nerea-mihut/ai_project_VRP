import csv
import io
import unicodedata
import urllib.request
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

#harta cu toate localitatile (13755) ce genereaza un csv doar cu coordonatele

SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    "romania/localitati/master/orase.csv"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "date"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_FILE = DATA_DIR / "localitati_sursa.csv"
CSV_FILE = DATA_DIR / "localitati_romania.csv"
MAP_FILE = DATA_DIR / "harta_localitati_romania.png"



def normalize_text(text):
    text = text.lower().replace("ş", "ș").replace("ţ", "ț")
    text = unicodedata.normalize("NFD", text)

    return "".join(
        character
        for character in text
        if unicodedata.category(character) != "Mn"
    ).strip()


def download_source():
    if SOURCE_FILE.exists():
        print("Folosim fișierul deja descărcat.")
        return

    print("Descărcăm localitățile...")

    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Romania-Localities-Viewer/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()

        if not content:
            raise RuntimeError("Fișierul descărcat este gol.")

        SOURCE_FILE.write_bytes(content)

    except Exception as error:
        raise RuntimeError(
            "Descărcarea nu a reușit. Verifică internetul "
            "sau disponibilitatea sursei.\n"
            f"Detalii: {error}"
        ) from error


def load_localities():
    text = SOURCE_FILE.read_text(encoding="utf-8-sig")

    try:
        dialect = csv.Sniffer().sniff(
            text[:10000],
            delimiters=",;\t",
        )
        reader = csv.reader(io.StringIO(text), dialect)
    except csv.Error:
        reader = csv.reader(io.StringIO(text))

    localities = []
    seen = set()

    for row in reader:
        if len(row) < 4:
            continue

        try:
            longitude = float(row[0].strip())
            latitude = float(row[1].strip())
        except ValueError:
            continue

        name = row[2].strip()
        county = row[3].strip()

        if (
            not name
            or not county
            or not np.isfinite(latitude)
            or not np.isfinite(longitude)
            or not 43.5 <= latitude <= 48.5
            or not 20.0 <= longitude <= 30.0
        ):
            continue

        key = (
            normalize_text(name),
            normalize_text(county),
            round(latitude, 6),
            round(longitude, 6),
        )

        if key in seen:
            continue

        seen.add(key)

        localities.append({
            "localitate": name,
            "judet": county,
            "latitudine": latitude,
            "longitudine": longitude,
        })

    if not localities:
        raise RuntimeError(
            "Nu au fost citite localități valide. "
            "Verifică formatul fișierului sursă."
        )

    localities.sort(
        key=lambda item: (
            normalize_text(item["judet"]),
            normalize_text(item["localitate"]),
        )
    )

    return localities


def save_csv(localities):
    with CSV_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "id",
            "localitate",
            "judet",
            "latitudine",
            "longitudine",
        ])

        for locality_id, locality in enumerate(localities, start=1):
            writer.writerow([
                locality_id,
                locality["localitate"],
                locality["judet"],
                locality["latitudine"],
                locality["longitudine"],
            ])



def show_map(localities):
    coordinates = np.array([
        [item["longitudine"], item["latitudine"]]
        for item in localities
    ])

    fig, ax = plt.subplots(figsize=(14, 9))

    ax.scatter(
        coordinates[:, 0],
        coordinates[:, 1],
        s=5,
        color="royalblue",
        alpha=0.65,
        linewidths=0,
        label=f"Localități: {len(localities)}",
    )

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
        fontsize=10,
        zorder=10,
    )
    annotation.set_visible(False)

    highlight, = ax.plot(
        [],
        [],
        marker="o",
        color="red",
        markersize=7,
        linestyle="",
        zorder=5,
    )

    def on_click(event):
        # Nu selectăm puncte când este activ zoom/pan.
        toolbar = getattr(fig.canvas.manager, "toolbar", None)
        if toolbar is not None and toolbar.mode:
            return

        if event.inaxes != ax:
            return

        screen_coordinates = ax.transData.transform(coordinates)

        distances = np.linalg.norm(
            screen_coordinates - np.array([event.x, event.y]),
            axis=1,
        )

        index = int(np.argmin(distances))

        if distances[index] > 12:
            annotation.set_visible(False)
            highlight.set_data([], [])
        else:
            locality = localities[index]

            longitude = locality["longitudine"]
            latitude = locality["latitudine"]

            annotation.xy = (longitude, latitude)
            annotation.set_text(
                f'{locality["localitate"]}\n'
                f'Județ: {locality["judet"]}\n'
                f'Latitudine: {latitude:.6f}\n'
                f'Longitudine: {longitude:.6f}'
            )
            annotation.set_visible(True)
            highlight.set_data([longitude], [latitude])

            print(
                f'{locality["localitate"]}, '
                f'{locality["judet"]} | '
                f'{latitude:.6f}, {longitude:.6f}'
            )

        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_click)

    mean_latitude = coordinates[:, 1].mean()

    ax.set_aspect(
        1.0 / np.cos(np.radians(mean_latitude))
    )

    ax.set_xlim(
        coordinates[:, 0].min() - 0.2,
        coordinates[:, 0].max() + 0.2,
    )
    ax.set_ylim(
        coordinates[:, 1].min() - 0.2,
        coordinates[:, 1].max() + 0.2,
    )

    ax.set_title(
        "Localități din România\n"
        "Click pe un punct pentru nume, județ și coordonate"
    )
    ax.set_xlabel("Longitudine")
    ax.set_ylabel("Latitudine")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.3)

    fig.tight_layout()
    fig.savefig(MAP_FILE, dpi=300, bbox_inches="tight")

    plt.show()


def main():
    download_source()
    localities = load_localities()
    save_csv(localities)

    print(f"\nLocalități încărcate: {len(localities)}")
    print(f"CSV salvat: {CSV_FILE}")
    print(f"Hartă salvată: {MAP_FILE}")
    print("Nu se generează clienți, cereri sau matrice de distanțe.")

    show_map(localities)


if __name__ == "__main__":
    main()