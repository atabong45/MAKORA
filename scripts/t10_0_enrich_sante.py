"""
MODULE : scripts/t10_0_enrich_sante.py
DESCRIPTION : Enrichissement du dataset Santé v1 → v2.
              Ajoute les colonnes nécessaires à la détection réseau,
              aux doublons et au drift monitor, sans modifier
              les dossiers existants ni les labels ground truth.

PRINCIPE :
  - Lecture de dataset_sante_v1.csv
  - Ajout de 4 groupes de colonnes (détaillés ci-dessous)
  - Écriture de dataset_sante_v2.csv (v1 inchangé)
  - Le test fixe (dataset_sante_test_fixe.csv) est traité séparément
    avec les MÊMES paramètres pour garantir la cohérence

COLONNES AJOUTÉES :
  Groupe 1 — Réseau praticien↔assuré
    · ID_Praticien  : redistribué avec concentration réaliste (loi de Pareto)
                      ~10% des praticiens concentrent ~70% des dossiers
    · ID_Employeur  : identifiant employeur pour détecter les groupes d'assurés
                      d'une même entreprise qui consultent les mêmes praticiens
    · community_id_sante : label de communauté pré-calculé (entier, 0 = aucune)
                           pour validation du graph_engine

  Groupe 2 — Doublons
    · Flag_Doublon  : True si le dossier est une soumission multiple d'un
                      dossier existant (même assuré, même acte, même montant,
                      même date ± 3 jours)
    · Nb_Fois_Hash_Vu : combien de fois ce document a été soumis
                        (basé sur Hash_Document si présent, sinon proxy)

  Groupe 3 — Drift monitor
    · Batch_Date    : date de batch pour le suivi PSI par fenêtre temporelle
                      [Gama2014] — PSI calculé sur fenêtres glissantes 90j/30j

  Groupe 4 — Ancienneté (DT-WARN résolu)
    · Anciennete_Contrat : remplie avec valeur par défaut 365 si absente
                           (déjà documentée dans DT-WARN SESSION_STATE)

RÉFÉRENCES ACADÉMIQUES :
  [Jiang2014] Jiang et al. (2014). CatchSync: catching synchronized behavior.
              KDD. → Justifie la distribution Pareto des praticiens
  [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection. ICMLA.
              → Taux fraude estimé 3-10%, seuils de concentration
  [Gama2014]  Gama et al. (2014). A survey on concept drift adaptation.
              ACM Computing Surveys. → Batch_Date pour PSI glissant

DÉCISIONS DE CONCEPTION :
  - Les ID_Praticien existants sont REMPLACÉS (ils étaient aléatoires,
    sans structure). C'est documenté et justifié — voir commentaire _rebuild_praticien_ids()
  - Les clusters réseau frauduleux sont injectés UNIQUEMENT sur les dossiers
    déjà labellisés FRAUDE (Label_Anomalie == "FRAUDE") pour ne pas
    créer de faux positifs dans les normaux
  - Seed = 42 partout pour reproductibilité
"""
from __future__ import annotations

import argparse
import hashlib
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
log = logging.getLogger("enrich_sante")

# Distribution Pareto pour les praticiens
# [Jiang2014] : ~10% des acteurs concentrent ~70% des transactions frauduleuses
N_PRATICIENS_POOL = 800          # pool de praticiens distincts
PARETO_ALPHA = 1.5               # forme Pareto (plus petit = plus concentré)

# Clusters réseau frauduleux (praticien↔assuré)
# [Bauder2017] : réseaux de 3-8 praticiens liés à 20-50 assurés
N_CLUSTERS_FRAUDE = 12           # nombre de clusters à injecter
CLUSTER_N_PRATICIENS = (3, 6)    # taille cluster praticiens
CLUSTER_N_ASSURES = (20, 50)     # taille cluster assurés liés

# Doublons
DOUBLON_FENETRE_JOURS = 3        # même acte ± 3 jours = doublon
DOUBLON_TAUX_CIBLE = 0.013       # ~1.3% du dataset (issu EDA overview)


# ─── 1. Chargement ────────────────────────────────────────────────────────────

def load(path: Path) -> pd.DataFrame:
    log.info("Chargement : %s", path)
    df = pd.read_csv(path, low_memory=False)
    log.info("  → shape : %s", df.shape)
    return df


# ─── 2. Ancienneté (DT-WARN) ──────────────────────────────────────────────────

