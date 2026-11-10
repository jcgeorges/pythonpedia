
# Pythonpédia

Pythonpédia est une encyclopédie distribuée consacrée au langage Python.

Le projet repose sur une API REST développée avec Flask. Les références sont organisées en topics, items et URL, puis échangées entre plusieurs serveurs.

## Technologies

- Python
- Flask
- Requests
- JSON
- HTML / CSS

## Fonctionnalités

- Consultation des topics et des références
- Annuaire des serveurs
- Synchronisation des données entre serveurs
- Détection des doublons
- Tableau de bord web
- Ajout de références
- Documentation de l'API

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Démarrage

```bash
python app.py
```

## API

- `GET /` : documentation
- `GET /ws/topics` : liste des topics
- `GET /ws/topic/<topic>` : références d'un topic
- `GET /ws/annuaire` : annuaire des serveurs
- `GET /dashboard` : tableau de bord

## Synchronisation

```bash
python services/synchronisation.py
```

La synchronisation récupère les références publiées par les serveurs connus et enrichit la base locale sans dupliquer les URL.
