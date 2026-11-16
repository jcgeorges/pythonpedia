"""Verrou interprocessus pour les fichiers JSON locaux (Linux/Ubuntu)."""

import fcntl
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FICHIER_VERROU = BASE_DIR / "data" / ".pythonpedia.lock"


@contextmanager
def verrou_base():
    """Protéger les blocs lecture-modification-écriture entre processus."""
    FICHIER_VERROU.parent.mkdir(parents=True, exist_ok=True)
    with open(FICHIER_VERROU, "a+", encoding="utf-8") as fichier:
        fcntl.flock(fichier.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fichier.fileno(), fcntl.LOCK_UN)