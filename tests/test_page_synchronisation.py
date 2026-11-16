import pytest

import app as application
import services.historique as historique


@pytest.fixture
def client_synchronisation(tmp_path, monkeypatch):
    """
    Créer un client Flask avec un historique temporaire.
    """

    fichier_historique = (
        tmp_path / "historique_synchronisations.json"
    )

    # Éviter de modifier l'historique réel
    monkeypatch.setattr(
        historique,
        "FICHIER_HISTORIQUE",
        fichier_historique
    )

    application.app.config["TESTING"] = True

    with application.app.test_client() as client:
        yield client, fichier_historique


def test_affichage_page_synchronisation(
    client_synchronisation
):
    """
    Vérifier que la page s'affiche correctement.
    """

    client, _ = client_synchronisation

    reponse = client.get(
        "/dashboard/synchronisation"
    )

    assert reponse.status_code == 200

    assert b"Synchronisation" in reponse.data


def test_synchronisation_sans_csrf(
    client_synchronisation
):
    """
    Vérifier qu'une synchronisation sans jeton
    CSRF est interdite.
    """

    client, fichier = client_synchronisation

    reponse = client.post(
        "/dashboard/synchronisation"
    )

    assert reponse.status_code == 403

    # Aucun historique ne doit être créé
    assert not fichier.exists()


def test_synchronisation_distante_interdite(
    client_synchronisation
):
    """
    Vérifier qu'une requête distante
    ne peut pas lancer la synchronisation.
    """

    client, fichier = client_synchronisation

    # Ouvrir la page pour créer une session
    client.get("/dashboard/synchronisation")

    with client.session_transaction() as session:
        jeton = session["csrf_synchronisation"]

    reponse = client.post(
        "/dashboard/synchronisation",
        data={
            "csrf_token": jeton
        },
        environ_overrides={
            "REMOTE_ADDR": "192.0.2.10"
        }
    )

    assert reponse.status_code == 403

    assert not fichier.exists()