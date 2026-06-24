"""
MODULE : scripts/_ml_common.py
DESCRIPTION : Utilitaires partagés par les scripts de challengers Phase 2b
              (t10_4b / t10_4c / t10_4d). Centralise le chargement des splits,
              l'appel à engineer_features() via le Plugin Contract, le calcul
              des métriques ADR-006, et — surtout — la STRATÉGIE DE RÉSILIENCE :
              sauvegarde incrémentale + timeout par modèle + isolation des
              erreurs, pour qu'un modèle qui bloque ou que l'on interrompt
              manuellement n'efface jamais les résultats déjà obtenus.

RÉFÉRENCES ACADÉMIQUES :
- [Goldstein2016] Goldstein & Uchida (2016). Comparative evaluation of
  unsupervised anomaly detection algorithms. PLOS ONE.
  → Métriques et protocole de comparaison homogènes entre algorithmes.
- [Matthews1975] Matthews, B.W. (1975). Comparison of the predicted and
  observed secondary structure of T4 phage lysozyme. → MCC.
- [Davis2006] Davis & Goadrich (2006). The relationship between Precision-
  Recall and ROC curves. ICML. → Average Precision sur données déséquilibrées.

DÉCISIONS DE CONCEPTION :
- Module partagé (et non duplication par fichier) — évite la dérive entre
  scripts et garde chaque script sous 400 lignes (IMP-007).
- Sauvegarde incrémentale : le JSON est réécrit après CHAQUE modèle terminé.
  → Interruption manuelle (Ctrl-C) = tous les modèles précédents sont conservés.
- Timeout par modèle via signal.SIGALRM (Linux/Docker) — un modèle trop long
  est abandonné proprement et marqué "timeout", les autres continuent.
- Isolation des erreurs : une exception sur un modèle ne tue pas la campagne.
"""
from __future__ import annotations

import json
import logging
import signal
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

# ─── Chemins & constantes (identiques à t10_3 / t10_4) ───────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR = PROJECT_ROOT / "data" / "splits"
MODELS_DIR = PROJECT_ROOT / "data" / "models"
RESULTS_DIR = PROJECT_ROOT / "results"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RANDOM_STATE = 42
LABEL_COL = "Label_Anomalie"
NORMAL_VAL = "NORMAL"

# [Bauder2017] — plage contamination documentée fraude assurance 3-10 %
CONTAMINATION_GRID = [0.03, 0.05, 0.07, 0.08, 0.10, 0.12]

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
}

log = logging.getLogger("makora.challengers")


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


# ─── Chargement des données (mêmes conventions que t10_4) ────────────────────

def load_splits(
    branch: str, need_val: bool = True
) -> tuple[pd.DataFrame, Optional[pd.DataFrame], pd.DataFrame]:
    """Charge les splits Parquet produits par T10.2."""
    branch_dir = SPLITS_DIR / branch
    wanted = ("train", "val", "test") if need_val else ("train", "test")
    splits: dict[str, pd.DataFrame] = {}
    for name in wanted:
        path = branch_dir / f"{branch}_{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"Split '{name}' introuvable : {path}\n"
                f"Lancer d'abord : python scripts/t10_2_split.py"
            )
        splits[name] = pd.read_parquet(path)
    log.info(
        "[%s] Splits chargés — %s",
        branch.upper(),
        " | ".join(f"{k}={len(v)}" for k, v in splits.items()),
    )
    return splits["train"], splits.get("val"), splits["test"]


def apply_module(df: pd.DataFrame, branch: str) -> tuple[pd.DataFrame, list[str]]:
    """Appelle engineer_features() du module via PluginRegistry (Plugin Contract)."""
    from core.plugin_registry import PluginRegistry

    if branch == "sante":
        import modules.sante.sante_module  # noqa: F401 — déclenche @register
    elif branch == "auto":
        import modules.auto.auto_module  # noqa: F401 — déclenche @register

    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module = PluginRegistry.get(branch)(config_path=yaml_path)
    df_eng = module.engineer_features(df.copy())
    feats = [f for f in module.get_feature_names() if f in df_eng.columns]
    log.info("[%s] engineer_features → %d features", branch.upper(), len(feats))
    return df_eng, feats


