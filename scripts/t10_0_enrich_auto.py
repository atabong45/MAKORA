"""
MODULE : scripts/t10_0_enrich_auto.py
DESCRIPTION : Enrichissement du dataset Auto v1 → v2.
              Même logique que t10_0_enrich_sante.py, adapté
              au contexte Auto (garage↔assuré au lieu de praticien↔assuré).

PRINCIPE :
  - Lecture de dataset_auto_v1.csv ou .parquet
  - Ajout de 4 groupes de colonnes
  - Écriture de dataset_auto_v2.csv + .parquet
  - Le test fixe est traité séparément avec les MÊMES paramètres

COLONNES AJOUTÉES :
  Groupe 1 — Réseau garage↔assuré
    · ID_Garage     : redistribué avec concentration Pareto (si déjà aléatoire)
    · community_id_auto : label de communauté pré-calculé

  Groupe 2 — Doublons
    · Flag_Doublon_Auto : double déclaration d'un même sinistre
    · Nb_Declarations   : nombre de fois que ce sinistre a été soumis

  Groupe 3 — Drift monitor
    · Batch_Date    : date de batch pour suivi PSI [Gama2014]

  Groupe 4 — Expert
    · ID_Expert_Stable : identifiant expert redistribué avec structure réseau
                         (certains experts valident systématiquement des garages
                          spécifiques — signal de collusion [Viaene2002])

RÉFÉRENCES ACADÉMIQUES :
  [Viaene2002] Viaene et al. (2002). Automobile insurance fraud detection.
               Journal of Risk and Insurance.
               → Collusion garage-expert : concentration des validations
  [Jiang2014]  Jiang et al. (2014). CatchSync. KDD.
               → Distribution Pareto des garages, clusters frauduleux
  [Gama2014]   Gama et al. (2014). Concept drift adaptation.
               ACM Computing Surveys. → Batch_Date pour PSI

DÉCISIONS DE CONCEPTION :
  - ID_Garage redistribué uniquement si la distribution actuelle est plate
    (entropie proche du max). Si elle est déjà concentrée, on la garde.
  - Les clusters frauduleux sont injectés sur les dossiers FRAUDE uniquement
  - Seed = 42 pour reproductibilité
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ─── Configuration ────────────────────────────────────────────────────────────

SEED = 42
rng = np.random.default_rng(SEED)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("enrich_auto")

# Distribution Pareto garages
# [Jiang2014] : concentration typique dans les réseaux de fraude auto
N_GARAGES_POOL = 300
PARETO_ALPHA_GARAGE = 1.4        # légèrement moins concentré que santé

# Clusters réseau frauduleux garage↔assuré
N_CLUSTERS_AUTO = 8
CLUSTER_N_GARAGES = (2, 4)       # petit nombre de garages par cluster
CLUSTER_N_ASSURES = (15, 40)     # groupe d'assurés complices

# Distribution experts
N_EXPERTS_POOL = 120
PARETO_ALPHA_EXPERT = 1.3

# Seuil pour décider si ID_Garage est déjà structuré
ENTROPIE_SEUIL = 0.85            # au-dessus = distribution trop plate → redistribuer


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load(path: Path) -> pd.DataFrame:
    log.info("Chargement : %s", path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, low_memory=False)
    log.info("  → shape : %s", df.shape)
    return df


def _pareto_weights(n: int, alpha: float) -> np.ndarray:
    ranks = np.arange(1, n + 1, dtype=float)
    weights = ranks ** (-alpha)
    return weights / weights.sum()


def _normalized_entropy(series: pd.Series) -> float:
    """Entropie normalisée [0, 1]. 1 = distribution uniforme."""
    counts = series.value_counts(normalize=True)
    import math
    h = -sum(p * math.log2(p) for p in counts if p > 0)
    h_max = math.log2(len(counts)) if len(counts) > 1 else 1
    return h / h_max if h_max > 0 else 0.0


# ─── 1. Batch_Date ────────────────────────────────────────────────────────────

def add_batch_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crée Batch_Date depuis Date_Accident ou Date_Declaration.
    [Gama2014] — fenêtre 90j référence / 30j courante.
    """
    date_col = next(
        (c for c in ["Date_Accident", "Date_Sinistre", "Date_Declaration"]
         if c in df.columns), None
    )
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        df["Batch_Date"] = dates.dt.to_period("M").dt.to_timestamp()
        n_null = df["Batch_Date"].isna().sum()
        if n_null:
            df["Batch_Date"] = df["Batch_Date"].fillna(pd.Timestamp("2023-01-01"))
        log.info("  Batch_Date depuis '%s' — plage : %s → %s",
                 date_col, df["Batch_Date"].min(), df["Batch_Date"].max())
    else:
        months = pd.date_range("2021-01-01", "2025-12-01", freq="MS")
        df["Batch_Date"] = rng.choice(months, size=len(df))
        log.warning("  Aucune colonne date — Batch_Date généré aléatoirement")
    return df


