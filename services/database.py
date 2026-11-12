import json
import os
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

FICHIER_TOPICS = BASE_DIR / "data" / "topics.json"
FICHIER_SERVEURS = BASE_DIR / "data" / "serveurs.json"


def lire_json(chemin):
    """
    Lire un fichier JSON et retourner son contenu.
    """
    with open(chemin, "r", encoding="utf-8") as fichier:
        return json.load(fichier)


def enregistrer_json(chemin, donnees):
    """
    Enregistrer des données JSON de manière atomique.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    fichier_temporaire = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=chemin.parent,
            prefix=".pythonpedia_",
            suffix=".tmp",
            delete=False
        ) as fichier:

            fichier_temporaire = fichier.name

            json.dump(
                donnees,
                fichier,
                indent=4,
                ensure_ascii=False
            )

            fichier.flush()
            os.fsync(fichier.fileno())

        os.replace(fichier_temporaire, chemin)

    finally:
        if (
            fichier_temporaire is not None
            and os.path.exists(fichier_temporaire)
        ):
            os.remove(fichier_temporaire)


def charger_topics():
    """
    Récupérer les topics enregistrés localement.
    """
    return lire_json(FICHIER_TOPICS)


def charger_serveurs():
    """
    Récupérer les serveurs connus.
    """
    return lire_json(FICHIER_SERVEURS)