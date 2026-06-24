"""
scripts/setup_datasets.py
Convertit les CSV générés en Parquet et les place dans la structure cible.

USAGE :
  python scripts/setup_datasets.py                        # auto-détection
  python scripts/setup_datasets.py --auto  chemin/auto.csv
  python scripts/setup_datasets.py --sante chemin/sante.csv
  python scripts/setup_datasets.py --auto  auto.csv --test-auto  test.csv
"""
import argparse
import hashlib
import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("makora.setup")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Emplacements cibles (architecture MAKORA)
TARGETS = {
    "auto":  PROJECT_ROOT / "data" / "processed" / "auto",
    "sante": PROJECT_ROOT / "data" / "processed" / "sante",
}

# Noms des fichiers CSV attendus par le générateur ARGUS/UNITY
CSV_CANDIDATES = {
    "auto":       ["dataset_auto_v1.csv", "dataset_auto_argus_raw.csv"],
    "auto_test":  ["dataset_auto_test_fixe.csv"],
    "sante":      ["dataset_sante_v1.csv", "dataset_sante_unity_raw.csv"],
    "sante_test": ["dataset_sante_test_fixe.csv"],
}


def _find_csv(candidates: list[str]) -> Path | None:
    """Cherche récursivement depuis PROJECT_ROOT."""
    for name in candidates:
        for p in PROJECT_ROOT.rglob(name):
            return p
    return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def convert_and_place(csv_path: Path, out_dir: Path, out_name: str) -> Path:
    """
    Lit un CSV, le convertit en Parquet compressé (snappy),
    écrit le checksum SHA-256, retourne le chemin Parquet.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = out_dir / out_name

    log.info("Lecture CSV  : %s", csv_path)
    log.info("Taille       : %.1f MB", csv_path.stat().st_size / 1e6)
    df = pd.read_csv(csv_path, low_memory=False)
    log.info("Dimensions   : %d lignes × %d colonnes", *df.shape)

    # Vérification minimale
    if "Label_Anomalie" not in df.columns:
        log.warning("Colonne 'Label_Anomalie' absente — vérifier le CSV source.")
    else:
        n_anom = (df["Label_Anomalie"] != "NORMAL").sum()
        taux = n_anom / len(df)
        log.info("Anomalies    : %d (%.2f%%)", n_anom, taux * 100)
        if not (0.03 <= taux <= 0.15):
            log.warning("Taux anomalies hors plage [3%%,15%%] : %.2f%%", taux * 100)

    log.info("Écriture     : %s", out_parquet)
    df.to_parquet(out_parquet, index=False, compression="snappy")
    size_mb = out_parquet.stat().st_size / 1e6
    log.info("Taille Parquet : %.1f MB (ratio %.1f×)",
             size_mb, csv_path.stat().st_size / out_parquet.stat().st_size)

    # Checksum
    sha = _sha256(out_parquet)
    sha_path = out_parquet.with_suffix(".sha256")
    sha_path.write_text(f"{sha}  {out_name}\n")
    log.info("SHA-256      : %s…", sha[:16])
    return out_parquet


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MAKORA — Setup datasets Parquet")
    p.add_argument("--auto",       type=Path, default=None, metavar="CSV",
                   help="CSV dataset Auto complet")
    p.add_argument("--sante",      type=Path, default=None, metavar="CSV",
                   help="CSV dataset Santé complet")
    p.add_argument("--test-auto",  type=Path, default=None, metavar="CSV",
                   help="CSV test fixe Auto (optionnel)")
    p.add_argument("--test-sante", type=Path, default=None, metavar="CSV",
                   help="CSV test fixe Santé (optionnel)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    SEP = "─" * 55
    log.info(SEP)
    log.info("MAKORA — Conversion CSV → Parquet")
    log.info("Projet : %s", PROJECT_ROOT)
    log.info(SEP)

    tasks = []  # (csv_path, out_dir, out_name, label)

    # ── Auto ──────────────────────────────────────────────────────
    auto_csv = args.auto or _find_csv(CSV_CANDIDATES["auto"])
    if auto_csv:
        tasks.append((auto_csv, TARGETS["auto"], "dataset_auto_v1.parquet", "Auto complet"))
    else:
        log.warning("CSV Auto introuvable — ignoré. Passer --auto CHEMIN.csv")

    auto_test = args.test_auto or _find_csv(CSV_CANDIDATES["auto_test"])
    if auto_test:
        tasks.append((auto_test, TARGETS["auto"], "dataset_auto_v1_test.parquet", "Auto test fixe"))
    else:
        log.info("CSV test Auto absent — le test fixe sera créé par t10_8_final_eval.py")

    # ── Santé ─────────────────────────────────────────────────────
    sante_csv = args.sante or _find_csv(CSV_CANDIDATES["sante"])
    if sante_csv:
        tasks.append((sante_csv, TARGETS["sante"], "dataset_sante_v1.parquet", "Santé complet"))
    else:
        log.warning("CSV Santé introuvable — ignoré. Passer --sante CHEMIN.csv")

    sante_test = args.test_sante or _find_csv(CSV_CANDIDATES["sante_test"])
    if sante_test:
        tasks.append((sante_test, TARGETS["sante"], "dataset_sante_v1_test.parquet", "Santé test fixe"))

    if not tasks:
        log.error("Aucun CSV trouvé. Exemple d'utilisation :")
        log.error("  python scripts/setup_datasets.py \\")
        log.error("    --auto  ARGUS/data/processed/dataset_auto_v1.csv \\")
        log.error("    --sante UNITY/data/processed/dataset_sante_v1.csv")
        sys.exit(1)

    # ── Conversion ────────────────────────────────────────────────
    done = []
    for csv_path, out_dir, out_name, label in tasks:
        log.info(SEP)
        log.info("▶  %s", label)
        try:
            out = convert_and_place(csv_path, out_dir, out_name)
            done.append((label, out))
        except Exception as exc:
            log.error("Échec %s : %s", label, exc)

    log.info(SEP)
    log.info("Terminé — %d/%d fichier(s) convertis :", len(done), len(tasks))
    for label, path in done:
        log.info("  ✅ %-22s → %s", label, path)
    if done:
        log.info("")
        log.info("Prochaine étape :")
        log.info("  python scripts/t10_1_eda.py --branch auto")
        log.info("  python scripts/t10_1_eda.py --branch sante")
    log.info(SEP)


if __name__ == "__main__":
    main()