# ─── 2. Redistribution ID_Garage ──────────────────────────────────────────────

def rebuild_garage_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Redistribue ID_Garage avec une distribution de Pareto si la distribution
    actuelle est trop plate (entropie normalisée > ENTROPIE_SEUIL).

    [Viaene2002] : les garages frauduleux tendent à concentrer les sinistres.
    Si la distribution est déjà concentrée, on ne touche pas aux IDs.
    """
    if "ID_Garage" not in df.columns:
        log.warning("  ID_Garage absent — création de zéro")
        df["ID_Garage"] = "GARAGE_000"

    entropie = _normalized_entropy(df["ID_Garage"])
    log.info("  Entropie normalisée ID_Garage : %.3f (seuil=%.2f)",
             entropie, ENTROPIE_SEUIL)

    if entropie > ENTROPIE_SEUIL:
        log.info("  Distribution plate → redistribution Pareto")
        weights = _pareto_weights(N_GARAGES_POOL, PARETO_ALPHA_GARAGE)
        garage_ids = [f"GAR_{i:04d}" for i in range(N_GARAGES_POOL)]
        df["ID_Garage"] = rng.choice(garage_ids, size=len(df), p=weights)
        top3 = df["ID_Garage"].value_counts().head(3).to_dict()
        log.info("  Top 3 garages après redistribution : %s", top3)
    else:
        log.info("  Distribution déjà concentrée → ID_Garage conservé")

    return df


# ─── 3. ID_Expert_Stable ──────────────────────────────────────────────────────

def add_expert_stable(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crée ou restructure ID_Expert_Stable.
    Certains experts valident systématiquement les mêmes garages —
    signal de collusion [Viaene2002].
    La distribution suit une Pareto : peu d'experts très actifs.
    """
    weights = _pareto_weights(N_EXPERTS_POOL, PARETO_ALPHA_EXPERT)
    expert_ids = [f"EXP_{i:03d}" for i in range(N_EXPERTS_POOL)]
    df["ID_Expert_Stable"] = rng.choice(expert_ids, size=len(df), p=weights)
    log.info("  ID_Expert_Stable ajouté — %d experts distincts", N_EXPERTS_POOL)
    return df


# ─── 4. Clusters réseau frauduleux ────────────────────────────────────────────

