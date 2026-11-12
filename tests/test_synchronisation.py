from services.synchronisation import fusionner_topics


def test_ajout_nouveau_topic():
    """Vérifier l'importation d'un nouveau topic."""

    locaux = {}

    distants = {
        "definition": ["https://docs.python.org/fr/3/tutorial/classes.html"]
    }

    modifications = fusionner_topics(
        locaux,
        "POO",
        distants
    )

    assert "POO" in locaux
    assert locaux["POO"] == distants
    assert modifications == 1


def test_fusion_topic_existant():
    """Vérifier la fusion sans perte de données."""

    locaux = {
        "fonctions": {
            "tutoriel": ["https://exemple-a.fr"]
        }
    }

    distants = {
        "tutoriel": [
            "https://exemple-a.fr",
            "https://exemple-b.fr"
        ]
    }

    modifications = fusionner_topics(
        locaux,
        "fonctions",
        distants
    )

    assert modifications == 1

    assert locaux["fonctions"]["tutoriel"] == [
        "https://exemple-a.fr",
        "https://exemple-b.fr"
    ]


def test_synchronisation_sans_doublons():
    """Vérifier que la fusion répétée ne crée pas de doublons."""

    locaux = {
        "fonctions": {
            "definition": ["https://exemple-a.fr"]
        }
    }

    distants = {
        "definition": [
            "https://exemple-a.fr",
            "https://exemple-b.fr"
        ]
    }

    premier = fusionner_topics(
        locaux,
        "fonctions",
        distants
    )

    deuxieme = fusionner_topics(
        locaux,
        "fonctions",
        distants
    )

    assert premier == 1
    assert deuxieme == 0
    assert len(locaux["fonctions"]["definition"]) == 2


def test_format_distant_invalide():
    """Vérifier le traitement d'une réponse incorrecte."""

    locaux = {"fonctions": {}}

    modifications = fusionner_topics(
        locaux,
        "fonctions",
        ["donnees_incorrectes"]
    )

    assert modifications == 0
    assert locaux == {"fonctions": {}}


import json

import services.synchronisation as synchro


def test_synchronisation_complete(tmp_path, monkeypatch):
    """Tester la récupération des topics et de l'annuaire."""

    # Création d'une base temporaire
    fichier_topics = tmp_path / "topics.json"
    fichier_serveurs = tmp_path / "serveurs.json"

    fichier_topics.write_text(
        json.dumps({
            "fonctions": {
                "definition": ["https://exemple-a.fr"]
            }
        }),
        encoding="utf-8"
    )

    fichier_serveurs.write_text(
        json.dumps(["http://192.168.1.10:5000"]),
        encoding="utf-8"
    )

    # Remplacer les chemins réels
    monkeypatch.setattr(
        synchro,
        "FICHIER_TOPICS",
        fichier_topics
    )

    monkeypatch.setattr(
        synchro,
        "FICHIER_SERVEURS",
        fichier_serveurs
    )

    # Simuler les réponses HTTP
    def fausse_requete(url):

        if url.endswith("/ws/topics"):
            return ["fonctions", "POO"]

        if url.endswith("/ws/topic/fonctions"):
            return {
                "definition": [
                    "https://exemple-a.fr",
                    "https://exemple-b.fr"
                ]
            }

        if url.endswith("/ws/topic/POO"):
            return {
                "tutoriel": [
                    "https://exemple-c.fr"
                ]
            }

        if url.endswith("/ws/annuaire"):
            return [
                "http://192.168.1.10:5000",
                "http://192.168.1.11:5000"
            ]

        raise ValueError(f"URL inattendue : {url}")

    monkeypatch.setattr(
        synchro,
        "requete_json",
        fausse_requete
    )

    # Exécution de la synchronisation
    synchro.synchroniser()

    # Lecture des résultats
    topics = json.loads(
        fichier_topics.read_text(encoding="utf-8")
    )

    serveurs = json.loads(
        fichier_serveurs.read_text(encoding="utf-8")
    )

    # Vérification des données
    assert "POO" in topics

    assert topics["fonctions"]["definition"] == [
        "https://exemple-a.fr",
        "https://exemple-b.fr"
    ]

    assert topics["POO"]["tutoriel"] == [
        "https://exemple-c.fr"
    ]

    # Vérification de la découverte
    assert "http://192.168.1.11:5000" in serveurs


def test_synchronisation_serveur_inaccessible(
    tmp_path,
    monkeypatch
):
    """Vérifier qu'une erreur réseau n'interrompt pas la collecte."""

    import requests

    fichier_topics = tmp_path / "topics.json"
    fichier_serveurs = tmp_path / "serveurs.json"

    donnees_initiales = {
        "fonctions": {
            "definition": ["https://exemple-a.fr"]
        }
    }

    fichier_topics.write_text(
        json.dumps(donnees_initiales),
        encoding="utf-8"
    )

    fichier_serveurs.write_text(
        json.dumps(["http://192.168.1.10:5000"]),
        encoding="utf-8"
    )

    monkeypatch.setattr(
        synchro,
        "FICHIER_TOPICS",
        fichier_topics
    )

    monkeypatch.setattr(
        synchro,
        "FICHIER_SERVEURS",
        fichier_serveurs
    )

    def serveur_inaccessible(url):
        raise requests.exceptions.ConnectionError(
            "Serveur inaccessible"
        )

    monkeypatch.setattr(
        synchro,
        "requete_json",
        serveur_inaccessible
    )

    # Le programme doit terminer sans exception
    synchro.synchroniser()

    # La base doit rester intacte
    resultat = json.loads(
        fichier_topics.read_text(encoding="utf-8")
    )

    assert resultat == donnees_initiales