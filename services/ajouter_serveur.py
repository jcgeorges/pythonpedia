import json
from pathlib import Path
from urllib.parse import urlsplit

FICHIER = Path(__file__).resolve().parent.parent / "data" / "serveurs.json"

adresse = input("Adresse du nouveau serveur : ").strip().rstrip("/")

url = urlsplit(adresse)

if (
    url.scheme != "http"
    or not url.hostname
    or url.port is None
    or url.path not in ("", "/")
    or url.username is not None
    or url.password is not None
    or url.query
    or url.fragment
):
    print("Adresse invalide.")

else:
    with open(FICHIER, "r", encoding="utf-8") as f:
        serveurs = json.load(f)

    if adresse in serveurs:
        print("Serveur déjà enregistré.")
    else:
        serveurs.append(adresse)

        with open(FICHIER, "w", encoding="utf-8") as f:
            json.dump(serveurs, f, indent=4)

        print("Nouveau serveur ajouté.")