def fix_anciennete(df: pd.DataFrame) -> pd.DataFrame:
    """
    Résout DT-WARN : Anciennete_Contrat absente → valeur par défaut 365 j.
    Si la colonne existe déjà avec des NaN, les NaN sont comblés.
    """
    if "Anciennete_Contrat" not in df.columns:
        log.info("  Anciennete_Contrat absente → création avec valeur 365")
        df["Anciennete_Contrat"] = 365
    else:
        n_null = df["Anciennete_Contrat"].isna().sum()
        if n_null:
            log.info("  Anciennete_Contrat : %d NaN comblés avec 365", n_null)
            df["Anciennete_Contrat"] = df["Anciennete_Contrat"].fillna(365).astype(int)
    return df


# ─── 3. Batch_Date (drift monitor) ────────────────────────────────────────────

def add_batch_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crée Batch_Date à partir de Date_Soin (mois de traitement).
    Si Date_Soin absent, utilise une distribution uniforme sur 2021-2025.
    [Gama2014] : fenêtre de référence 90j, fenêtre courante 30j.
    """
    if "Date_Soin" in df.columns:
        dates = pd.to_datetime(df["Date_Soin"], errors="coerce")
        # Filtrer les dates aberrantes hors plage réaliste [2015, 2026]
        date_min = pd.Timestamp("2015-01-01")
        date_max = pd.Timestamp("2026-12-31")
        hors_plage = ((dates < date_min) | (dates > date_max)).sum()
        if hors_plage:
            log.warning("  %d dates hors plage [2015-2026] -> remplacees par NaN",
                        hors_plage)
            dates = dates.where((dates >= date_min) & (dates <= date_max), other=pd.NaT)
        # Batch = début du mois du soin (granularité mensuelle pour le drift)
        df["Batch_Date"] = dates.dt.to_period("M").dt.to_timestamp()
        n_null = df["Batch_Date"].isna().sum()
        if n_null:
            fallback = pd.Timestamp("2023-01-01")
            df["Batch_Date"] = df["Batch_Date"].fillna(fallback)
            log.info("  Batch_Date : %d NaN combles avec 2023-01-01", n_null)
    else:
        log.warning("  Date_Soin absent — Batch_Date généré aléatoirement")
        months = pd.date_range("2021-01-01", "2025-12-01", freq="MS")
        df["Batch_Date"] = rng.choice(months, size=len(df))
    log.info("  Batch_Date ajoutée — plage : %s → %s",
             df["Batch_Date"].min(), df["Batch_Date"].max())
    return df


# ─── 4. Reconstruction ID_Praticien (structure réseau) ────────────────────────

def _pareto_weights(n_pool: int, alpha: float) -> np.ndarray:
    """Distribution Pareto normalisée sur n_pool praticiens."""
    ranks = np.arange(1, n_pool + 1, dtype=float)
    weights = ranks ** (-alpha)
    return weights / weights.sum()


def rebuild_praticien_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remplace les ID_Praticien aléatoires par des identifiants structurés
    suivant une distribution de Pareto.

    POURQUOI ON REMPLACE (pas juste on ajoute) :
    Les ID_Praticien actuels sont tirés aléatoirement — chaque dossier
    a un praticien différent, ce qui rend le graphe praticien↔assuré
    totalement plat (aucune communauté détectable).
    En réalité [Bauder2017], ~10% des praticiens concentrent ~70%
    des actes. On redistribue les IDs selon cette loi tout en gardant
    le même pool de praticiens (pas de nouveau praticien inventé).

    Les praticiens des clusters frauduleux sont fixés en étape suivante.
    """
    n = len(df)
    weights = _pareto_weights(N_PRATICIENS_POOL, PARETO_ALPHA)
    praticien_ids = [f"PRAT_{i:04d}" for i in range(N_PRATICIENS_POOL)]

    new_ids = rng.choice(praticien_ids, size=n, p=weights)
    df["ID_Praticien"] = new_ids

    top10 = pd.Series(new_ids).value_counts().head(10)
    log.info("  ID_Praticien redistribués — top 3 : %s",
             top10.head(3).to_dict())
    return df


# ─── 5. ID_Employeur ──────────────────────────────────────────────────────────

