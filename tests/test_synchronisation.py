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