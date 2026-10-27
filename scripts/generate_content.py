from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "generated"
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_REGULAR = 210
N_SPORT = 40

ADJ = ["Midnight", "Silent", "Golden", "Broken", "Hidden", "Last", "Crimson", "Electric",
       "Distant", "Wild", "Lost", "Rising", "Hollow", "Bright", "Iron"]
NOUN = ["Harbor", "Empire", "Letters", "Horizon", "Garden", "Signal", "Kingdom", "Promise",
        "River", "Shadows", "Journey", "Orchard", "Frontier", "Echo", "Station"]
GENRES = ["Drama", "Comedy", "Thriller", "Action", "Romance", "Documentary", "Kids"]
LANGS = ["Hindi", "English", "Tamil", "Telugu", "Bengali"]
LANG_P = [0.35, 0.25, 0.15, 0.15, 0.10]

combos = [f"{a} {b}" for a in ADJ for b in NOUN]
titles = rng.choice(combos, N_REGULAR, replace=False)   # unique titles

regular = pd.DataFrame({
    "title": titles,
    "genre": rng.choice(GENRES, N_REGULAR),
    "language": rng.choice(LANGS, N_REGULAR, p=LANG_P),
    "content_type": rng.choice(["Movie", "Series"], N_REGULAR, p=[0.55, 0.45]),
    "release_year": rng.integers(2015, 2026, N_REGULAR),
})

sport = pd.DataFrame({
    "title": [f"Premier T20 League - Match {i}" for i in range(1, N_SPORT + 1)],
    "genre": "Sports",
    "language": rng.choice(["Hindi", "English"], N_SPORT, p=[0.6, 0.4]),
    "content_type": "Live Sport",
    "release_year": 2025,
})

content = pd.concat([regular, sport], ignore_index=True)
content.insert(0, "content_id", content.index + 1)
content.to_csv(OUT_DIR / "content.csv", index=False)

print("Content rows:", len(content))
print(content["content_type"].value_counts())