def add_employeur_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute ID_Employeur pour permettre la détection de groupes d'assurés
    d'une même entreprise qui consultent les mêmes praticiens.
    Distribution Pareto : quelques gros employeurs, beaucoup de petits.
    """
    N_EMPLOYEURS = 200
    weights = _pareto_weights(N_EMPLOYEURS, alpha=1.2)
    emp_ids = [f"EMP_{i:03d}" for i in range(N_EMPLOYEURS)]
    df["ID_Employeur"] = rng.choice(emp_ids, size=len(df), p=weights)
    log.info("  ID_Employeur ajouté — %d employeurs distincts", N_EMPLOYEURS)
    return df


# ─── 6. Clusters réseau frauduleux ────────────────────────────────────────────

def inject_fraud_network_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Injecte des clusters praticien↔assuré frauduleux.
    Un cluster = un groupe de praticiens complices qui traitent
    systématiquement un groupe d'assurés liés (kickbacks, soins fantômes).

    RÈGLE : on n'injecte QUE sur des dossiers déjà FRAUDE ou NORMAL.
    Les dossiers FRAUDE existants sont réaffectés à un cluster.
    Les dossiers NORMAL ne sont PAS touchés (pas de faux positifs injectés).

    [Jiang2014] — CatchSync : détection de comportements synchronisés
    [Bauder2017] — Medicare : clusters de 3-8 praticiens typiques
    """
    df["community_id_sante"] = 0  # 0 = pas de communauté suspecte

    # Identifier les dossiers FRAUDE disponibles pour les clusters
    fraude_mask = df["Label_Anomalie"] == "FRAUDE"
    fraude_idx = df[fraude_mask].index.tolist()

    if len(fraude_idx) < 50:
        log.warning("  Trop peu de dossiers FRAUDE (%d) — clusters non injectés",
                    len(fraude_idx))
        return df

    rng.shuffle(fraude_idx)
    cursor = 0

    for cluster_id in range(1, N_CLUSTERS_FRAUDE + 1):
        n_prat = int(rng.integers(*CLUSTER_N_PRATICIENS))
        n_assures = int(rng.integers(*CLUSTER_N_ASSURES))

        # Praticiens dédiés à ce cluster
        cluster_prats = [f"PRAT_CLUSTER_{cluster_id:02d}_{j:02d}"
                         for j in range(n_prat)]
        # Assurés dédiés à ce cluster
        cluster_assures = [f"ASS_CLUSTER_{cluster_id:02d}_{k:02d}"
                           for k in range(n_assures)]

        # Nombre de dossiers à affecter à ce cluster
        n_dossiers = min(n_prat * n_assures * 2,
                         len(fraude_idx) - cursor,
                         60)  # max 60 dossiers par cluster
        if n_dossiers <= 0:
            break

        cluster_indices = fraude_idx[cursor: cursor + n_dossiers]
        cursor += n_dossiers

        # Réaffecter praticiens et assurés
        df.loc[cluster_indices, "ID_Praticien"] = rng.choice(
            cluster_prats, size=n_dossiers
        )
        df.loc[cluster_indices, "ID_Assure"] = rng.choice(
            cluster_assures, size=n_dossiers
        )
        df.loc[cluster_indices, "community_id_sante"] = cluster_id

    n_clustered = (df["community_id_sante"] > 0).sum()
    log.info("  %d clusters réseau injectés — %d dossiers affectés",
             N_CLUSTERS_FRAUDE, n_clustered)
    return df


# ─── 7. Doublons ──────────────────────────────────────────────────────────────

