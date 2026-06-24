"""
MODULE : modules/sante/features.py
DESCRIPTION : Fonctions de feature engineering V1 pour le module Santé MAKORA.
              Séparé de sante_module.py pour respecter la limite IMP-007 (< 400 lignes)
              et faciliter les tests unitaires indépendants.

              PRINCIPE YAML-DRIVEN (Scénarios A→C) :
              Ce fichier expose FEATURE_FUNCTIONS_SANTE_V1, un dict ordonné
              importé par SanteModule.engineer_features(). Ajouter ou renommer
              une feature V1 ne nécessite plus de modifier sante_module.py :
              seul ce fichier et sante.yaml doivent être mis à jour.

              Ordre du dict = ordre de calcul garanti :
              ratio_prix_mercuriale DOIT précéder historique_ratio_praticien
              car ce dernier lit la colonne ratio_prix_mercuriale du DataFrame.

RÉFÉRENCES ACADÉMIQUES :
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection using
  machine learning methods. ICMLA.
  → Justifie ratio_prix_mercuriale, flag_incoherence_sexe_acte et
    is_weekend_event comme features discriminantes de fraude santé.
- [Viaene2002] Viaene et al. (2002). Automobile insurance fraud detection.
  Journal of Risk and Insurance.
  → Justifie l'analyse de fréquence (nb_sinistres_30j) comme signal fraude.
- [Subudhi2017] Subudhi & Panigrahi (2017). Automobile insurance fraud.
  Journal of King Saud University.
  → Historique praticien (historique_ratio_praticien) : signal de fraude
    coordonnée ou de comportement systématique anormal d'un prestataire.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Toutes les fonctions sont STATELESS — pas de state global ni de boucle
    Python sur les lignes. Robustesse via dégradation gracieuse.

DÉCISIONS DE CONCEPTION :
- Toutes les fonctions sont STATELESS et opèrent sur le batch courant.
  Un référentiel praticien persistant sera ajouté en Phase 2 (ADR futur).
- Les colonnes manquantes sont gérées silencieusement (valeur neutre + log)
  plutôt que par exception [Sculley2015].
- La nomenclature des actes suit l'ASAC camerounais, pas la CCAM française.
  Les prix de référence sont issus de la mercuriale CIMA (XAF).
- compute_flag_weekend_care conserve son nom interne pour la compatibilité
  avec les tests existants ; la clé exposée dans FEATURE_FUNCTIONS_SANTE_V1
  est 'is_weekend_event' (harmonisation M_makora_dif, Scénario A).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Référentiels ASAC (nomenclature camerounaise — mercuriale CIMA)
# [Bauder2017] : l'incohérence sexe/acte est un signal fort d'usurpation
# ---------------------------------------------------------------------------
_ACTES_FEMININS: frozenset[str] = frozenset({
    "GYNECO_001", "GYNECO_002", "GYNECO_003",
    "OBSTET_001", "OBSTET_002", "OBSTET_003",
    "MAMMO_001", "MAMMO_002",
    "CERVI_001", "CERVI_002",
})

_ACTES_MASCULINS: frozenset[str] = frozenset({
    "PROSTA_001", "PROSTA_002",
    "ANDRO_001", "ANDRO_002",
})


# ---------------------------------------------------------------------------
# Feature 1 — ratio_prix_mercuriale
# DOIT être calculée en premier : utilisée par compute_historique_ratio_praticien
# ---------------------------------------------------------------------------

def compute_ratio_prix_mercuriale(df: pd.DataFrame) -> pd.Series:
    """
    Ratio prix facturé / prix de référence mercuriale CIMA.

    [Bauder2017] : un ratio > 1.5 est le seuil discriminant principal
    pour la surfacturation dans les études de fraude santé.

    Valeur neutre = 1.0 si Prix_Unitaire_Ref est absent ou nul.
    Cap à 50.0 pour éviter que les outliers extrêmes saturent SHAP
    [Lundberg2017].

    Args:
        df: DataFrame avec colonnes Montant_Facture et Prix_Unitaire_Ref.

    Returns:
        pd.Series nommée 'ratio_prix_mercuriale'.
    """
    required = {"Montant_Facture", "Prix_Unitaire_Ref"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        logger.warning("compute_ratio_prix_mercuriale — colonnes manquantes %s → ratio=1.0", missing)
        return pd.Series(1.0, index=df.index, name="ratio_prix_mercuriale")

    ref = pd.to_numeric(df["Prix_Unitaire_Ref"], errors="coerce").replace(0.0, np.nan)
    facture = pd.to_numeric(df["Montant_Facture"], errors="coerce")

    # [Bauder2017] : cap à 50x — au-delà, la valeur exacte est sans intérêt
    ratio = (facture / ref).fillna(1.0).clip(lower=0.0, upper=50.0)
    return ratio.rename("ratio_prix_mercuriale")


# ---------------------------------------------------------------------------
# Feature 2 — flag_incoherence_sexe_acte
# ---------------------------------------------------------------------------

def compute_flag_incoherence_sexe_acte(df: pd.DataFrame) -> pd.Series:
    """
    Flag binaire : acte médical incompatible avec le sexe déclaré.

    [Bauder2017] : l'incohérence sexe/acte est un signal d'usurpation
    d'identité ou de prêt de carte d'assuré (phantom billing).
    0 = cohérent ou inconnu, 1 = incohérence détectée.

    Args:
        df: DataFrame avec colonnes Code_Acte et Sexe_Assure.

    Returns:
        pd.Series nommée 'flag_incoherence_sexe_acte' (int 0/1).
    """
    required = {"Code_Acte", "Sexe_Assure"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        logger.warning("compute_flag_incoherence_sexe_acte — colonnes manquantes %s → flag=0", missing)
        return pd.Series(0, index=df.index, dtype=int, name="flag_incoherence_sexe_acte")

    sexe = df["Sexe_Assure"].astype(str).str.strip().str.upper()
    acte = df["Code_Acte"].astype(str).str.strip().str.upper()

    flag = pd.Series(0, index=df.index, dtype=int)
    # Homme avec acte féminin
    flag = flag.where(~((sexe == "M") & acte.isin(_ACTES_FEMININS)), other=1)
    # Femme avec acte masculin
    flag = flag.where(~((sexe == "F") & acte.isin(_ACTES_MASCULINS)), other=1)
    return flag.rename("flag_incoherence_sexe_acte")


# ---------------------------------------------------------------------------
# Feature 3 — historique_ratio_praticien
# Dépend de ratio_prix_mercuriale — calculée après Feature 1
# ---------------------------------------------------------------------------

def compute_historique_ratio_praticien(df: pd.DataFrame) -> pd.Series:
    """
    Ratio moyen du praticien sur le batch courant.

    [Subudhi2017] : l'historique d'un prestataire est un prédicteur
    de fraude coordonnée. Un praticien avec un ratio moyen élevé sur
    l'ensemble du batch est suspect même si chaque dossier pris
    individuellement semble raisonnable.

    PRÉCONDITION : ratio_prix_mercuriale doit être présent dans df.
    Cela est garanti par l'ordre de FEATURE_FUNCTIONS_SANTE_V1.

    Note : calcul STATELESS sur le batch. Un référentiel persistant
    sera ajouté en Phase 2 pour capturer l'historique inter-batches.
    [Sculley2015] : dette technique documentée DT-002.

    Args:
        df: DataFrame avec colonnes ID_Praticien et ratio_prix_mercuriale.

    Returns:
        pd.Series nommée 'historique_ratio_praticien'.
    """
    required = {"ID_Praticien", "ratio_prix_mercuriale"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        logger.warning("compute_historique_ratio_praticien — colonnes manquantes %s → ratio=1.0", missing)
        return pd.Series(1.0, index=df.index, name="historique_ratio_praticien")

    mean_ratio = df.groupby("ID_Praticien")["ratio_prix_mercuriale"].transform("mean")
    return mean_ratio.fillna(1.0).rename("historique_ratio_praticien")


# ---------------------------------------------------------------------------
# Feature 4 — nb_sinistres_30j_assure
# ---------------------------------------------------------------------------

def compute_nb_sinistres_30j(df: pd.DataFrame) -> pd.Series:
    """
    Nombre de sinistres dans les 30 derniers jours pour chaque assuré.

    [Viaene2002] : la fréquence anormale de sinistres est le signal
    primaire de fraude à la fréquence (unbundling, soins fictifs répétés).

    Algorithme : pour chaque assuré, comptage par fenêtre glissante
    sur le batch trié par date. Complexité O(k² * A) où k = sinistres
    par assuré et A = nombre d'assurés — acceptable en batch.

    Args:
        df: DataFrame avec colonnes ID_Assure et Date_Soin.

    Returns:
        pd.Series nommée 'nb_sinistres_30j_assure' (int).
    """
    required = {"ID_Assure", "Date_Soin"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        logger.warning("compute_nb_sinistres_30j — colonnes manquantes %s → nb=1", missing)
        return pd.Series(1, index=df.index, dtype=int, name="nb_sinistres_30j_assure")

    dates = pd.to_datetime(df["Date_Soin"], errors="coerce")
    result = pd.Series(1, index=df.index, dtype=int)
    window = np.timedelta64(30, "D")

    df_work = pd.DataFrame({
        "ID_Assure": df["ID_Assure"].values,
        "date": dates.values,
        "orig_idx": df.index,
    })

    for _, grp in df_work.groupby("ID_Assure"):
        dates_arr = grp["date"].values
        orig_idx = grp["orig_idx"].values
        counts = []
        for i, d in enumerate(dates_arr):
            if pd.isna(d):
                counts.append(1)
                continue
            valid = ~pd.isna(dates_arr)
            cnt = int(np.sum(valid & (dates_arr >= d - window) & (dates_arr <= d)))
            counts.append(max(cnt, 1))
        result.loc[orig_idx] = counts

    return result.rename("nb_sinistres_30j_assure")


# ---------------------------------------------------------------------------
# Feature 5 — is_weekend_event  (★ COMMUN M_makora_dif)
# Nom interne de la fonction conservé pour rétrocompatibilité des tests.
# La clé exposée dans FEATURE_FUNCTIONS_SANTE_V1 est 'is_weekend_event'.
# ---------------------------------------------------------------------------

def compute_flag_weekend_care(df: pd.DataFrame) -> pd.Series:
    """
    Flag binaire : soin effectué un samedi (5) ou dimanche (6).

    Feature commune ★ avec AutoModule (is_weekend_event) pour M_makora_dif.
    [Bauder2017] : les soins du weekend sont statistiquement associés
    à la fraude dans les contextes où les cabinets sont fermés —
    facturation fictive ou antidatage de soins (phantom billing).
    0 = jour de semaine, 1 = weekend.

    Note sur le nommage : la fonction s'appelle compute_flag_weekend_care
    pour préserver la rétrocompatibilité des tests unitaires ; la Series
    retournée et la clé de FEATURE_FUNCTIONS_SANTE_V1 sont 'is_weekend_event'
    (harmonisation Scénario A — [Xu2023] M_makora_dif).

    Args:
        df: DataFrame avec colonne Date_Soin.

    Returns:
        pd.Series nommée 'is_weekend_event' (int 0/1).
    """
    if "Date_Soin" not in df.columns:
        logger.warning("compute_flag_weekend_care — colonne Date_Soin manquante → flag=0")
        return pd.Series(0, index=df.index, dtype=int, name="is_weekend_event")

    dates = pd.to_datetime(df["Date_Soin"], errors="coerce")
    flag = dates.dt.dayofweek.isin([5, 6]).astype(int)
    return flag.fillna(0).astype(int).rename("is_weekend_event")


# ===========================================================================
# Registre V1 — utilisé par SanteModule.engineer_features()
#
# PRINCIPE YAML-DRIVEN : SanteModule itère ce dict au lieu d'appeler les
# fonctions explicitement. Ajouter une feature V1 = ajouter une entrée ici
# + déclarer le nom dans sante.yaml. Aucune modification de sante_module.py.
#
# ORDRE CRITIQUE :
#   1. ratio_prix_mercuriale      — calcul en premier (dépendance aval)
#   2. flag_incoherence_sexe_acte — indépendant
#   3. historique_ratio_praticien — LIT ratio_prix_mercuriale depuis df
#   4. nb_sinistres_30j_assure    — indépendant
#   5. is_weekend_event           — indépendant
#
# L'ordre d'insertion du dict Python 3.7+ est garanti stable à l'itération.
# [Sculley2015] : l'ordre de calcul fait partie du contrat du pipeline.
# ===========================================================================

FEATURE_FUNCTIONS_SANTE_V1: dict[str, callable] = {
    "ratio_prix_mercuriale":      compute_ratio_prix_mercuriale,       # V1.1 — PREMIER (dép. aval)
    "flag_incoherence_sexe_acte": compute_flag_incoherence_sexe_acte,  # V1.2
    "historique_ratio_praticien": compute_historique_ratio_praticien,  # V1.3 — après ratio
    "nb_sinistres_30j_assure":    compute_nb_sinistres_30j,            # V1.4
    "is_weekend_event":           compute_flag_weekend_care,           # V1.5 ★ COMMUN (Scénario A)
}
"""
Registre des 5 fonctions V1 du module Santé dans leur ordre de calcul.
Clé = nom de feature tel que déclaré dans sante.yaml (section features).
Valeur = fonction callable(df) -> pd.Series.

Importé par SanteModule.engineer_features() pour une itération YAML-driven
sans hardcoder les noms de features dans le module.
"""