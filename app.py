
import json
import secrets
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from services.database import (
    lire_json,
    enregistrer_json,
    FICHIER_TOPICS,
    FICHIER_SERVEURS
)

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort
)

# ------------------------------------------
# CONFIGURATION
# ------------------------------------------

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

BASE_DIR = Path(__file__).resolve().parent

# FICHIER_TOPICS = BASE_DIR / "data" / "topics.json"
# FICHIER_SERVEURS = BASE_DIR / "data" / "serveurs.json"
SCRIPT_SYNCHRO = BASE_DIR / "services" / "synchronisation.py"

verrou_donnees = threading.Lock()
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
        return redirect(url_for("tableau_de_bord"))

    if not verrou_donnees.acquire(blocking=False):
        flash("Une opération est déjà en cours.")
        return redirect(url_for("tableau_de_bord"))

    try:
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

    finally:
        verrou_donnees.release()

    return redirect(url_for("tableau_de_bord"))


# ------------------------------------------
# SYNCHRONISATION
# ------------------------------------------

@app.route("/synchroniser", methods=["POST"])
def lancer_synchronisation():

    global dernier_rapport

    verifier_modification()

    if not verrou_donnees.acquire(blocking=False):
        flash("Une opération est déjà en cours.")
        return redirect(url_for("tableau_de_bord"))

    try:
        resultat = subprocess.run(
            [sys.executable, "-m", "services.synchronisation"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=360
        )

        sortie = resultat.stdout

        if resultat.stderr:
            sortie += "\n" + resultat.stderr

        dernier_rapport = {
            "date": datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
            "succes": resultat.returncode == 0,
            "message": sortie[-12000:]
        }

        if resultat.returncode == 0:
            flash("Synchronisation exécutée.")
        else:
            flash("Erreur pendant la synchronisation.")

    except subprocess.TimeoutExpired:
        dernier_rapport = {
            "date": datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
            "succes": False,
            "message": "Délai de synchronisation dépassé."
        }

        flash("La synchronisation a dépassé le délai.")

    except OSError as erreur:
        dernier_rapport = {
            "date": datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            ),
            "succes": False,
            "message": str(erreur)
        }

        flash("Impossible de lancer la synchronisation.")

    finally:
        verrou_donnees.release()

    return redirect(url_for("tableau_de_bord"))


# ------------------------------------------
# DÉMARRAGE UNIQUE
# ------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