def get_xy(df: pd.DataFrame, feats: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Extrait X (features métier explicites) et y binaire."""
    X = df[feats].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).astype(int).to_numpy()
    return X, y


def load_best_contamination(branch: str) -> float:
    """Récupère la contamination optimale calibrée en T10.3 (sinon défaut)."""
    path = RESULTS_DIR / branch / "t10_3_if_results.json"
    if path.exists():
        try:
            data = json.loads(path.read_text())
            for entry in data:
                if entry.get("algo") == "IsolationForest":
                    c = entry.get("metrics", {}).get("contamination", 0.08)
                    log.info("Contamination issue de T10.3 : %.3f", float(c))
                    return float(c)
        except Exception as exc:  # noqa: BLE001
            log.warning("Lecture t10_3 échouée (%s) — défaut 0.08", exc)
    log.info("T10.3 introuvable — contamination défaut : 0.08 [Bauder2017]")
    return 0.08


# ─── Métriques (ADR-006 complet : + MCC, FPR, AP) ────────────────────────────

def compute_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, scores: np.ndarray
) -> dict:
    """
    Calcule les métriques ADR-006 — [Goldstein2016].
    scores : plus élevé = plus anormal (convention PyOD).
    """
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    return {
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "auc_roc": round(float(roc_auc_score(y_true, scores)), 4),
        "average_precision": round(float(average_precision_score(y_true, scores)), 4),
        "mcc": round(float(matthews_corrcoef(y_true, y_pred)), 4),
        "fpr": round(fpr, 4),
        "n_pred_anomalie": int(y_pred.sum()),
        "n_true_anomalie": int(y_true.sum()),
    }


# ─── STRATÉGIE DE RÉSILIENCE ─────────────────────────────────────────────────

class ModelTimeout(Exception):
    """Levée quand un modèle dépasse le budget temps alloué."""


@contextmanager
def time_limit(seconds: int):
    """
    Limite le temps d'exécution d'un bloc via SIGALRM (Linux/Docker).

    Best-effort : l'alarme interrompt au prochain bytecode Python. Les boucles
    natives C très longues (rare ici) peuvent ne pas s'interrompre instantanément.
    seconds <= 0 → pas de limite.
    """
    if seconds and seconds > 0 and hasattr(signal, "SIGALRM"):
        def _handler(signum, frame):  # noqa: ANN001
            raise ModelTimeout(f"Dépassement du budget de {seconds}s")

        old = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
    else:
        yield


def save_results_incremental(results: list[dict], branch: str, filename: str) -> Path:
    """
    Réécrit l'intégralité du JSON après chaque modèle terminé.

    C'est le cœur de la résilience : à tout instant, le fichier sur disque
    reflète tous les modèles déjà aboutis. Une interruption ultérieure ne
    peut donc rien faire perdre.
    """
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    return path


def run_model_safe(
    name: str,
    fn: Callable[[], Optional[dict]],
    results: list[dict],
    branch: str,
    out_filename: str,
    timeout_s: int = 0,
) -> None:
    """
    Exécute un entraînement de modèle de façon défensive :

    - timeout par modèle (time_limit) → marqué "timeout", on continue
    - toute exception est isolée → marquée "error", on continue
    - succès → résultat ajouté ET sauvegardé immédiatement (incrémental)
    - Ctrl-C (KeyboardInterrupt) → on sauvegarde l'état puis on re-propage
      pour arrêter proprement la campagne (les modèles précédents sont saufs).
    """
    log.info("─" * 60)
    log.info("▶ Modèle : %s", name)
    t0 = time.perf_counter()
    try:
        with time_limit(timeout_s):
            res = fn()
        if res is None:
            log.warning("  %s a renvoyé None — ignoré (dépendance manquante ?)", name)
            entry = {"algo": name, "status": "skipped"}
        else:
            res.setdefault("status", "ok")
            res.setdefault("algo", name)
            elapsed = round(time.perf_counter() - t0, 2)
            res.get("metrics", {}).setdefault("train_time_s", elapsed)
            m = res.get("metrics", {})
            log.info(
                "  ✅ %s — F1=%.4f | AUC=%.4f | AP=%.4f | %.1fs",
                name, m.get("f1", 0), m.get("auc_roc", 0),
                m.get("average_precision", 0), elapsed,
            )
            entry = res
    except ModelTimeout as exc:
        log.error("  ⏱ TIMEOUT %s : %s — modèle abandonné, on continue.", name, exc)
        entry = {"algo": name, "status": "timeout", "timeout_s": timeout_s}
    except KeyboardInterrupt:
        log.warning("  ⛔ Interruption manuelle pendant %s.", name)
        entry = {"algo": name, "status": "interrupted"}
        results.append(entry)
        path = save_results_incremental(results, branch, out_filename)
        log.warning("  État sauvegardé (%d entrées) : %s", len(results), path)
        raise
    except Exception as exc:  # noqa: BLE001
        log.error("  ❌ ERREUR %s : %s — on continue.", name, exc)
        entry = {"algo": name, "status": "error", "error": str(exc)}

    results.append(entry)
    path = save_results_incremental(results, branch, out_filename)
    log.info("  💾 Sauvegarde incrémentale (%d entrées) → %s", len(results), path.name)


def print_summary(results: list[dict]) -> None:
    """Affiche un tableau récapitulatif Markdown copiable dans le mémoire."""
    log.info("=" * 60)
    log.info("RÉCAPITULATIF")
    log.info("=" * 60)
    header = f"| {'Algorithme':<22} | {'Statut':<11} | {'F1':>6} | {'AUC':>6} | {'AP':>6} | {'MCC':>6} | {'FPR':>6} |"
    sep = "|" + "-" * 24 + "|" + "-" * 13 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 8 + "|"
    print(header)
    print(sep)
    for r in results:
        if "metrics" not in r and "algo" not in r:
            continue
        m = r.get("metrics", {})
        print(
            f"| {r.get('algo', '?'):<22} | {r.get('status', 'ok'):<11} "
            f"| {m.get('f1', 0):>6.4f} | {m.get('auc_roc', 0):>6.4f} "
            f"| {m.get('average_precision', 0):>6.4f} | {m.get('mcc', 0):>6.4f} "
            f"| {m.get('fpr', 0):>6.4f} |"
        )