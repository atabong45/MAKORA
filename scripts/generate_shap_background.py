"""
MODULE : scripts/generate_shap_background.py
DESCRIPTION : Génère les fichiers shap_background.npy nécessaires à KernelSHAP
              pour les branches Santé et Auto.

CORRECTION (v2) :
Le DIF peut avoir été entraîné sur N features alors que le module courant
en expose M > N. On détecte N depuis dif.minmax_scaler.n_features_in_ et
on restreint le background à ces N features — cohérence garantie avec
_build_pipeline() qui applique la même logique.

POURQUOI :
KernelSHAP [Lundberg2017] nécessite un "background dataset" représentatif
de la distribution d'entraînement servant de référence pour calculer les
contributions SHAP. Sa shape doit correspondre exactement aux features
attendues par le DIF.

PROCÉDURE :
1. Charge data/splits/{branch}/{branch}_train.parquet
2. Applique engineer_features() du module métier via PluginRegistry
3. Restreint aux features attendues par le DIF (auto-détection depuis scaler)
4. Échantillonne N_BACKGROUND lignes (défaut 50) — stratifié sur le label
5. Sauve en data/models/{branch}/shap_background.npy au format float32

USAGE :
    docker compose exec api python scripts/generate_shap_background.py
    docker compose exec api python scripts/generate_shap_background.py --branch sante
    docker compose exec api python scripts/generate_shap_background.py --n 100

RÉFÉRENCES :
- [Lundberg2017] KernelSHAP avec background set.
- [Sculley2015] Le background doit refléter la distribution réelle.
- [Xu2023] DIF — le minmax_scaler interne dicte le nombre de features.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.shap_bg")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SPLITS_DIR = PROJECT_ROOT / "data" / "splits"
MODELS_DIR = PROJECT_ROOT / "data" / "models"

DEFAULT_N_BACKGROUND = 50
RANDOM_STATE = 42
LABEL_COL = "Label_Anomalie"
NORMAL_VAL = "NORMAL"


def _load_training_split(branch: str) -> pd.DataFrame:
    """Charge le training set issu de T10.2 (split immuable)."""
    path = SPLITS_DIR / branch / f"{branch}_train.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"Training set introuvable : {path}\n"
            f"Lance d'abord : python scripts/t10_2_split.py"
        )
    df = pd.read_parquet(path)
    log.info("[%s] Training set chargé : %d lignes × %d colonnes",
             branch.upper(), *df.shape)
    return df


def _apply_module_features(df: pd.DataFrame, branch: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Applique engineer_features() du module métier via PluginRegistry.
    Ce script est dans scripts/ (hors Kernel) — imports directs autorisés.
    """
    from core.plugin_registry import PluginRegistry

    if branch == "sante":
        import modules.sante.sante_module  # noqa: F401
    elif branch == "auto":
        import modules.auto.auto_module    # noqa: F401
    else:
        raise ValueError(f"Branche inconnue : {branch}")

    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module = PluginRegistry.get(branch)(config_path=yaml_path)

    df_eng = module.engineer_features(df)
    feats = [f for f in module.get_feature_names() if f in df_eng.columns]

    log.info("[%s] engineer_features() OK — %d features module",
             branch.upper(), len(feats))
    if not feats:
        raise RuntimeError(
            f"[{branch}] Aucune feature retournée par module.get_feature_names()."
        )
    return df_eng, feats


def _restrict_to_dif_features(
    feats: list[str], branch: str
) -> list[str]:
    """
    Détecte le nombre de features attendu par le DIF depuis son
    minmax_scaler.n_features_in_ et restreint la liste si nécessaire.

    [Xu2023] — cohérence garantie avec _build_pipeline() qui applique
    la même logique de restriction.
    """
    dif_path = MODELS_DIR / branch / "dif_model.joblib"
    if not dif_path.exists():
        log.warning("[%s] dif_model.joblib absent — pas de restriction features",
                    branch.upper())
        return feats

    dif = joblib.load(dif_path)
    scaler = getattr(dif, "minmax_scaler", None)
    expected_n = getattr(scaler, "n_features_in_", None)

    if expected_n is None:
        log.warning("[%s] minmax_scaler.n_features_in_ non disponible — "
                    "pas de restriction", branch.upper())
        return feats

    if expected_n == len(feats):
        log.info("[%s] Features cohérentes : module=%d = DIF=%d ✅",
                 branch.upper(), len(feats), expected_n)
        return feats

    log.warning(
        "[%s] Feature mismatch : module=%d, DIF=%d → restriction "
        "aux %d premières [Xu2023]",
        branch.upper(), len(feats), expected_n, expected_n,
    )
    return feats[:expected_n]


