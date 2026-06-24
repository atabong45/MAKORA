"""
conftest.py — Racine du projet MAKORA
Injecte le répertoire racine dans sys.path pour que
"from core.xxx" et "from makora.core.xxx" fonctionnent
selon le contexte d'exécution (local vs Docker).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))