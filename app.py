"""Application Flask Pythonpédia : API, tableau de bord et gestion locale."""

import hmac
import os
import secrets
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

import requests
from flask import (
    Flask, abort, flash, jsonify, redirect, render_template,
    request, session, url_for,
)

from services.database import (
    FICHIER_SERVEURS, FICHIER_TOPICS, enregistrer_json, lire_json,
)
from services.historique import ajouter_historique, charger_historique
from services.verrou import verrou_base

# ------------------------------------------
# CONFIGURATION
# ------------------------------------------
verrou_synchronisation = threading.Lock()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

BASE_DIR = Path(__file__).resolve().parent


dernier_rapport = None


# ------------------------------------------
# FONCTIONS UTILITAIRES
# ------------------------------------------

def gestion_locale():
    """Autoriser les modifications uniquement en local."""
    return request.remote_addr in ("127.0.0.1", "::1")


@app.context_processor
def fournir_variables():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    return {
        "csrf_token": session["csrf_token"],
        "gestion_locale": gestion_locale()
    }


def verifier_modification():
    """Vérifier l'origine et le jeton CSRF."""
    if not gestion_locale():
        abort(403)

    token = request.form.get("csrf_token", "")

    if not secrets.compare_digest(
        token,
        session.get("csrf_token", "")
    ):
        abort(403)




def gestion_serveurs_locale():
    """
    Autoriser la gestion uniquement depuis la machine locale.
    """
    return request.remote_addr in ("127.0.0.1", "::1")


def obtenir_csrf_serveurs():
    """
    Créer un jeton CSRF propre à la gestion des serveurs.
    """
    if "csrf_serveurs" not in session:
        session["csrf_serveurs"] = secrets.token_hex(32)

    return session["csrf_serveurs"]


def proteger_gestion_serveurs():
    """
    Vérifier l'origine locale et le jeton CSRF.
    """
    if not gestion_serveurs_locale():
        abort(403)

    jeton_attendu = session.get("csrf_serveurs")
    jeton_recu = request.form.get("csrf_token", "")

    if (
        not jeton_attendu
        or not hmac.compare_digest(
            jeton_attendu,
            jeton_recu
        )
    ):
        abort(403)


def normaliser_adresse_serveur(adresse):
    """
    Vérifier et normaliser l'adresse d'un serveur HTTP.
    """
    adresse = adresse.strip().rstrip("/")

    if not adresse:
        raise ValueError("L'adresse est vide.")

    try:
        parsed = urlsplit(adresse)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                "L'adresse doit commencer par http:// ou https://."
            )

        if not parsed.hostname:
            raise ValueError("Nom d'hôte invalide.")

        if parsed.username or parsed.password:
            raise ValueError(
                "Les identifiants dans l'URL ne sont pas autorisés."
            )

        if parsed.path or parsed.query or parsed.fragment:
            raise ValueError(
                "Indique uniquement l'adresse du serveur, sans chemin."
            )

        # Vérifie également que le port éventuel est valide.
        port = parsed.port

        if port is not None and port <= 0:
            raise ValueError("Port invalide.")

    except ValueError as erreur:
        raise ValueError(
            f"Adresse invalide : {erreur}"
        ) from erreur

    return adresse



# ==================================================
# FONCTIONS DE COMPTAGE
# ==================================================

def ensemble_references(topics):
    """
    Construire l'ensemble des références distinctes.
    """

    references = set()

    for topic, items in topics.items():
        for item, urls in items.items():
            for url in urls:
                references.add((topic, item, url))

    return references


def etat_base():
    """
    Récupérer un instantané des références
    et des serveurs enregistrés.
    """

    with verrou_base():
        topics = lire_json(FICHIER_TOPICS)
        serveurs = lire_json(FICHIER_SERVEURS)

    return (ensemble_references(topics), set(serveurs))



# ------------------------------------------
# DOCUMENTATION PUBLIQUE
# ------------------------------------------

@app.route("/", methods=["GET"])
def accueil():
    return render_template("index.html")


# ------------------------------------------
# API REST PUBLIQUE
# ------------------------------------------

@app.route("/ws/topics", methods=["GET"])
def get_topics():
    topics = lire_json(FICHIER_TOPICS)
    return jsonify(list(topics.keys()))


