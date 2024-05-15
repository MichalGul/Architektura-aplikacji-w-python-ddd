#pylint: disable=bare-except
import time
import pytest

def wait_for(fn):
    """
    Wykonujemy funkcję, przechwytując wyjątki, aż zwróci coś prawdziwego
    lub osiągamy limit czasu.
    """
    timeout = time.time() + 3
    while time.time() < timeout:
        try:
            r = fn()
            if r:
                return r
        except:
            if time.time() > timeout:
                raise
        time.sleep(0.1)
    pytest.fail(f'Funkcja {fn} nie zwróciła nic prawdziwego.')
