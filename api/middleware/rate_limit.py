"""
MODULE : api/middleware/rate_limit.py
DESCRIPTION : Configuration rate limiting via slowapi.
5 req/min sur /auth/login, 100 req/min sur le reste.

DÉCISION DE CONCEPTION :
- En mode TESTING (variable d'env TESTING=true), le limiter est remplacé
  par un no-op decorator. Cela évite les 429 pendant les tests sans modifier
  la logique de production.
- Le @limiter.limit("5/minute") est appliqué au moment de l'import du module
  router — le patch doit donc se faire ICI, avant tout import des routers.
"""
import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


def _noop_limit(*args, **kwargs):
    """Décorateur no-op pour les tests — ne limite rien."""
    def decorator(func):
        return func
    return decorator


class _NoOpLimiter:
    """Limiter factice pour les tests — toutes les méthodes sont des no-ops."""
    def limit(self, *args, **kwargs):
        return _noop_limit(*args, **kwargs)

    def shared_limit(self, *args, **kwargs):
        return _noop_limit(*args, **kwargs)


# Vérification AVANT la création du vrai limiter
# → le décorateur @limiter.limit(...) utilise l'objet instancié ici
if os.environ.get("TESTING", "").lower() in ("true", "1", "yes"):
    limiter = _NoOpLimiter()
else:
    limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


def setup_rate_limit(app) -> None:
    """Configure le rate limiting sur l'app FastAPI.
    En mode TESTING, n'attache pas le vrai limiter à app.state.
    """
    if isinstance(limiter, _NoOpLimiter):
        return  # Pas de rate limiting en test
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)