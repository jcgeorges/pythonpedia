import json

from services.database import lire_json, enregistrer_json

"""
tmp_path est une fonctionnalité fournie par pytest.
Elle permet de créer automatiquement un dossier temporaire pour chaque test.
"""

def test_lire_json(tmp_path):
    """Vérifier la lecture d'un fichier JSON."""

    fichier = tmp_path / "topics.json"

    donnees = {
        "fonctions": {
            "definition": ["https://docs.python.org"]
        }
    }

    fichier.write_text(
        json.dumps(donnees),
        encoding="utf-8"
    )

    resultat = lire_json(fichier)

    assert resultat == donnees # assert vérifie que le résultat obtenu correspond au résultat attendu.


def test_enregistrer_json(tmp_path):
    """Vérifier l'enregistrement des données."""

    fichier = tmp_path / "topics.json"

    donnees = {
        "POO": {
            "tutoriel": ["https://docs.python.org"]
        }
    }

    enregistrer_json(fichier, donnees)

    assert fichier.exists()

    resultat = lire_json(fichier)

    assert resultat == donnees


def test_remplacer_donnees(tmp_path):
    """Vérifier qu'un fichier peut être mis à jour."""

    fichier = tmp_path / "topics.json"

    anciennes_donnees = {
        "fonctions": {}
    }

    nouvelles_donnees = {
        "fonctions": {},
        "exceptions": {}
    }

    enregistrer_json(fichier, anciennes_donnees)
    enregistrer_json(fichier, nouvelles_donnees)

    resultat = lire_json(fichier)

    assert resultat == nouvelles_donnees