@app.route("/ws/topic/<topic>", methods=["GET"])
def get_topic(topic):
    topics = lire_json(FICHIER_TOPICS)

    if topic not in topics:
        return jsonify({
            "erreur": "Topic introuvable"
        }), 404

    return jsonify(topics[topic])


@app.route("/ws/annuaire", methods=["GET"])
def get_annuaire():
    serveurs = lire_json(FICHIER_SERVEURS)
    return jsonify(serveurs)


# ------------------------------------------
# TABLEAU DE BORD
# ------------------------------------------

@app.route("/dashboard", methods=["GET"])
def tableau_de_bord():

    topics = lire_json(FICHIER_TOPICS)
    serveurs = lire_json(FICHIER_SERVEURS)

    nombre_topics = len(topics)

    nombre_items = sum(
        len(items) for items in topics.values()
    )

    urls_uniques = set()
    statistiques_topics = []

    for nom, items in topics.items():

        urls_topic = set()

        for urls in items.values():
            urls_topic.update(urls)
            urls_uniques.update(urls)

        statistiques_topics.append({
            "nom": nom,
            "items": len(items),
            "urls": len(urls_topic)
        })

    statistiques_topics.sort(
        key=lambda x: x["urls"],
        reverse=True
    )

    statistiques = {
        "topics": nombre_topics,
        "nombre_items": nombre_items,
        "urls": len(urls_uniques),
        "serveurs": len(serveurs)
    }

    recherche = request.args.get(
        "q", ""
    ).strip().lower()

    if recherche:
        topics_affiches = {
            nom: items
            for nom, items in topics.items()
            if recherche in nom.lower()
        }
    else:
        topics_affiches = topics

    return render_template(
        "dashboard.html",
        statistiques=statistiques,
        topics=topics_affiches,
        serveurs=serveurs,
        statistiques_topics=statistiques_topics,
        recherche=recherche,
        rapport_synchro=dernier_rapport
    )


# ------------------------------------------
# AJOUT D'UNE RÉFÉRENCE
# ------------------------------------------

@app.route("/ajouter", methods=["POST"])
def ajouter_reference():

    verifier_modification()

    topic = request.form.get("topic", "").strip()
    item = request.form.get("item", "").strip()
    url = request.form.get("url", "").strip()

    try:
        adresse = urlsplit(url)

        url_valide = (
            adresse.scheme in ("http", "https")
            and adresse.hostname is not None
            and adresse.username is None
            and adresse.password is None
        )

    except ValueError:
        url_valide = False

    if (
        not topic
        or not item
        or len(topic) > 100
        or len(item) > 100
        or not url_valide
    ):
        flash("Informations invalides.")
        return redirect(url_for("page_references"))

    with verrou_base():
        topics = lire_json(FICHIER_TOPICS)

        if topic not in topics:
            topics[topic] = {}

        if item not in topics[topic]:
            topics[topic][item] = []

        if url in topics[topic][item]:
            flash("Cette URL existe déjà dans cet item.")
        else:
            topics[topic][item].append(url)
            enregistrer_json(FICHIER_TOPICS, topics)
            flash("Référence ajoutée avec succès.")

    return redirect(url_for("page_references"))


# ------------------------------------------
# SYNCHRONISATION
# ------------------------------------------

def executer_synchronisation():
    """Exécuter le script sans bloquer la base pendant les requêtes HTTP.

    Cette fonction prend le verrou de synchronisation du processus Flask.
    Le script enfant utilise verrou_base() uniquement lors de la fusion locale.
    """
    global dernier_rapport

    if not verrou_synchronisation.acquire(blocking=False):
        return False

    try:
        succes = False
        nouvelles_urls = None
        nouveaux_serveurs = None
        message = ""

        try:
            references_avant, serveurs_avant = etat_base()
            resultat = subprocess.run(
                [sys.executable, "-m", "services.synchronisation"],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                check=False,
            )
            message = ((resultat.stdout or "") + "\n" + (resultat.stderr or "")).strip()
            succes = resultat.returncode == 0

            references_apres, serveurs_apres = etat_base()
            nouvelles_urls = len(references_apres - references_avant)
            nouveaux_serveurs = len(serveurs_apres - serveurs_avant)
            if not message:
                message = "Synchronisation terminée sans message supplémentaire."

        except subprocess.TimeoutExpired:
            message = "La synchronisation a dépassé le délai de 90 secondes."
        except (OSError, ValueError) as erreur:
            message = f"Erreur pendant la synchronisation : {erreur}"

        # Le fichier d'historique est partagé par les processus Flask.
        with verrou_base():
            rapport = ajouter_historique(
                succes=succes,
                nouvelles_urls=nouvelles_urls,
                nouveaux_serveurs=nouveaux_serveurs,
                message=message,
            )

        dernier_rapport = rapport
        return True
    finally:
        verrou_synchronisation.release()


