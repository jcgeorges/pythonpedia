
import json
import ipaddress
from pathlib import Path
from urllib.parse import quote, urlsplit
from services.database import (
    lire_json,
    enregistrer_json,
    FICHIER_TOPICS,
    FICHIER_SERVEURS
)

import requests


# Chemins vers les fichiers de données
BASE_DIR = Path(__file__).resolve().parent.parent
# FICHIER_TOPICS = BASE_DIR / "data" / "topics.json"
# FICHIER_SERVEURS = BASE_DIR / "data" / "serveurs.json"


def requete_json(url):
    """Interroger une API et récupérer sa réponse JSON."""
    reponse = requests.get(url, timeout=5)
    reponse.raise_for_status()
    return reponse.json()


def fusionner_topics(topics_locaux, topic, items_distants):
    """Ajouter les URL absentes sans supprimer les anciennes."""

    modifications = 0

    if not isinstance(items_distants, dict):
        return modifications

    # Créer le topic s'il n'existe pas
    if topic not in topics_locaux:
        topics_locaux[topic] = {}

    # Parcourir les items du serveur distant
    for item, urls in items_distants.items():

        if not isinstance(item, str) or not isinstance(urls, list):
            continue

        # Créer l'item s'il n'existe pas
        if item not in topics_locaux[topic]:
            topics_locaux[topic][item] = []

        # Ajouter uniquement les nouvelles URL
        for url in urls:

            if not isinstance(url, str):
                continue

            if url not in topics_locaux[topic][item]:
                topics_locaux[topic][item].append(url)
                modifications += 1

    return modifications



def adresse_valide(adresse):
    """Vérifie qu'une adresse peut désigner un serveur distant."""

    if not isinstance(adresse, str):
        return False

    try:
        url = urlsplit(adresse)

        if (
            url.scheme != "http"
            or url.hostname is None
            or url.port is None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or url.username is not None
            or url.password is not None
        ):
            return False

        # Vérification des adresses IP littérales
        try:
            ip = ipaddress.ip_address(url.hostname)

            if (
                ip.is_loopback
                or ip.is_unspecified
                or ip.is_multicast
                or ip.is_link_local
            ):
                return False

        except ValueError:
            # Les noms DNS sont acceptés
            pass

        return True

    except ValueError:
        return False


def synchroniser():
    """Synchroniser les références et l'annuaire local."""

    topics_locaux = lire_json(FICHIER_TOPICS)
    serveurs = lire_json(FICHIER_SERVEURS)

    # Copie de la liste initiale pour cette exécution
    serveurs_a_contacter = list(serveurs)

    for serveur in serveurs_a_contacter:

        if not adresse_valide(serveur):
            print("Adresse de serveur invalide :", serveur)
            continue

        serveur = serveur.rstrip("/")
        print(f"\nConnexion à {serveur}")

        # 1. Récupération des topics
        try:
            topics_distants = requete_json(
                f"{serveur}/ws/topics"
            )

            if not isinstance(topics_distants, list):
                raise ValueError("Liste de topics invalide")

            for topic in topics_distants:

                if not isinstance(topic, str):
                    continue

                try:
                    items = requete_json(
                        f"{serveur}/ws/topic/{quote(topic, safe='')}"
                    )

                    if not isinstance(items, dict):
                        raise ValueError("Format du topic invalide")

                    nb = fusionner_topics(
                        topics_locaux, topic, items
                    )

                    print(f"  {topic} : {nb} nouvelle(s) URL")

                except (requests.RequestException, ValueError) as e:
                    print(f"  Erreur pour {topic} : {e}")

        except (requests.RequestException, ValueError) as e:
            print("Impossible de récupérer les topics :", e)

        # 2. Récupération de l'annuaire
        try:
            annuaire = requete_json(
                f"{serveur}/ws/annuaire"
            )

            if not isinstance(annuaire, list):
                raise ValueError("Annuaire invalide")

            for adresse in annuaire:

                if not adresse_valide(adresse):
                    continue

                adresse = adresse.rstrip("/")

                if adresse not in serveurs:
                    serveurs.append(adresse)
                    print("  Nouveau serveur :", adresse)

        except (requests.RequestException, ValueError) as e:
            print("Impossible de récupérer l'annuaire :", e)

        # Sauvegarde après chaque serveur
        enregistrer_json(FICHIER_TOPICS, topics_locaux)
        enregistrer_json(FICHIER_SERVEURS, serveurs)

    print("\nSynchronisation terminée.")


if __name__ == "__main__":
    synchroniser()
