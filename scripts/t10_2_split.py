"""
MODULE : scripts/t10_2_split.py
DESCRIPTION : Split fixe 70/15/15 stratifié sur Label_Anomalie pour
              les deux branches (Santé + Auto) simultanément.
              Gère les doublons sur ID_Sinistre : le split se fait
              au niveau des IDs uniques pour éviter les fuites.

RÉFÉRENCES ACADÉMIQUES :
- [Kohavi1995] Kohavi, R. (1995). A study of cross-validation and bootstrap
  for accuracy estimation. IJCAI.
- [Caruana1997] Caruana, R. (1997). Multitask learning. Machine Learning.

DÉCISIONS DE CONCEPTION :
- Split au niveau des ID_Sinistre uniques (pas des lignes) — anti-fuite.
- ids converti en np.ndarray avant train_test_split (fix PyArrow compat).
- Seed fixe 42 partout — reproductibilité protocole H0.

USAGE :
  python scripts/t10_2_split.py
  python scripts/t10_2_split.py --dry-run
  python scripts/t10_2_split.py --branch sante
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t10_2")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR     = PROJECT_ROOT / "data" / "processed"
SPLITS_DIR   = PROJECT_ROOT / "data" / "splits"

RANDOM_STATE = 42
TEST_SIZE    = 0.30
VAL_RATIO    = 0.50

BRANCHES: dict[str, Path] = {
    "sante": DATA_DIR / "sante" / "dataset_sante_v1.parquet",
    "auto":  DATA_DIR / "auto"  / "dataset_auto_v1.parquet",
}

LABEL_COL  = "Label_Anomalie"
NORMAL_VAL = "NORMAL"
ID_COL     = "ID_Sinistre"


# ─── Types ────────────────────────────────────────────────────────────────────

class SplitResult(NamedTuple):
    branch:   str
    df_train: pd.DataFrame
    df_val:   pd.DataFrame
    df_test:  pd.DataFrame
    stats:    dict


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _split_stats(df: pd.DataFrame, name: str) -> dict:
    n_anom = int((df[LABEL_COL] != NORMAL_VAL).sum())
    return {
        "name":          name,
        "n_total":       len(df),
        "n_normal":      int((df[LABEL_COL] == NORMAL_VAL).sum()),
        "n_anomalie":    n_anom,
        "taux_anomalie": round(n_anom / len(df), 4),
    }


# ─── Chargement ──────────────────────────────────────────────────────────────

def load_branch(branch: str, path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset '{branch}' introuvable : {path}\n"
            f"Lancer d'abord : python scripts/setup_datasets.py"
        )
    log.info("[%s] Chargement : %s", branch.upper(), path)
    df = pd.read_parquet(path)
    log.info("[%s] Dimensions : %d × %d", branch.upper(), *df.shape)

    if LABEL_COL not in df.columns:
        raise ValueError(f"Colonne '{LABEL_COL}' absente dans {branch}.")

    if ID_COL in df.columns:
        n_dup    = int(df[ID_COL].duplicated().sum())
        n_unique = int(df[ID_COL].nunique())
        log.info("[%s] ID uniques : %d | Doublons lignes : %d",
                 branch.upper(), n_unique, n_dup)
        if n_dup > 0:
            log.info("[%s] ⚠️  Doublons — split au niveau des IDs uniques.",
                     branch.upper())
    else:
        log.warning("[%s] '%s' absente — split sur lignes.", branch.upper(), ID_COL)

    taux = (df[LABEL_COL] != NORMAL_VAL).mean()
    log.info("[%s] Taux anomalies : %.2f%%", branch.upper(), taux * 100)
    return df


# ─── Split robuste aux doublons ──────────────────────────────────────────────

def make_split(branch: str, df: pd.DataFrame) -> SplitResult:
    """
    Split stratifié 70/15/15 au niveau des IDs uniques.

    Stratégie anti-fuite [Kohavi1995] :
    1. Index ID → label binaire (1 si au moins 1 ligne anomalie)
    2. Splitter les IDs uniques (numpy array — fix compat PyArrow)
    3. Récupérer les lignes par isin()

    Fallback : split sur lignes si ID_Sinistre absent.
    """
    if ID_COL not in df.columns:
        log.warning("[%s] Fallback : split sur lignes.", branch.upper())
        return _split_on_rows(branch, df)

    # ── Étape 1 : label par ID unique ──────────────────────────────
    id_label = (
        df.groupby(ID_COL)[LABEL_COL]
        .apply(lambda s: int((s != NORMAL_VAL).any()))
        .reset_index()
        .rename(columns={LABEL_COL: "y"})
    )

    # CRITIQUE : convertir en numpy pur (évite le TypeError PyArrow)
    ids   = id_label[ID_COL].to_numpy()      # np.ndarray de strings
    y_ids = id_label["y"].to_numpy(dtype=int) # np.ndarray d'int

    log.info("[%s] IDs uniques : %d | Anomalies IDs : %d (%.1f%%)",
             branch.upper(), len(ids),
             int(y_ids.sum()), y_ids.mean() * 100)

    # ── Étape 2 : split sur IDs numpy ──────────────────────────────
    ids_train, ids_tmp, _, y_tmp = train_test_split(
        ids, y_ids,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_ids,
    )
    ids_val, ids_test, _, _ = train_test_split(
        ids_tmp, y_tmp,
        test_size=VAL_RATIO,
        random_state=RANDOM_STATE,
        stratify=y_tmp,
    )

    # ── Étape 3 : récupérer les lignes correspondantes ─────────────
    set_train = set(ids_train)
    set_val   = set(ids_val)
    set_test  = set(ids_test)

    df_train = df[df[ID_COL].isin(set_train)].copy().reset_index(drop=True)
    df_val   = df[df[ID_COL].isin(set_val)].copy().reset_index(drop=True)
    df_test  = df[df[ID_COL].isin(set_test)].copy().reset_index(drop=True)

    # ── Vérification étanchéité ────────────────────────────────────
    leak_tv = set_train & set_val
    leak_tt = set_train & set_test
    leak_vt = set_val   & set_test
    if leak_tv or leak_tt or leak_vt:
        raise ValueError(
            f"FUITE IDs — train∩val={len(leak_tv)}, "
            f"train∩test={len(leak_tt)}, val∩test={len(leak_vt)}"
        )
    log.info("[%s] ✅ Étanchéité OK (niveau IDs).", branch.upper())

    stats = {
        "branch":       branch,
        "random_state": RANDOM_STATE,
        "split_level":  ID_COL,
        "train": _split_stats(df_train, "train"),
        "val":   _split_stats(df_val,   "val"),
        "test":  _split_stats(df_test,  "test"),
    }

    for sn in ("train", "val", "test"):
        s = stats[sn]
        log.info("[%s] %-6s : %6d lignes | anomalies : %4d (%.1f%%)",
                 branch.upper(), sn,
                 s["n_total"], s["n_anomalie"], s["taux_anomalie"] * 100)

    return SplitResult(branch, df_train, df_val, df_test, stats)


def _split_on_rows(branch: str, df: pd.DataFrame) -> SplitResult:
    """Fallback : split direct sur les lignes."""
    y = (df[LABEL_COL] != NORMAL_VAL).to_numpy(dtype=int)
    df_arr = np.arange(len(df))

    idx_train, idx_tmp, _, y_tmp = train_test_split(
        df_arr, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y,
    )
    idx_val, idx_test, _, _ = train_test_split(
        idx_tmp, y_tmp, test_size=VAL_RATIO, random_state=RANDOM_STATE, stratify=y_tmp,
    )
    df_train = df.iloc[idx_train].copy().reset_index(drop=True)
    df_val   = df.iloc[idx_val].copy().reset_index(drop=True)
    df_test  = df.iloc[idx_test].copy().reset_index(drop=True)

    stats = {
        "branch": branch, "random_state": RANDOM_STATE, "split_level": "rows",
        "train": _split_stats(df_train, "train"),
        "val":   _split_stats(df_val,   "val"),
        "test":  _split_stats(df_test,  "test"),
    }
    for sn in ("train", "val", "test"):
        s = stats[sn]
        log.info("[%s] %-6s : %6d lignes | anomalies : %4d (%.1f%%)",
                 branch.upper(), sn,
                 s["n_total"], s["n_anomalie"], s["taux_anomalie"] * 100)
    return SplitResult(branch, df_train, df_val, df_test, stats)


# ─── Persistance ─────────────────────────────────────────────────────────────

def save_split(result: SplitResult, out_dir: Path, dry_run: bool = False) -> dict:
    branch_dir = out_dir / result.branch
    if not dry_run:
        branch_dir.mkdir(parents=True, exist_ok=True)

    checksums: dict = {}
    for split_name, df in (
        ("train", result.df_train),
        ("val",   result.df_val),
        ("test",  result.df_test),
    ):
        fname = f"{result.branch}_{split_name}.parquet"
        fpath = branch_dir / fname
        if not dry_run:
            df.to_parquet(fpath, index=False, compression="snappy")
            sha = _sha256(fpath)
            checksums[fname] = sha[:16] + "..."
            log.info("[%s] Écrit : %s (%d Mo)", result.branch.upper(),
                     fname, round(fpath.stat().st_size / 1e6, 1))
        else:
            log.info("[DRY-RUN] %s — %d lignes", fname, len(df))
    return checksums


def save_metadata(
    all_stats: list[dict], all_checksums: dict,
    out_dir: Path, dry_run: bool = False,
) -> None:
    meta = {
        "protocol":      "MAKORA Bloc B — T10.2",
        "random_state":  RANDOM_STATE,
        "splits_ratio":  {"train": 0.70, "val": 0.15, "test": 0.15},
        "stratified_on": LABEL_COL,
        "split_level":   ID_COL,
        "branches":      all_stats,
        "checksums":     all_checksums,
        "note": (
            "Split au niveau des IDs uniques — anti-fuite [Kohavi1995]. "
            "Test set IMMUTABLE [Caruana1997]."
        ),
    }
    meta_path = out_dir / "split_metadata.json"
    if not dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        log.info("Métadonnées : %s", meta_path)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.2 — Split fixe 70/15/15 stratifié"
    )
    p.add_argument("--branch", choices=["sante", "auto", "both"], default="both")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out-dir", type=Path, default=SPLITS_DIR)
    return p.parse_args()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    SEP  = "─" * 60
    log.info(SEP)
    log.info("MAKORA — T10.2 Split fixe 70/15/15")
    log.info("Seed : %d | Sortie : %s", RANDOM_STATE, args.out_dir)
    if args.dry_run:
        log.info("MODE : DRY-RUN")
    log.info(SEP)

    branches_to_run = (
        list(BRANCHES.items()) if args.branch == "both"
        else [(args.branch, BRANCHES[args.branch])]
    )

    all_stats:     list[dict] = []
    all_checksums: dict       = {}

    for branch, path in branches_to_run:
        log.info(SEP)
        try:
            df     = load_branch(branch, path)
            result = make_split(branch, df)
            chks   = save_split(result, args.out_dir, dry_run=args.dry_run)
            all_stats.append(result.stats)
            all_checksums.update(chks)
        except (FileNotFoundError, ValueError) as exc:
            log.error("%s", exc)
            sys.exit(1)

    log.info(SEP)
    save_metadata(all_stats, all_checksums, args.out_dir, dry_run=args.dry_run)
    log.info(SEP)
    log.info("✅ T10.2 terminé.")
    log.info("Prochaine étape :")
    log.info("  python scripts/t10_3_train_if.py --branch sante")
    log.info("  python scripts/t10_3_train_if.py --branch auto")
    log.info(SEP)


if __name__ == "__main__":
    main()