@app.route("/synchroniser", methods=["POST"])
def lancer_synchronisation():
    """Ancienne route conservée pour compatibilité avec le tableau de bord."""
    verifier_modification()
    if not executer_synchronisation():
        flash("Une synchronisation est déjà en cours.")
    else:
        flash("Synchronisation terminée. Consulte l'historique.")
    return redirect(url_for("page_synchronisation"))


@app.route("/dashboard/references", methods=["GET"])
def page_references():

    # Charger les références
    topics = lire_json(FICHIER_TOPICS)

    # Récupérer la recherche
    recherche = request.args.get("q", "").strip().lower()

    references = []

    # Parcourir les topics et les items
    for topic, items in topics.items():

        for item, urls in items.items():

            for url in urls:

                # Vérifier si la référence correspond à la recherche
                if (
                    recherche in topic.lower()
                    or recherche in item.lower()
                    or recherche in url.lower()
                ):

                    references.append({
                        "topic": topic,
                        "item": item,
                        "url": url
                    })

    # Trier les références
    references.sort(
        key=lambda x: (
            x["topic"].lower(),
            x["item"].lower(),
            x["url"]
        )
    )

    return render_template(
        "references.html",
        references=references,
        topics=topics,
        recherche=recherche,
        nombre_references=len(references)
    )


@app.route("/dashboard/serveurs", methods=["GET"])
def page_serveurs():

    # Charger l'annuaire
    serveurs = lire_json(FICHIER_SERVEURS)

    # Récupérer les résultats des dernières vérifications
    statuts = session.get("statuts_serveurs", {})

    liste_serveurs = []

    for adresse in serveurs:

        statut = statuts.get(adresse, "non_verifie")

        liste_serveurs.append({
            "adresse": adresse,
            "statut": statut
        })

    # Statistiques
    nombre_serveurs = len(liste_serveurs)

    nombre_accessibles = sum(
        serveur["statut"] == "accessible"
        for serveur in liste_serveurs
    )

    nombre_inaccessibles = sum(
        serveur["statut"] == "inaccessible"
        for serveur in liste_serveurs
    )

    nombre_non_verifies = sum(
        serveur["statut"] == "non_verifie"
        for serveur in liste_serveurs
    )

    return render_template(
        "serveurs.html",
        serveurs=liste_serveurs,
        nombre_serveurs=nombre_serveurs,
        nombre_accessibles=nombre_accessibles,
        nombre_inaccessibles=nombre_inaccessibles,
        nombre_non_verifies=nombre_non_verifies,
        gestion_locale=gestion_serveurs_locale(),
        csrf_token_serveurs=(
            obtenir_csrf_serveurs()
            if gestion_serveurs_locale()
            else None
        )
    )


@app.route(
    "/dashboard/synchronisation",
    methods=["GET", "POST"]
)
def page_synchronisation():

    # =====================================
    # PROTECTION DE L'INTERFACE
    # =====================================

    gestion_locale = request.remote_addr in (
        "127.0.0.1",
        "::1"
    )

    # Créer un jeton CSRF pour cette page
    if gestion_locale and "csrf_synchronisation" not in session:

        session["csrf_synchronisation"] = (
            secrets.token_hex(32)
        )

    # =====================================
    # LANCEMENT DE LA SYNCHRONISATION
    # =====================================

    if request.method == "POST":

        # Interdire les modifications distantes
        if not gestion_locale:
            abort(403)

        # Vérifier le jeton CSRF
        jeton_attendu = session.get(
            "csrf_synchronisation"
        )

        jeton_recu = request.form.get(
            "csrf_token",
            ""
        )

        if (
            not jeton_attendu
            or not hmac.compare_digest(
                jeton_attendu,
                jeton_recu
            )
        ):
            abort(403)

        if not executer_synchronisation():
            flash("Une synchronisation est déjà en cours.")
        else:
            flash("Synchronisation terminée. Consulte le dernier rapport.")

        return redirect(url_for("page_synchronisation"))

    # =====================================
    # AFFICHAGE DE LA PAGE
    # =====================================

    historique = charger_historique()

    derniere = (
        historique[0]
        if historique
        else None
    )

    return render_template(
        "synchronisation.html",
        historique=historique,
        derniere=derniere,
        nombre_synchronisations=len(historique),
        gestion_locale=gestion_locale,
        csrf_token_synchronisation=(
            session.get("csrf_synchronisation")
            if gestion_locale
            else None
        )
    )


