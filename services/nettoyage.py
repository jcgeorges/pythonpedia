
import json
import ipaddress
import socket
import shutil

from pathlib import Path
from urllib.parse import urlsplit


BASE_DIR = Path(__file__).resolve().parent.parent

FICHIER_SERVEURS = BASE_DIR / "data" / "serveurs.json"
FICHIER_BACKUP = BASE_DIR / "data" / "serveurs_backup_nettoyage.json"


def identifier_serveur(adresse):
    """Retourner une identité réseau ou None."""

    if not isinstance(adresse, str):
        return None

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
            return None

        ip = socket.gethostbyname(url.hostname)
        objet_ip = ipaddress.ip_address(ip)

        if (
            objet_ip.is_loopback
            or objet_ip.is_unspecified
            or objet_ip.is_multicast
            or objet_ip.is_link_local
        ):
            return None

        return (ip, url.port)

    except (ValueError, OSError):
        return None


def nettoyer_annuaire():

    with open(FICHIER_SERVEURS, "r", encoding="utf-8") as f:
        serveurs = json.load(f)

    serveurs_valides = []
    identites = set()
    supprimes = []

    for adresse in serveurs:

        identite = identifier_serveur(adresse)

        if identite is None:
            supprimes.append((adresse, "Adresse invalide"))
            continue

        if identite in identites:
            supprimes.append((adresse, "Doublon"))
            continue

        identites.add(identite)
        serveurs_valides.append(adresse)

    print("\nADRESSES À RETIRER\n")

    for adresse, raison in supprimes:
        print(f"{adresse} -> {raison}")

    print("\nBILAN")
    print("Avant :", len(serveurs))
    print("Après :", len(serveurs_valides))
    print("Retirées :", len(supprimes))

    confirmation = input("\nConfirmer le nettoyage ? (o/n) : ")

    if confirmation.lower() != "o":
        print("Nettoyage annulé.")
        return

    # Sauvegarde de l'annuaire original
    shutil.copy2(FICHIER_SERVEURS, FICHIER_BACKUP)

    # Enregistrement des adresses conservées
    with open(FICHIER_SERVEURS, "w", encoding="utf-8") as f:
        json.dump(
            serveurs_valides,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("\nAnnuaire nettoyé avec succès.")
    print("Sauvegarde :", FICHIER_BACKUP)


if __name__ == "__main__":
    nettoyer_annuaire()
