
import json
import ipaddress
import socket

from pathlib import Path
from urllib.parse import urlsplit

import requests


# Chemin de l'annuaire
BASE_DIR = Path(__file__).resolve().parent.parent
FICHIER_SERVEURS = BASE_DIR / "data" / "serveurs.json"


def analyser_adresse(adresse):
    """Vérifie une adresse et retourne son identité réseau."""

    if not isinstance(adresse, str):
        return None, "Format invalide"

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
            return None, "Format invalide"

        # Résolution DNS
        ip = socket.gethostbyname(url.hostname)
        adresse_ip = ipaddress.ip_address(ip)

        if (
            adresse_ip.is_loopback
            or adresse_ip.is_unspecified
            or adresse_ip.is_multicast
            or adresse_ip.is_link_local
        ):
            return None, "Adresse non utilisable à distance"

        identite = (ip, url.port)

        return identite, None

    except (ValueError, socket.gaierror, OSError):
        return None, "Adresse invalide ou DNS introuvable"


def verifier_serveur(adresse):
    """Teste l'API REST d'un serveur Pythonpédia."""

    try:
        reponse = requests.get(
            f"{adresse.rstrip('/')}/ws/topics",
            timeout=3
        )

        reponse.raise_for_status()
        topics = reponse.json()

        if not isinstance(topics, list):
            return False, "Réponse JSON incorrecte"

        return True, f"{len(topics)} topics"

    except (requests.RequestException, ValueError) as erreur:
        return False, str(erreur)


def main():

    with open(FICHIER_SERVEURS, "r", encoding="utf-8") as f:
        serveurs = json.load(f)

    identites_vues = set()

    accessibles = []
    inaccessibles = []
    invalides = []
    doublons = []

    print("\nVÉRIFICATION DES SERVEURS PYTHONPÉDIA\n")

    for serveur in serveurs:

        identite, erreur = analyser_adresse(serveur)

        if erreur:
            invalides.append(serveur)
            print(f"[INVALIDE] {serveur}")
            continue

        if identite in identites_vues:
            doublons.append(serveur)
            print(f"[DOUBLON] {serveur}")
            continue

        identites_vues.add(identite)

        ok, message = verifier_serveur(serveur)

        if ok:
            accessibles.append(serveur)
            print(f"[OK] {serveur} - {message}")

        else:
            inaccessibles.append(serveur)
            print(f"[ERREUR] {serveur} - {message}")

    print("\n------ BILAN ------")
    print("Adresses enregistrées :", len(serveurs))
    print("Serveurs accessibles :", len(accessibles))
    print("Serveurs inaccessibles :", len(inaccessibles))
    print("Adresses invalides :", len(invalides))
    print("Doublons détectés :", len(doublons))


if __name__ == "__main__":
    main()
