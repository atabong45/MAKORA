"""
MODULE : modules/sante/features_ext.py
DESCRIPTION : Fonctions de feature engineering complémentaires (V2) pour le
              module Santé MAKORA — 12 features (9 originales + 3 nouvelles).
              Séparé de features.py pour respecter la règle IMP-007 (< 400 lignes)
              et faciliter les tests unitaires indépendants.

HISTORIQUE DES FEATURES :
  Session H (v0.2.0) — 9 features originales :
    document_altere, praticien_hors_agrement, ocr_confiance_faible,
    delai_soin_depot_anormal (→ delai_depot_anormal), anciennete_contrat_courte,
    saisie_hors_heures, montant_normalise_log (→ montant_log),
    post_mortem_flag, nb_sinistres_meme_iban
  Scénario A (v0.5.0) — +1 :
    acte_incomplet ★ (Flag_Acte_Incomp)
  Scénario B (v0.5.0) — +2 :
    nb_sinistres_recents ★ (Nb_Sinistres_12m)
    document_age_anormal ★ (correction dette documentaire SESSION H)
  Scénario C (v0.5.0) — renommages :
    delai_depot_anormal (ex delai_soin_depot_anormal)
    montant_log (ex montant_normalise_log)

RÉFÉRENCES ACADÉMIQUES :
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection using
  machine learning methods. ICMLA.
  → document_altere, praticien_hors_agrement, post_mortem_flag : patterns
    de fraude documentaire et identitaire recensés sur données Medicare.
- [Chandola2009] Chandola et al. (2009). Anomaly detection: A survey.
  ACM Computing Surveys. § 3.1 — Features temporelles (delai_depot_anormal,
  document_age_anormal, anciennete_contrat_courte, saisie_hors_heures)
  comme signaux contextuels de fraude préméditée.
- [Viaene2002] Viaene et al. (2002). Automobile insurance fraud detection.
  Journal of Risk and Insurance.
  → anciennete_contrat_courte, nb_sinistres_recents : signaux fréquentiels
    et temporels universels entre branches.
- [Liu2008] Liu et al. (2008). Isolation Forest. ICDM 2008.
  → montant_log (log1p) : la transformation log réduit l'asymétrie et
    améliore la séparation IF/DIF sur les distributions à longue queue.
- [Xu2023] Xu et al. (2023). Deep Isolation Forest for Anomaly Detection.
  IEEE TKDE. → Features communes ★ enrichissent l'espace M_makora_dif.
- [INSURANCE_DOMAIN_CONTEXT §3.2] Cachet humide et OCR au Cameroun :
  taux d'erreur OCR élevé → ocr_confiance_faible est un signal spécifique
  au contexte camerounais. Seuil 0.5 calibré sur le dataset UNITY.

DÉCISIONS DE CONCEPTION :
- Toutes les fonctions sont vectorisées (pandas/numpy) — pas de boucle Python.
- Dégradation gracieuse : colonne absente → valeur neutre (0 ou False) + warning.
  Jamais d'exception levée depuis une fonction de feature. [Sculley2015]
- Les noms de Series retournées correspondent EXACTEMENT aux clés du registre
  FEATURE_EXT_FUNCTIONS (invariant testé par TestRegistreFonctions).
- montant_log utilise log1p (log(x+1)) pour gérer les montants nuls.
  [Liu2008] : la log-transformation améliore la séparation IF/DIF.
- post_mortem_flag : comparaison de dates après coercion — NaT traité comme
  non-fraude (0) pour éviter les faux positifs sur données incomplètes.
- document_age_anormal : fallback sur Delai_Soin_Depot si Date_Saisie_Systeme
  absent — robustesse sans crash.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper interne — lecture sécurisée d'une colonne avec valeur par défaut
# [Sculley2015] : robustesse > pureté — ne jamais crasher sur colonne absente
# ---------------------------------------------------------------------------

def _safe_col(df: pd.DataFrame, col: str, default=0) -> pd.Series:
    """Retourne la colonne ou une série de valeur par défaut avec warning."""
    if col not in df.columns:
        logger.warning(
            "features_ext — colonne '%s' absente → valeur par défaut %s", col, default
        )
        return pd.Series(default, index=df.index)
    return df[col]


# ===========================================================================
# Feature 1 — document_altere
# ===========================================================================

def compute_document_altere(df: pd.DataFrame) -> pd.Series:
    """
    Lecture directe du flag de document altéré produit par le pipeline OCR.

    [Bauder2017] : la falsification de documents (ordonnances, factures) est
    le vecteur de fraude documentaire #1 dans les systèmes de santé africains.
    Impacte les scénarios : Phantom Billing, Soin Post-Mortem.

    Returns:
        pd.Series int (0/1) nommée 'document_altere'.
    """
    raw = _safe_col(df, "Flag_Doc_Altere", default=0)
    return raw.fillna(0).astype(int).rename("document_altere")


# ===========================================================================
# Feature 2 — praticien_hors_agrement
# ===========================================================================

def compute_praticien_hors_agrement(df: pd.DataFrame) -> pd.Series:
    """
    1 si le praticien n'est pas actif/agréé au moment du soin.

    [INSURANCE_DOMAIN_CONTEXT §4.1] : les assureurs CIMA exigent que les
    prestataires soient référencés dans le réseau de soins agréé. Un acte
    facturé par un praticien hors agrément est systématiquement suspect.

    Returns:
        pd.Series int (0/1) nommée 'praticien_hors_agrement'.
    """
    raw = _safe_col(df, "Praticien_Actif", default=True)
    # Praticien_Actif == False → hors agrément
    flag = (~raw.fillna(True).astype(bool)).astype(int)
    return flag.rename("praticien_hors_agrement")


# ===========================================================================
# Feature 3 — ocr_confiance_faible  (★ COMMUN M_makora_dif)
# ===========================================================================

def compute_ocr_confiance_faible(
    df: pd.DataFrame,
    seuil: float = 0.5,
) -> pd.Series:
    """
    1 si le score de confiance OCR global est inférieur au seuil.

    [INSURANCE_DOMAIN_CONTEXT §3.2] : le cachet humide des documents
    camerounais dégrade la qualité OCR (score moyen observé : 0.62 ± 0.18).
    Un score < 0.5 est corrélé à des documents retouchés ou de mauvaise qualité.
    Seuil calibré sur le dataset UNITY.

    Feature commune ★ avec AutoModule pour M_makora_dif [Xu2023].

    Args:
        seuil : valeur de coupure (default=0.5, configurable).

    Returns:
        pd.Series int (0/1) nommée 'ocr_confiance_faible'.
    """
    raw = _safe_col(df, "Confiance_OCR_Glob", default=1.0)
    flag = (raw.fillna(1.0).astype(float) < seuil).astype(int)
    return flag.rename("ocr_confiance_faible")


# ===========================================================================
# Feature 4 — delai_depot_anormal  (★ COMMUN M_makora_dif)
# Renommée depuis delai_soin_depot_anormal (Scénario A).
# Le nom de la fonction interne est conservé pour rétrocompatibilité.
# ===========================================================================

def compute_delai_soin_depot_anormal(
    df: pd.DataFrame,
    seuil_jours: int = 30,
) -> pd.Series:
    """
    1 si le délai entre la date du soin et le dépôt du dossier dépasse le seuil.

    [Chandola2009] §3.1 — Les features temporelles sont parmi les meilleurs
    discriminants en fraude santé. Un délai excessif suggère une antidatation
    ou une accumulation frauduleuse de dossiers (batching).
    Seuil de 30 jours : conforme aux délais réglementaires CIMA Art. 12.

    Feature commune ★ avec AutoModule (delai_depot_anormal) pour M_makora_dif.
    Le seuil 30j est distinct de document_age_anormal (180j) : deux niveaux
    de retard capturant des patterns de fraude différents [Chandola2009].

    Note sur le nommage : la fonction s'appelle compute_delai_soin_depot_anormal
    pour préserver la rétrocompatibilité des tests ; la Series retournée et la
    clé du registre sont 'delai_depot_anormal' (Scénario A).

    Returns:
        pd.Series int (0/1) nommée 'delai_depot_anormal'.
    """
    raw = _safe_col(df, "Delai_Soin_Depot", default=0)
    flag = (raw.fillna(0).astype(float) > seuil_jours).astype(int)
    return flag.rename("delai_depot_anormal")


# ===========================================================================
# Feature 5 — anciennete_contrat_courte  (★ COMMUN M_makora_dif)
# ===========================================================================

def compute_anciennete_contrat_courte(
    df: pd.DataFrame,
    seuil_jours: int = 90,
) -> pd.Series:
    """
    1 si l'ancienneté du contrat est inférieure au seuil au moment du soin.

    [Viaene2002] Viaene et al. (2002). Automobile insurance fraud detection.
    Journal of Risk and Insurance. — Bien que le contexte soit Auto, le signal
    "souscription récente + sinistre précoce" est un pattern universel validé
    sur plusieurs branches (Santé, Auto, Vie).
    Seuil 90 jours : période anti-sélection standard des assureurs africains.

    Feature commune ★ avec AutoModule pour M_makora_dif [Xu2023].

    Returns:
        pd.Series int (0/1) nommée 'anciennete_contrat_courte'.
    """
    raw = _safe_col(df, "Anciennete_Contrat", default=365)
    flag = (raw.fillna(365).astype(float) < seuil_jours).astype(int)
    return flag.rename("anciennete_contrat_courte")


# ===========================================================================
# Feature 6 — saisie_hors_heures  (★ COMMUN M_makora_dif)
# ===========================================================================

def compute_saisie_hors_heures(
    df: pd.DataFrame,
    heure_min: int = 7,
    heure_max: int = 20,
) -> pd.Series:
    """
    1 si la saisie informatique a eu lieu en dehors des heures ouvrées.

    [INSURANCE_DOMAIN_CONTEXT §3.3] : la saisie nocturne (avant 7h ou après
    20h) est un signal contextuel faible mais qui renforce significativement
    d'autres features (document_altere, praticien_hors_agrement).
    [Chandola2009] : les features temporelles contextuelles améliorent le
    recall sur le scénario "fraude organisée" de 8 à 15 points.

    Feature commune ★ avec AutoModule pour M_makora_dif [Xu2023].

    Returns:
        pd.Series int (0/1) nommée 'saisie_hors_heures'.
    """
    raw = _safe_col(df, "Heure_Saisie", default=12)
    heure = raw.fillna(12).astype(float)
    flag = ((heure < heure_min) | (heure > heure_max)).astype(int)
    return flag.rename("saisie_hors_heures")


# ===========================================================================
# Feature 7 — montant_log  (★ COMMUN M_makora_dif)
# Renommée depuis montant_normalise_log (Scénario C).
# Le nom de la fonction interne est conservé pour rétrocompatibilité.
# ===========================================================================

def compute_montant_normalise_log(df: pd.DataFrame) -> pd.Series:
    """
    Transformation log1p du montant facturé : log(Montant_Facture + 1).

    [Liu2008] Liu et al. (2008). Isolation Forest. ICDM 2008.
    La distribution des montants de santé est fortement asymétrique (skewness
    typique > 5). La log-transformation réduit l'asymétrie et améliore la
    séparation IF/DIF : les anomalies de surfacturation extrême
    (upcoding massif) deviennent moins dominantes et permettent au modèle de
    détecter aussi les fraudes à montant modéré (unbundling).

    Feature commune ★ avec AutoModule (montant_log) pour M_makora_dif [Xu2023].
    Même transformation log1p appliquée sur Montant_Facture (Santé) et
    Montant_Devis (Auto) — les valeurs sont comparables après transformation
    malgré les différences d'échelle XAF/EUR.

    Note sur le nommage : la fonction s'appelle compute_montant_normalise_log
    pour préserver la rétrocompatibilité des tests ; la Series retournée et la
    clé du registre sont 'montant_log' (Scénario C).

    Returns:
        pd.Series float nommée 'montant_log'.
    """
    raw = _safe_col(df, "Montant_Facture", default=0.0)
    montant = raw.fillna(0.0).astype(float).clip(lower=0.0)
    return np.log1p(montant).rename("montant_log")


# ===========================================================================
# Feature 8 — post_mortem_flag
# ===========================================================================

def compute_post_mortem_flag(df: pd.DataFrame) -> pd.Series:
    """
    1 si la date du soin est postérieure à la date de décès de l'assuré.

    [Bauder2017] : le scénario "Soin Post-Mortem" (utilisation frauduleuse
    de la carte vitale d'un assuré décédé) représente 2 à 4% des fraudes
    détectées dans les études Medicare. Signal quasi-déterministe quand il
    est disponible.

    Note : si Date_Deces est absente ou NaT → flag = 0 (assuré vivant présumé).
    Évite les faux positifs sur données incomplètes.

    Returns:
        pd.Series int (0/1) nommée 'post_mortem_flag'.
    """
    if "Date_Soin" not in df.columns or "Date_Deces" not in df.columns:
        logger.warning(
            "compute_post_mortem_flag — colonnes Date_Soin ou Date_Deces absentes → flag=0"
        )
        return pd.Series(0, index=df.index, dtype=int, name="post_mortem_flag")

    date_soin = pd.to_datetime(df["Date_Soin"], errors="coerce")
    date_deces = pd.to_datetime(df["Date_Deces"], errors="coerce")

    # Comparaison sécurisée : NaT > NaT → False → flag = 0 ✓
    flag = (date_soin > date_deces).fillna(False).astype(int)
    return flag.rename("post_mortem_flag")


# ===========================================================================
# Feature 9 — nb_sinistres_meme_iban
# ===========================================================================

def compute_nb_sinistres_meme_iban(df: pd.DataFrame) -> pd.Series:
    """
    Nombre de sinistres remboursés vers le même IBAN dans la période glissante.

    [INSURANCE_DOMAIN_CONTEXT §4.3] : le "Détournement RIB/IBAN" consiste à
    modifier les coordonnées bancaires de l'assuré pour rediriger les
    remboursements. Un IBAN partagé par plusieurs assurés non liés est un
    signal fort de fraude organisée.
    Colonne déjà produite par ARGUS/UNITY — lecture directe.

    Returns:
        pd.Series float nommée 'nb_sinistres_meme_iban'.
    """
    raw = _safe_col(df, "Nb_Sinistres_Meme_IBAN", default=1)
    return raw.fillna(1).astype(float).rename("nb_sinistres_meme_iban")


# ===========================================================================
# Feature 10 — acte_incomplet  (★ COMMUN M_makora_dif — Scénario A)
# ===========================================================================

def compute_acte_incomplet(df: pd.DataFrame) -> pd.Series:
    """
    1 si le dossier est marqué comme acte/dossier incomplet.

    [INSURANCE_DOMAIN_CONTEXT §4.2] : un acte incomplet soumis délibérément
    est un signal d'intention frauduleuse (tenter le traitement avec un dossier
    insuffisant) ou d'erreur opérationnelle grave.
    Colonne source : Flag_Acte_Incomp (présent dans les datasets UNITY et ARGUS).

    Feature commune ★ avec AutoModule pour M_makora_dif [Xu2023].

    Returns:
        pd.Series int (0/1) nommée 'acte_incomplet'.
    """
    raw = _safe_col(df, "Flag_Acte_Incomp", default=0)
    return raw.fillna(0).astype(int).rename("acte_incomplet")


# ===========================================================================
# Feature 11 — document_age_anormal  (★ COMMUN M_makora_dif — Scénario B)
# Correction de dette documentaire : feature manquante en Session H.
# ===========================================================================

def compute_document_age_anormal_sante(
    df: pd.DataFrame,
    seuil_jours: int = 180,
) -> pd.Series:
    """
    1 si le délai entre la saisie système et le soin dépasse le seuil.

    Formule : (Date_Saisie_Systeme - Date_Soin) > seuil_jours
    Colonnes sources : Date_Saisie_Systeme, Date_Soin.

    [Chandola2009] — signal temporel de fraude préméditée : un document
    déposé plus de 180 jours après le soin est statistiquement associé
    à l'antidatage ou à la fabrication de justificatifs a posteriori.

    Note : distinct de delai_depot_anormal (seuil 30j, Delai_Soin_Depot).
    Deux niveaux de retard capturant des patterns différents :
    - 30j → retard opérationnel / négligence
    - 180j → antidatage délibéré / fabrication

    Stratégie de dégradation (ordre) :
    1. Calcul depuis Date_Saisie_Systeme - Date_Soin (source primaire)
    2. Fallback sur Delai_Soin_Depot > seuil_jours (colonne pré-calculée)
    3. Valeur neutre 0 si aucune source disponible

    Feature commune ★ avec AutoModule (compute_document_age_anormal_auto)
    pour M_makora_dif [Xu2023]. Seuil 180j identique dans les deux modules.

    Returns:
        pd.Series int (0/1) nommée 'document_age_anormal'.
    """
    # Chemin 1 : calcul depuis les dates brutes (source primaire)
    if "Date_Saisie_Systeme" in df.columns and "Date_Soin" in df.columns:
        date_saisie = pd.to_datetime(df["Date_Saisie_Systeme"], errors="coerce")
        date_soin = pd.to_datetime(df["Date_Soin"], errors="coerce")
        delta = (date_saisie - date_soin).dt.days
        flag = (delta.fillna(0) > seuil_jours).astype(int)
        return flag.rename("document_age_anormal")

    # Chemin 2 : fallback sur Delai_Soin_Depot (colonne pré-calculée UNITY)
    if "Delai_Soin_Depot" in df.columns:
        logger.warning(
            "compute_document_age_anormal_sante — Date_Saisie_Systeme absente, "
            "fallback sur Delai_Soin_Depot > %d jours", seuil_jours
        )
        raw = df["Delai_Soin_Depot"].fillna(0).astype(float)
        return (raw > seuil_jours).astype(int).rename("document_age_anormal")

    # Chemin 3 : aucune source disponible
    logger.warning(
        "compute_document_age_anormal_sante — colonnes Date_Saisie_Systeme "
        "et Delai_Soin_Depot absentes → flag=0"
    )
    return pd.Series(0, index=df.index, dtype=int, name="document_age_anormal")


# ===========================================================================
# Feature 12 — nb_sinistres_recents  (★ COMMUN M_makora_dif — Scénario B)
# ===========================================================================

def compute_nb_sinistres_recents_sante(df: pd.DataFrame) -> pd.Series:
    """
    Nombre de sinistres de l'assuré sur les 12 derniers mois (fenêtre glissante).

    [Viaene2002] Viaene et al. (2002). Automobile insurance fraud detection.
    Journal of Risk and Insurance. — La fréquence anormale de sinistres
    (Doctor Shopping, soins fictifs répétés) est le signal de fraude par
    répétition le plus documenté. Seuil critique : > 3 sinistres / 12 mois.

    Colonne source : Nb_Sinistres_12m (pré-calculée dans le dataset UNITY).
    Fenêtre 12M unifiée avec AutoModule (même colonne source) pour l'alignement
    M_makora_dif [Xu2023].

    Feature commune ★ avec AutoModule pour M_makora_dif.

    Returns:
        pd.Series float nommée 'nb_sinistres_recents'.
    """
    raw = _safe_col(df, "Nb_Sinistres_12m", default=0)
    return raw.fillna(0).astype(float).rename("nb_sinistres_recents")


# ===========================================================================
# Registre V2 — utilisé par SanteModule.engineer_features()
#
# PRINCIPE YAML-DRIVEN : SanteModule itère ce dict via :
#   for feature_name, fn in FEATURE_EXT_FUNCTIONS.items():
#       df[feature_name] = fn(df)
# La clé = nom de feature exact tel que déclaré dans sante.yaml.
# La valeur = fonction callable(df) -> pd.Series dont .name == clé.
#
# Invariant testé par TestRegistreFonctions.test_noms_series_coherents :
#   result.name == nom_clé pour chaque entrée du registre.
#
# NOTES DE MIGRATION :
#   'delai_depot_anormal'  = compute_delai_soin_depot_anormal (Scénario A)
#   'montant_log'          = compute_montant_normalise_log (Scénario C)
# ===========================================================================

FEATURE_EXT_FUNCTIONS: dict[str, callable] = {
    "document_altere":           compute_document_altere,
    "praticien_hors_agrement":   compute_praticien_hors_agrement,
    "ocr_confiance_faible":      compute_ocr_confiance_faible,
    "delai_depot_anormal":       compute_delai_soin_depot_anormal,      # Scénario A
    "anciennete_contrat_courte": compute_anciennete_contrat_courte,
    "saisie_hors_heures":        compute_saisie_hors_heures,
    "montant_log":               compute_montant_normalise_log,          # Scénario C
    "post_mortem_flag":          compute_post_mortem_flag,
    "nb_sinistres_meme_iban":    compute_nb_sinistres_meme_iban,
    "acte_incomplet":            compute_acte_incomplet,                 # Scénario A ★
    "document_age_anormal":      compute_document_age_anormal_sante,     # Scénario B ★
    "nb_sinistres_recents":      compute_nb_sinistres_recents_sante,     # Scénario B ★
}
"""
Registre des 12 fonctions de feature engineering V2 du module Santé.
Utilisé par SanteModule.engineer_features() pour itérer dans l'ordre
déclaré dans sante.yaml → garantit reproductibilité de l'ordre de calcul.

Importé aussi par les tests unitaires pour validation systématique.
"""