@app.route("/supprimer-reference", methods=["POST"])
def supprimer_reference():

    # Vérifier que l'utilisateur peut modifier les données
    verifier_modification()

    # Récupérer les informations
    topic = request.form.get("topic", "")
    item = request.form.get("item", "")
    url = request.form.get("url", "")

    with verrou_base():
        topics = lire_json(FICHIER_TOPICS)

        if (
            topic in topics
            and item in topics[topic]
            and url in topics[topic][item]
        ):
            topics[topic][item].remove(url)
            enregistrer_json(FICHIER_TOPICS, topics)
            flash("Référence supprimée avec succès.")
        else:
            flash("Référence introuvable.")

    return redirect(url_for("page_references"))




@app.route("/dashboard/serveurs/action", methods=["POST"])
def action_serveurs():

    # Vérifier les autorisations
    proteger_gestion_serveurs()

    action = request.form.get("action", "")

    # =========================================
    # AJOUTER UN SERVEUR
    # =========================================

    if action == "ajouter":

        try:
            adresse = normaliser_adresse_serveur(
                request.form.get("adresse", "")
            )

        except ValueError as erreur:
            flash(str(erreur))

            return redirect(
                url_for("page_serveurs")
            )

        with verrou_base():

            serveurs = lire_json(FICHIER_SERVEURS)

            if adresse in serveurs:
                flash("Ce serveur existe déjà.")

            else:
                serveurs.append(adresse)

                enregistrer_json(
                    FICHIER_SERVEURS,
                    serveurs
                )

                flash("Serveur ajouté avec succès.")

    # =========================================
    # SUPPRIMER UN SERVEUR
    # =========================================

    elif action == "supprimer":

        adresse = request.form.get("adresse", "")

        with verrou_base():

            serveurs = lire_json(FICHIER_SERVEURS)

            if adresse in serveurs:

                serveurs.remove(adresse)

                enregistrer_json(
                    FICHIER_SERVEURS,
                    serveurs
                )

                # Supprimer l'ancien statut
                statuts = session.get(
                    "statuts_serveurs",
                    {}
                )

                statuts.pop(adresse, None)

                session["statuts_serveurs"] = statuts

                flash("Serveur supprimé avec succès.")

            else:
                flash("Serveur introuvable.")

    # =========================================
    # VÉRIFIER LES SERVEURS
    # =========================================

    elif action == "verifier":

        serveurs = lire_json(FICHIER_SERVEURS)

        statuts = {}

        for adresse in serveurs:

            try:

                reponse = requests.get(
                    f"{adresse}/ws/topics",
                    timeout=2,
                    allow_redirects=False
                )

                if (
                    reponse.status_code == 200
                    and isinstance(reponse.json(), list)
                ):

                    statuts[adresse] = "accessible"

                else:
                    statuts[adresse] = "inaccessible"

            except (
                requests.exceptions.RequestException,
                ValueError
            ):

                statuts[adresse] = "inaccessible"

        session["statuts_serveurs"] = statuts

        accessibles = sum(
            statut == "accessible"
            for statut in statuts.values()
        )

        flash(
            f"Vérification terminée : "
            f"{accessibles}/{len(serveurs)} "
            f"serveurs accessibles."
        )

    else:
        abort(400)

    return redirect(
        url_for("page_serveurs")
    )

# ------------------------------------------
# DÉMARRAGE UNIQUE
# ------------------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PYTHONPEDIA_PORT", 5000))

    app.run(
        host="127.0.0.1",
        port=port,
        debug=False
    )