from datetime import datetime
from pathlib import Path

from services.database import (
    lire_json,
    enregistrer_json
)


BASE_DIR = Path(__file__).resolve().parent.parent

FICHIER_HISTORIQUE = (
    BASE_DIR / "data" / "historique_synchronisations.json"
)

MAX_HISTORIQUE = 30


def charger_historique():
    """
    Charger les dernières synchronisations.
    """

    if not FICHIER_HISTORIQUE.exists():
        return []

    historique = lire_json(FICHIER_HISTORIQUE)

    if not isinstance(historique, list):
        raise ValueError(
            "Le fichier d'historique doit contenir une liste."
        )

    return historique


def ajouter_historique(
    succes,
    nouvelles_urls=None,
    nouveaux_serveurs=None,
    message=""
):
    """
    Enregistrer une synchronisation dans l'historique.
    """

    historique = charger_historique()

    entree = {
        "date": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "succes": succes,
        "nouvelles_urls": nouvelles_urls,
        "nouveaux_serveurs": nouveaux_serveurs,
        "message": message[:10000]
    }

    # Ajouter la nouvelle exécution en première position
    historique.insert(0, entree)

    # Conserver les 30 dernières
    historique = historique[:MAX_HISTORIQUE]

    enregistrer_json(
        FICHIER_HISTORIQUE,
        historique
    )

    return entree