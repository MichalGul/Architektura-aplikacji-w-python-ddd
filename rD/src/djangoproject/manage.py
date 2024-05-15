#!/usr/bin/env python
"""Narzędzie wiersza poleceń Django do zadań administracyjnych."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Błąd importu Django. Jesteś pewny, że jest zainstalowany i "
            "dostępny w zmiennej środowiskowej PYTHONPATH? Czy "
            "zapomniałeś aktywować środowisko wirtualne?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
