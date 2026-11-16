"""Synchronisation des références et découverte des serveurs Pythonpédia."""

import ipaddress
import os
from copy import deepcopy
from urllib.parse import quote, urlsplit

import requests

from services.database import (
    FICHIER_SERVEURS,
    FICHIER_TOPICS,
    enregistrer_json,
    lire_json,
)
from services.verrou import verrou_base


def requete_json(url):
    """Récupérer une réponse JSON avec un délai maximal de cinq secondes."""
    reponse = requests.get(url, timeout=5, allow_redirects=False)
    reponse.raise_for_status()
    return reponse.json()


def fusionner_topics(topics_locaux, topic, items_distants):
    """Ajouter uniquement les URL manquantes, sans effacer les autres."""
    modifications = 0

    if not isinstance(items_distants, dict):
        return modifications

    if topic not in topics_locaux:
        topics_locaux[topic] = {}

    for item, urls in items_distants.items():
        if not isinstance(item, str) or not isinstance(urls, list):
            continue

        if item not in topics_locaux[topic]:
            topics_locaux[topic][item] = []

        for url in urls:
            if not isinstance(url, str):
                continue
            if url not in topics_locaux[topic][item]:
                topics_locaux[topic][item].append(url)
                modifications += 1

    return modifications


def adresse_valide(adresse):
    """Contrôler le format des adresses annoncées dans les annuaires."""
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

        try:
            ip = ipaddress.ip_address(url.hostname)
            mode_simulation = os.environ.get("PYTHONPEDIA_ALLOW_LOOPBACK") == "1"
            if ip.is_loopback and not mode_simulation:
                return False
            if (
                ip.is_unspecified
                or ip.is_multicast
                or ip.is_link_local
                or ip.is_reserved
            ):
                return False
        except ValueError:
            # On accepte les noms DNS (sans effectuer de résolution ici).
            pass

        return True
    except ValueError:
        return False


def synchroniser():
    """Télécharger hors verrou, puis fusionner sous verrou interprocessus.

    La découverte de nouveaux serveurs prend effet à l'exécution suivante.
    """
    with verrou_base():
        serveurs_a_contacter = list(lire_json(FICHIER_SERVEURS))

    for serveur in serveurs_a_contacter:
        if not adresse_valide(serveur):
            print("Adresse de serveur invalide :", serveur)
            continue

        serveur = serveur.rstrip("/")
        print(f"\nConnexion à {serveur}")

        # Téléchargements : aucun verrou n'est détenu pendant les appels réseau.
        topics_recus = []
        annuaire_recu = []

        try:
            topics_distants = requete_json(f"{serveur}/ws/topics")
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
                    topics_recus.append((topic, items))
                except (requests.RequestException, ValueError) as erreur:
                    print(f"  Erreur pour {topic} : {erreur}")
        except (requests.RequestException, ValueError) as erreur:
            print("Impossible de récupérer les topics :", erreur)

        try:
            annuaire = requete_json(f"{serveur}/ws/annuaire")
            if not isinstance(annuaire, list):
                raise ValueError("Annuaire invalide")
            annuaire_recu = [
                adresse.rstrip("/")
                for adresse in annuaire
                if adresse_valide(adresse)
            ]
        except (requests.RequestException, ValueError) as erreur:
            print("Impossible de récupérer l'annuaire :", erreur)

        # Lecture-Fusion-Écriture dans une seule section critique.
        # On RELIT les JSON ici pour conserver les modifications faites
        # depuis le tableau de bord pendant les requêtes HTTP.
        with verrou_base():
            topics_locaux = lire_json(FICHIER_TOPICS)
            serveurs = lire_json(FICHIER_SERVEURS)
            topics_modifies = False
            serveurs_modifies = False

            for topic, items in topics_recus:
                etat_precedent = deepcopy(topics_locaux.get(topic))
                nb = fusionner_topics(topics_locaux, topic, items)
                if topics_locaux.get(topic) != etat_precedent:
                    topics_modifies = True
                print(f"  {topic} : {nb} nouvelle(s) URL")

            for adresse in annuaire_recu:
                if adresse not in serveurs:
                    serveurs.append(adresse)
                    serveurs_modifies = True
                    print("  Nouveau serveur :", adresse)

            if topics_modifies:
                enregistrer_json(FICHIER_TOPICS, topics_locaux)
            if serveurs_modifies:
                enregistrer_json(FICHIER_SERVEURS, serveurs)

    print("\nSynchronisation terminée.")


if __name__ == "__main__":
    synchroniser()