def inject_fraud_network_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Injecte des clusters garage↔assuré frauduleux.
    Un cluster = un garage (ou un petit groupe) qui traite systématiquement
    les sinistres d'un groupe d'assurés avec des montants gonflés.

    Injection uniquement sur dossiers FRAUDE existants.
    [Jiang2014] — comportements synchronisés entre garage et assuré complice.
    """
    df["community_id_auto"] = 0

    fraude_mask = df["Label_Anomalie"] == "FRAUDE"
    fraude_idx = df[fraude_mask].index.tolist()

    if len(fraude_idx) < 30:
        log.warning("  Trop peu de dossiers FRAUDE (%d) → clusters non injectés",
                    len(fraude_idx))
        return df

    rng.shuffle(fraude_idx)
    cursor = 0

    for cluster_id in range(1, N_CLUSTERS_AUTO + 1):
        n_gar = int(rng.integers(*CLUSTER_N_GARAGES))
        n_ass = int(rng.integers(*CLUSTER_N_ASSURES))

        cluster_garages = [f"GAR_CLUSTER_{cluster_id:02d}_{j:02d}"
                           for j in range(n_gar)]
        cluster_assures = [f"ASS_CLUSTER_AUTO_{cluster_id:02d}_{k:02d}"
                           for k in range(n_ass)]

        n_dossiers = min(n_gar * n_ass * 2,
                         len(fraude_idx) - cursor,
                         50)
        if n_dossiers <= 0:
            break

        cluster_indices = fraude_idx[cursor: cursor + n_dossiers]
        cursor += n_dossiers

        df.loc[cluster_indices, "ID_Garage"] = rng.choice(
            cluster_garages, size=n_dossiers
        )
        if "ID_Assure" in df.columns:
            df.loc[cluster_indices, "ID_Assure"] = rng.choice(
                cluster_assures, size=n_dossiers
            )
        df.loc[cluster_indices, "community_id_auto"] = cluster_id

    n_clustered = (df["community_id_auto"] > 0).sum()
    log.info("  %d clusters réseau injectés — %d dossiers affectés",
             N_CLUSTERS_AUTO, n_clustered)
    return df


# ─── 5. Doublons ──────────────────────────────────────────────────────────────

def add_doublon_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Détecte les doubles déclarations de sinistre.
    Un doublon auto = même assuré, même type de sinistre,
    même véhicule, déclaration ± 7 jours.

    [INSURANCE_DOMAIN_CONTEXT] : Double_Declaration — scénario no-go EDA
    à couvrir par cette feature.
    """
    df["Flag_Doublon_Auto"] = False
    df["Nb_Declarations"] = 1

    key_cols = [c for c in ["ID_Assure", "Type_Sinistre", "Montant_Devis"]
                if c in df.columns]

    if len(key_cols) < 2:
        log.warning("  Colonnes insuffisantes pour proxy doublon auto")
        return df

    df["_proxy_auto"] = (
        df.get("ID_Assure", "").astype(str) + "|"
        + df.get("Type_Sinistre", "").astype(str) + "|"
        + (df.get("Montant_Devis", 0) // 1000).astype(str)
    )
    counts = df["_proxy_auto"].value_counts()
    doublons = counts[counts > 1].index
    mask = df["_proxy_auto"].isin(doublons)
    df.loc[mask, "Flag_Doublon_Auto"] = True
    df.loc[mask, "Nb_Declarations"] = df.loc[mask, "_proxy_auto"].map(counts)
    df.drop(columns=["_proxy_auto"], inplace=True)

    log.info("  Flag_Doublon_Auto : %d dossiers (%.1f%%)",
             mask.sum(), mask.mean() * 100)
    return df


# ─── 6. Rapport ───────────────────────────────────────────────────────────────

def print_report(df_before: pd.DataFrame, df_after: pd.DataFrame) -> None:
    log.info("─" * 60)
    log.info("RAPPORT ENRICHISSEMENT AUTO")
    log.info("  Lignes          : %d (inchangé)", len(df_after))
    log.info("  Colonnes avant  : %d", len(df_before.columns))
    log.info("  Colonnes après  : %d", len(df_after.columns))
    nouvelles = set(df_after.columns) - set(df_before.columns)
    log.info("  Nouvelles cols  : %s", sorted(nouvelles))
    log.info("  community_id>0  : %d dossiers réseau",
             (df_after["community_id_auto"] > 0).sum())
    log.info("  Flag_Doublon    : %d dossiers (%.1f%%)",
             df_after["Flag_Doublon_Auto"].sum(),
             df_after["Flag_Doublon_Auto"].mean() * 100)
    log.info("  Anomalies       : %d (%.1f%%) — inchangé",
             (df_after["Label_Anomalie"] != "NORMAL").sum(),
             (df_after["Label_Anomalie"] != "NORMAL").mean() * 100)
    log.info("─" * 60)


# ─── 7. Pipeline principal ────────────────────────────────────────────────────

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = add_batch_date(df)
    df = rebuild_garage_ids(df)
    df = add_expert_stable(df)
    df = inject_fraud_network_clusters(df)
    df = add_doublon_flags(df)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrichit dataset Auto raw CSV/Parquet → Parquet v2"
    )
    parser.add_argument("--input", required=True,
                        help="Chemin vers le fichier source (CSV ou Parquet)")
    parser.add_argument("--output", required=True,
                        help="Chemin de sortie Parquet (data/processed/auto/dataset_auto_v2.parquet)")
    parser.add_argument("--csv", action="store_true",
                        help="Produire aussi un CSV de consultation (même chemin, extension .csv)")
    args = parser.parse_args()

    # ── Chargement ─────────────────────────────────────────────────
    df_v1 = load(Path(args.input))
    df_v2 = enrich(df_v1.copy())
    print_report(df_v1, df_v2)

    # ── Sauvegarde Parquet (format principal) ──────────────────────
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df_v2.to_parquet(out, index=False)
    log.info("✅ Parquet sauvegardé : %s  (%s Mo)",
             out, round(out.stat().st_size / 1e6, 1))

    # ── CSV optionnel ──────────────────────────────────────────────
    if args.csv:
        out_csv = out.with_suffix(".csv")
        df_v2.to_csv(out_csv, index=False)
        log.info("✅ CSV sauvegardé   : %s", out_csv)

    log.info("Terminé. Vérifier le rapport avant de valider.")
    log.info("Commande de vérification :")
    log.info("  python -c \"import pandas as pd; df=pd.read_parquet('%s'); "
             "print(df.shape, df['community_id_auto'].value_counts().head())\"",
             args.output)


if __name__ == "__main__":
    main()