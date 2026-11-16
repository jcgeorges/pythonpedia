import pytest

import app as application


@pytest.fixture
def client_serveurs(tmp_path, monkeypatch):
    """
    Créer un client Flask utilisant un annuaire temporaire.
    """

    fichier_serveurs = tmp_path / "serveurs.json"

    application.enregistrer_json(
        fichier_serveurs,
        [
            "http://127.0.0.1:5001"
        ]
    )

    # Utiliser l'annuaire temporaire
    monkeypatch.setattr(
        application,
        "FICHIER_SERVEURS",
        fichier_serveurs
    )

    application.app.config["TESTING"] = True

    with application.app.test_client() as client:
        yield client, fichier_serveurs


def obtenir_jeton(client):
    """
    Récupérer le jeton CSRF après ouverture de la page.
    """

    reponse = client.get("/dashboard/serveurs")

    assert reponse.status_code == 200

    with client.session_transaction() as session:
        return session["csrf_serveurs"]


def test_affichage_serveurs(client_serveurs):
    """
    Vérifier l'affichage de l'annuaire.
    """

    client, _ = client_serveurs

    reponse = client.get("/dashboard/serveurs")

    assert reponse.status_code == 200

    assert b"127.0.0.1:5001" in reponse.data


def test_ajouter_serveur(client_serveurs):
    """
    Vérifier l'ajout d'un serveur.
    """

    client, fichier = client_serveurs

    jeton = obtenir_jeton(client)

    reponse = client.post(
        "/dashboard/serveurs/action",
        data={
            "csrf_token": jeton,
            "action": "ajouter",
            "adresse": "http://127.0.0.1:5002"
        }
    )

    assert reponse.status_code == 302

    serveurs = application.lire_json(fichier)

    assert "http://127.0.0.1:5002" in serveurs


def test_ajouter_doublon(client_serveurs):
    """
    Vérifier qu'une adresse existante
    n'est pas ajoutée deux fois.
    """

    client, fichier = client_serveurs

    jeton = obtenir_jeton(client)

    client.post(
        "/dashboard/serveurs/action",
        data={
            "csrf_token": jeton,
            "action": "ajouter",
            "adresse": "http://127.0.0.1:5001"
        }
    )

    serveurs = application.lire_json(fichier)

    assert serveurs.count(
        "http://127.0.0.1:5001"
    ) == 1


def test_supprimer_serveur(client_serveurs):
    """
    Vérifier la suppression d'un serveur.
    """

    client, fichier = client_serveurs

    jeton = obtenir_jeton(client)

    reponse = client.post(
        "/dashboard/serveurs/action",
        data={
            "csrf_token": jeton,
            "action": "supprimer",
            "adresse": "http://127.0.0.1:5001"
        }
    )

    assert reponse.status_code == 302

    serveurs = application.lire_json(fichier)

    assert "http://127.0.0.1:5001" not in serveurs


def test_modification_sans_csrf(client_serveurs):
    """
    Vérifier qu'une modification sans jeton
    CSRF est interdite.
    """

    client, fichier = client_serveurs

    reponse = client.post(
        "/dashboard/serveurs/action",
        data={
            "action": "supprimer",
            "adresse": "http://127.0.0.1:5001"
        }
    )

    assert reponse.status_code == 403

    serveurs = application.lire_json(fichier)

    assert "http://127.0.0.1:5001" in serveurs


def test_modification_distante_interdite(client_serveurs):
    """
    Vérifier qu'une requête distante
    ne peut pas modifier l'annuaire.
    """

    client, fichier = client_serveurs

    jeton = obtenir_jeton(client)

    reponse = client.post(
        "/dashboard/serveurs/action",
        data={
            "csrf_token": jeton,
            "action": "supprimer",
            "adresse": "http://127.0.0.1:5001"
        },
        environ_overrides={
            "REMOTE_ADDR": "192.0.2.10"
        }
    )

    assert reponse.status_code == 403

    serveurs = application.lire_json(fichier)

    assert "http://127.0.0.1:5001" in serveurs