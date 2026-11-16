import threading

from services.verrou import verrou_base


def test_acquisition_verrou():
    """Vérifier qu'un verrou peut être utilisé."""

    with verrou_base():
        resultat = True

    assert resultat


def test_liberation_verrou():
    """Vérifier que le verrou est libéré après utilisation."""

    with verrou_base():
        premiere_acquisition = True

    with verrou_base():
        deuxieme_acquisition = True

    assert premiere_acquisition
    assert deuxieme_acquisition