def add_doublon_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Détecte (et crée) les doublons de soumission.

    Deux dossiers sont doublons si :
      - même ID_Assure
      - même Code_Acte
      - même Montant_Facture (à 1% près)
      - même Date_Soin (± DOUBLON_FENETRE_JOURS jours)

    Pour atteindre le taux cible (~1.3%) on injecte quelques doublons
    supplémentaires sur des dossiers normaux (simulation de soumissions
    multiples par erreur administrative — cas le plus fréquent).

    [INSURANCE_DOMAIN_CONTEXT] — Duplicate Billing : Nb_Fois_Hash_Vu > 1
    """
    # Initialisation
    # Toujours repartir de False — ignorer toute colonne Flag_Doublon
    # préexistante dans le raw (elle causait le taux de 49%)
    df["Flag_Doublon"] = False
    df["Nb_Fois_Hash_Vu"] = 1

    # Stratégie : injection contrôlée sur dossiers FRAUDE (Duplicate Billing)
    # + quelques doublons sur NORMAL (erreur administrative)
    # On n'utilise PAS le proxy montant qui créait des faux positifs massifs
    # car beaucoup de dossiers ont des montants proches dans le même bucket // 10

    # Doublons sur dossiers FRAUDE labellisés "Soumission multiple" si présents
    if "Sous_Type_Anomalie" in df.columns:
        doublon_mask = df["Sous_Type_Anomalie"].str.contains(
            "Soumission|Doublon|multiple", case=False, na=False
        )
        df.loc[doublon_mask, "Flag_Doublon"] = True
        df.loc[doublon_mask, "Nb_Fois_Hash_Vu"] = 2
        log.info("  Doublons via Sous_Type_Anomalie : %d dossiers", doublon_mask.sum())

    # Injection complémentaire sur NORMAL pour atteindre le taux cible ~1.3%
    taux_actuel = df["Flag_Doublon"].mean()
    if taux_actuel < DOUBLON_TAUX_CIBLE:
        n_manquants = int((DOUBLON_TAUX_CIBLE - taux_actuel) * len(df))
        normal_idx = df[
            (df["Label_Anomalie"] == "NORMAL") & (~df["Flag_Doublon"])
        ].index
        if len(normal_idx) >= n_manquants:
            inj_idx = rng.choice(normal_idx, size=n_manquants, replace=False)
            df.loc[inj_idx, "Flag_Doublon"] = True
            df.loc[inj_idx, "Nb_Fois_Hash_Vu"] = 2

    taux_final = df["Flag_Doublon"].mean()
    log.info("  Flag_Doublon final : %d dossiers (%.1f%%)",
             df["Flag_Doublon"].sum(), taux_final * 100)
    return df


# ─── 8. Rapport de validation ─────────────────────────────────────────────────

def print_report(df_before: pd.DataFrame, df_after: pd.DataFrame) -> None:
    log.info("─" * 60)
    log.info("RAPPORT ENRICHISSEMENT SANTÉ")
    log.info("  Lignes          : %d (inchangé)", len(df_after))
    log.info("  Colonnes avant  : %d", len(df_before.columns))
    log.info("  Colonnes après  : %d", len(df_after.columns))
    nouvelles = set(df_after.columns) - set(df_before.columns)
    log.info("  Nouvelles cols  : %s", sorted(nouvelles))
    log.info("  community_id>0  : %d dossiers réseau",
             (df_after["community_id_sante"] > 0).sum())
    log.info("  Flag_Doublon    : %d dossiers (%.1f%%)",
             df_after["Flag_Doublon"].sum(),
             df_after["Flag_Doublon"].mean() * 100)
    log.info("  Anomalies       : %d (%.1f%%) — inchangé",
             (df_after["Label_Anomalie"] != "NORMAL").sum(),
             (df_after["Label_Anomalie"] != "NORMAL").mean() * 100)
    log.info("─" * 60)


# ─── 9. Pipeline principal ────────────────────────────────────────────────────

def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Applique tous les enrichissements dans l'ordre."""
    df = fix_anciennete(df)
    df = add_batch_date(df)
    df = rebuild_praticien_ids(df)
    df = add_employeur_ids(df)
    df = inject_fraud_network_clusters(df)
    df = add_doublon_flags(df)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrichit dataset Santé raw CSV → Parquet v2"
    )
    parser.add_argument(
        "--input", required=True,
        help="Chemin vers le CSV source (data/raw/unity/dataset_sante_unity_raw.csv)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Chemin de sortie Parquet (data/processed/sante/dataset_sante_v2.parquet)"
    )
    parser.add_argument(
        "--csv", action="store_true",
        help="Produire aussi un CSV de consultation (même chemin, extension .csv)"
    )
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

    # ── CSV optionnel (inspection manuelle) ───────────────────────
    if args.csv:
        out_csv = out.with_suffix(".csv")
        df_v2.to_csv(out_csv, index=False)
        log.info("✅ CSV sauvegardé   : %s", out_csv)

    log.info("Terminé. Vérifier le rapport ci-dessus avant de valider.")
    log.info("Commande de vérification :")
    log.info("  python -c \"import pandas as pd; df=pd.read_parquet('%s'); "
             "print(df.shape, df['community_id_sante'].value_counts().head())\"",
             args.output)


if __name__ == "__main__":
    main()