def _stratified_sample(
    df: pd.DataFrame, n: int, seed: int = RANDOM_STATE
) -> pd.DataFrame:
    """
    Échantillonne n lignes, stratifié sur Label_Anomalie si présent.
    Sinon échantillonnage uniforme.
    """
    rng = np.random.default_rng(seed)

    if LABEL_COL in df.columns:
        prop_anom = (df[LABEL_COL] != NORMAL_VAL).mean()
        n_anom = max(1, min(round(n * prop_anom), n - 1))
        n_normal = n - n_anom

        normal_mask = df[LABEL_COL] == NORMAL_VAL
        df_normal = df[normal_mask]
        df_anom = df[~normal_mask]

        idx_n = rng.choice(len(df_normal), size=min(n_normal, len(df_normal)), replace=False)
        idx_a = rng.choice(len(df_anom), size=min(n_anom, len(df_anom)), replace=False)

        sample = pd.concat([
            df_normal.iloc[idx_n],
            df_anom.iloc[idx_a],
        ]).reset_index(drop=True)
        log.info("Échantillon stratifié : %d normaux + %d anomalies = %d total",
                 len(idx_n), len(idx_a), len(sample))
    else:
        idx = rng.choice(len(df), size=min(n, len(df)), replace=False)
        sample = df.iloc[idx].reset_index(drop=True)
        log.info("Échantillon uniforme : %d lignes", len(sample))

    return sample


def generate_background_for_branch(branch: str, n_background: int) -> Path:
    """Pipeline complet pour une branche. Retourne le path du .npy créé."""
    log.info("=" * 60)
    log.info("Génération SHAP background pour : %s", branch.upper())
    log.info("=" * 60)

    # 1. Charger le training set
    df = _load_training_split(branch)

    # 2. Appliquer le feature engineering du module
    df_eng, feats = _apply_module_features(df, branch)

    # 3. Restreindre aux features attendues par le DIF [Xu2023]
    feats = _restrict_to_dif_features(feats, branch)
    log.info("[%s] Features retenues pour le background : %d", branch.upper(), len(feats))

    # 4. Échantillonner
    sample = _stratified_sample(df_eng, n_background, seed=RANDOM_STATE)

    # 5. Extraire la matrice numérique (float32 obligatoire pour SHAP)
    X = sample[feats].fillna(0).values.astype(np.float32)
    log.info("[%s] Matrice background : shape=%s dtype=%s",
             branch.upper(), X.shape, X.dtype)

    # 6. Sauvegarder
    out_dir = MODELS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "shap_background.npy"

    if out_path.exists():
        backup = out_dir / "shap_background.npy.bak"
        log.warning("[%s] Fichier existant → backup : %s", branch.upper(), backup.name)
        out_path.rename(backup)

    np.save(out_path, X)
    size_kb = out_path.stat().st_size / 1024
    log.info("[%s] ✅ Sauvegardé : %s (%.1f Ko) — shape=%s",
             branch.upper(), out_path, size_kb, X.shape)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Génère les fichiers shap_background.npy pour KernelSHAP."
    )
    parser.add_argument(
        "--branch", choices=["sante", "auto", "both"], default="both",
    )
    parser.add_argument(
        "--n", type=int, default=DEFAULT_N_BACKGROUND,
        help=f"Nombre de lignes du background (défaut : {DEFAULT_N_BACKGROUND})",
    )
    args = parser.parse_args()
    branches = ["sante", "auto"] if args.branch == "both" else [args.branch]

    results = []
    for branch in branches:
        try:
            path = generate_background_for_branch(branch, args.n)
            results.append((branch, path, "OK"))
        except Exception as exc:
            log.error("[%s] Échec : %s", branch.upper(), exc, exc_info=True)
            results.append((branch, None, f"ERREUR: {exc}"))

    print()
    print("=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    for branch, path, status in results:
        print(f"  {branch.upper():8s} {status}")
        if path:
            print(f"           → {path}")

    return 0 if all(s == "OK" for _, _, s in results) else 1


if __name__ == "__main__":
    sys.exit(main())

    