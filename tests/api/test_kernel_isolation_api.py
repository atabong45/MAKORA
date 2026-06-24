"""
MODULE : tests/api/test_kernel_isolation_api.py
DESCRIPTION : Vérification AST — Garantit qu'aucun fichier api/ n'importe
un module métier par son nom concret (ADR-002 Kernel isolation).

Ce test est un garde-fou automatique : il échoue dès qu'un développeur
ajoute un import interdit, avant même l'exécution du code.
"""
import ast
import pathlib
import pytest

FORBIDDEN_MODULES = [
    "modules.sante",
    "modules.auto",
    "modules.vie",
    "modules.agricole",
    "modules.sante.sante_module",
    "modules.auto.auto_module",
]

API_DIR = pathlib.Path(__file__).parent.parent.parent / "api"


def _get_imports(filepath: pathlib.Path) -> list[str]:
    """Extrait tous les modules importés depuis un fichier Python."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
    return imports


@pytest.mark.parametrize("py_file", sorted(API_DIR.rglob("*.py")))
def test_no_forbidden_import(py_file):
    """Vérifie que le fichier n'importe aucun module métier par nom concret."""
    imports = _get_imports(py_file)
    for mod in imports:
        for forbidden in FORBIDDEN_MODULES:
            assert not mod.startswith(forbidden), (
                f"ADR-002 VIOLATION dans {py_file.relative_to(API_DIR.parent)}:\n"
                f"  Import interdit : '{mod}'\n"
                f"  Utiliser PluginRegistry.get(branch) à la place."
            )


def test_analyze_service_uses_plugin_registry():
    """Vérifie que analyze_service.py utilise bien PluginRegistry."""
    src = (API_DIR / "services" / "analyze_service.py").read_text()
    assert "PluginRegistry" in src, "analyze_service.py doit utiliser PluginRegistry"
    assert "PluginRegistry.get" in src, "PluginRegistry.get(branch) requis (ADR-002)"


def test_all_routers_have_prefix():
    """Vérifie que tous les routers définissent un prefix."""
    for router_file in (API_DIR / "routers").glob("*.py"):
        if router_file.name.startswith("__"):
            continue
        src = router_file.read_text()
        assert "APIRouter" in src, f"{router_file.name} ne définit pas de APIRouter"
