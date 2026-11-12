"""
Ce script crée trois copies de mon application.

Chaque copie possède :
- Son propre fichier app.py.
- Ses propres fichiers JSON.
- Son propre programme de synchronisation.
- Ses propres templates HTML.
Les trois serveurs fonctionnent donc indépendamment, même s'ils sont exécutés sur le même ordinateur.
"""

import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEMO_DIR = BASE_DIR / "demo"

SERVEURS = {
    "serveur_a": {
        "port": 5000,
        "topics": {
            "fonctions": {
                "definition": [
                    "https://docs.python.org/fr/3/tutorial/controlflow.html"
                ]
            },
            "POO": {
                "tutoriel": [
                    "https://docs.python.org/fr/3/tutorial/classes.html"
                ]
            },
            "exceptions": {
                "exemple": [
                    "https://docs.python.org/fr/3/tutorial/errors.html"
                ]
            }
        },
        "annuaire": [
            "http://127.0.0.1:5001"
        ]
    },

    "serveur_b": {
        "port": 5001,
        "topics": {
            "decorateurs": {
                "definition": [
                    "https://docs.python.org/fr/3/glossary.html#term-decorator"
                ]
            },
            "modules": {
                "tutoriel": [
                    "https://docs.python.org/fr/3/tutorial/modules.html"
                ]
            }
        },
        "annuaire": [
            "http://127.0.0.1:5000",
            "http://127.0.0.1:5002"
        ]
    },

    "serveur_c": {
        "port": 5002,
        "topics": {
            "multithreading": {
                "tutoriel": [
                    "https://docs.python.org/fr/3/library/threading.html"
                ]
            },
            "fichiers": {
                "exemple": [
                    "https://docs.python.org/fr/3/tutorial/inputoutput.html"
                ]
            }
        },
        "annuaire": [
            "http://127.0.0.1:5001"
        ]
    }
}


def enregistrer_json(chemin, donnees):

    with open(chemin, "w", encoding="utf-8") as fichier:
        json.dump(
            donnees,
            fichier,
            indent=4,
            ensure_ascii=False
        )


def preparer_demo():

    if DEMO_DIR.exists():
        raise SystemExit(
            "Le dossier demo existe déjà. "
            "Aucune donnée existante n'a été écrasée."
        )

    for nom, configuration in SERVEURS.items():

        dossier = DEMO_DIR / nom

        dossier.mkdir(parents=True)

        # Copier l'application
        shutil.copy2(
            BASE_DIR / "app.py",
            dossier / "app.py"
        )

        shutil.copytree(
            BASE_DIR / "services",
            dossier / "services",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )

        shutil.copytree(
            BASE_DIR / "templates",
            dossier / "templates"
        )

        # Créer une base indépendante
        data_dir = dossier / "data"
        data_dir.mkdir()

        enregistrer_json(
            data_dir / "topics.json",
            configuration["topics"]
        )

        enregistrer_json(
            data_dir / "serveurs.json",
            configuration["annuaire"]
        )

        print(
            f"{nom} créé sur le port "
            f"{configuration['port']}"
        )

    print("\nSimulation préparée.")


if __name__ == "__main__":
    preparer_demo()