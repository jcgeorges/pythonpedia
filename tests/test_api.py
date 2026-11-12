import pytest

import app as application

"""
on a utiliser monkeypatch car nous ne voulons pas que les tests utilisent directement les fichiers :
data/topics.json
data/serveurs.json

Avec :
monkeypatch.setattr(
    application,
    "FICHIER_TOPICS",
    fichier_topics
)

nous remplaçons temporairement le chemin de la base réelle par celui d'une base de test. Lorsque le test se termine, pytest restaure automatiquement la valeur originale.
les données Pythonpédia ne seront donc pas modifiées par ces tests.
"""

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Créer un client Flask avec une base temporaire."""

    fichier_topics = tmp_path / "topics.json"
    fichier_serveurs = tmp_path / "serveurs.json"

    application.enregistrer_json(
        fichier_topics,
        {
            "fonctions": {
                "definition": [
                    "https://docs.python.org"
                ]
            },
            "POO": {
                "tutoriel": [
                    "https://docs.python.org/fr/3/tutorial/classes.html"
                ]
            }
        }
    )

    application.enregistrer_json(
        fichier_serveurs,
        [
            "http://192.168.1.10:5000"
        ]
    )

    # Remplacer les chemins réels pendant les tests
    monkeypatch.setattr(
        application,
        "FICHIER_TOPICS",
        fichier_topics
    )

    monkeypatch.setattr(
        application,
        "FICHIER_SERVEURS",
        fichier_serveurs
    )

    application.app.config["TESTING"] = True

    with application.app.test_client() as client:
        yield client


def test_topics(client):
    """Tester la liste des topics."""

    reponse = client.get("/ws/topics")

    assert reponse.status_code == 200

    donnees = reponse.get_json()

    assert "fonctions" in donnees
    assert "POO" in donnees
    assert len(donnees) == 2


def test_topic_existant(client):
    """Tester la consultation d'un topic."""

    reponse = client.get("/ws/topic/fonctions")

    assert reponse.status_code == 200

    donnees = reponse.get_json()

    assert "definition" in donnees
    assert len(donnees["definition"]) == 1


def test_topic_inexistant(client):
    """Vérifier la gestion d'un topic inconnu."""

    reponse = client.get("/ws/topic/java")

    assert reponse.status_code == 404

    donnees = reponse.get_json()

    assert donnees["erreur"] == "Topic introuvable"


def test_annuaire(client):
    """Tester la récupération des serveurs."""

    reponse = client.get("/ws/annuaire")

    assert reponse.status_code == 200

    donnees = reponse.get_json()

    assert isinstance(donnees, list)
    assert len(donnees) == 1


def test_documentation(client):
    """Vérifier que la documentation est disponible."""

    reponse = client.get("/")

    assert reponse.status_code == 200
    assert b"Pythonp" in reponse.data


def test_dashboard(client):
    """Vérifier que le tableau de bord fonctionne."""

    reponse = client.get("/dashboard")

    assert reponse.status_code == 200