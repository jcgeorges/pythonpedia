import multiprocessing
import time

from services.database import (
    lire_json,
    enregistrer_json
)

import services.verrou as module_verrou


def ajouter_references(
    fichier_topics,
    fichier_verrou,
    prefixe,
    depart,
    nombre=20
):
    """
    Ajouter plusieurs références depuis un processus indépendant.
    """

    # Les deux processus doivent utiliser le même verrou.
    module_verrou.FICHIER_VERROU = fichier_verrou

    # Attendre le signal de départ.
    depart.wait(timeout=10)

    for i in range(nombre):

        with module_verrou.verrou_base():

            # Lire les données les plus récentes.
            topics = lire_json(fichier_topics)

            # Initialiser le topic et l'item.
            topics.setdefault("concurrence", {})
            topics["concurrence"].setdefault("tests", [])

            # Ajouter une référence propre à ce processus.
            url = f"https://exemple.fr/{prefixe}/{i}"

            topics["concurrence"]["tests"].append(url)

            # Accentuer les possibilités d'entrelacement.
            time.sleep(0.002)

            # Enregistrer les nouvelles données.
            enregistrer_json(
                fichier_topics,
                topics
            )


def test_ecritures_simultanees(tmp_path):
    """
    Vérifier que deux processus ne perdent aucune référence.
    """

    fichier_topics = tmp_path / "topics.json"
    fichier_verrou = tmp_path / ".pythonpedia.lock"

    # Base temporaire initialement vide.
    enregistrer_json(fichier_topics, {})

    # Utilisation de fork, disponible sous Ubuntu/Linux.
    contexte = multiprocessing.get_context("fork")

    depart = contexte.Event()

    processus_a = contexte.Process(
        target=ajouter_references,
        args=(
            fichier_topics,
            fichier_verrou,
            "processus_a",
            depart
        )
    )

    processus_b = contexte.Process(
        target=ajouter_references,
        args=(
            fichier_topics,
            fichier_verrou,
            "processus_b",
            depart
        )
    )

    processus_a.start()
    processus_b.start()

    # Démarrer les deux processus.
    depart.set()

    processus_a.join(timeout=15)
    processus_b.join(timeout=15)

    # Arrêter les processus en cas de blocage.
    for processus in (processus_a, processus_b):
        if processus.is_alive():
            processus.terminate()
            processus.join(timeout=5)

    assert processus_a.exitcode == 0
    assert processus_b.exitcode == 0

    # Vérifier les données finales.
    topics = lire_json(fichier_topics)

    references = topics["concurrence"]["tests"]

    assert len(references) == 40

    # Vérifier l'absence de doublons.
    assert len(set(references)) == 40

    # Vérifier que chaque processus a bien ajouté ses URL.
    for i in range(20):

        assert (
            f"https://exemple.fr/processus_a/{i}"
            in references
        )

        assert (
            f"https://exemple.fr/processus_b/{i}"
            in references
        )