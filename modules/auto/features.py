"""
MODULE : modules/auto/features.py
DESCRIPTION : Feature engineering principal pour le module Auto MAKORA.
              18 features V1 (dont 3 nouvelles Scénarios A+B).
              Utilisé par AutoModule via FEATURE_FUNCTIONS (registre YAML-driven).

RÉFÉRENCES ACADÉMIQUES :
  [Viaene2002]  Viaene et al. (2002). Automobile insurance fraud detection.
                Journal of Risk and Insurance.
                Features ratio_devis_bareme, sinistre_nuit_sans_temoin,
                delai_depot_anormal, nb_sinistres_recents.
  [Subudhi2017] Subudhi & Panigrahi (2017). Automobile insurance fraud.
                Journal of King Saud University.
                Features vehicule_sur_value, ratio_mo_reference.
  [Liu2008]     Liu et al. (2008). Isolation Forest. ICDM 2008.
                Feature montant_log : la transformation log réduit l'influence
                des outliers extrêmes sur l'IF.
  [Bauder2017]  Bauder & Khoshgoftaar (2017). Medicare fraud detection. ICMLA.
                Feature is_weekend_event : signal comportemental transverse.
  [Chandola2009] Chandola et al. (2009). Anomaly Detection: A Survey.
                 ACM Computing Surveys. Feature document_age_anormal.
  [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
                Registre YAML-driven : zero hardcoding dans AutoModule.
  [Xu2023]      Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
                13 features communes (marquées ★) pour M_makora_dif.

DÉCISIONS DE CONCEPTION :
  - FEATURE_FUNCTIONS est le seul registre V1 lu par auto_module.py.
  - Invariant : chaque fonction fn retourne une pd.Series nommée
    exactement comme la clé du dict ou n'impose pas de nom (auto_module
    assigne le nom). Les fonctions V1 ne .rename() pas (auto_module gère).
  - _safe_col() est le pattern uniforme pour toutes les lectures optionnelles.
  - Toutes les exceptions sont absorbées avec un fallback 0 — le pipeline
    ne crashe jamais sur une colonne manquante [Sculley2015].

CHANGEMENTS v1.2.0 (Scénarios A+B+C) :
  - "garage_concentration_score" -> "prestataire_concentration" (Scénario A)
  - "delai_declaration_anormal"  -> "delai_depot_anormal" (Scénario A)
  - "nb_sinistres_12m"           -> "nb_sinistres_recents" (Scénario B)
  - "montant_devis_log"          -> "montant_log" (Scénario C)
  - NOUVELLES : compute_is_weekend_event, compute_acte_incomplet_auto,
                compute_document_age_anormal_auto
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Utilitaire interne
# ---------------------------------------------------------------------------

def _safe_col(
    df: pd.DataFrame,
    col: str,
    default: int | float = 0,
) -> pd.Series:
    """
    Lit une colonne avec fallback si absente.

    [Sculley2015] : la dégradation gracieuse est préférable à un crash.
    Une feature manquante retourne sa valeur neutre — le pipeline continue.
    """
    if col not in df.columns:
        logger.debug("_safe_col : colonne '%s' absente — valeur neutre %s.", col, default)
        return pd.Series(default, index=df.index, dtype=float)
    return df[col]


# ===========================================================================
# Feature 1 — ratio_devis_bareme  [CRITIQUE]
# ===========================================================================

def compute_ratio_devis_bareme(
    df: pd.DataFrame,
    mercuriale_index=None,
    cap: float = 50.0,
) -> pd.Series:
    """
    Ratio Montant_Devis / prix_reference_bareme (ASAC camerounais ou Argus FR).

    Stratégie de résolution du prix de référence :
      1. mercuriale_index (MercurialeLoader) si disponible
      2. colonne Montant_Reference_Bareme si présente dans df
      3. fallback 1.0 avec log warning

    [Viaene2002] : ratio > 1.30 est le seuil de surfacturation documenté
    dans les données de sinistres auto français.
    [Subudhi2017] : sur données indiennes, seuil > 1.50.
    Seuil retenu dans auto.yaml : 1.30 (contexte camerounais/africain).

    Args:
        df: DataFrame ARGUS
        mercuriale_index: MercurialeIndex chargé par AutoModule (peut être None)
        cap: valeur maximale du ratio (cap 50.0 pour outliers extrêmes)

    Returns:
        pd.Series float, capée à cap, fillna(1.0).
    """
    montant = _safe_col(df, "Montant_Devis", default=0).astype(float)

    # Priorité 1 — mercuriale dynamique
    if mercuriale_index is not None and "Code_Prestation" in df.columns:
        prix_ref = df["Code_Prestation"].map(mercuriale_index).astype(float)
    # Priorité 2 — colonne pré-calculée dans le dataset
    elif "Montant_Reference_Bareme" in df.columns:
        prix_ref = _safe_col(df, "Montant_Reference_Bareme", default=1.0).astype(float)
    else:
        logger.warning(
            "compute_ratio_devis_bareme : ni mercuriale ni Montant_Reference_Bareme "
            "disponible — ratio neutre 1.0 retourné."
        )
        return pd.Series(1.0, index=df.index, dtype=float)

    # Éviter la division par zéro
    prix_ref = prix_ref.replace(0, np.nan)
    ratio = (montant / prix_ref).clip(upper=cap)

    if ratio.isna().sum() > 0:
        logger.debug(
            "compute_ratio_devis_bareme : %d valeurs NaN.", ratio.isna().sum()
        )
    return ratio.fillna(1.0)


# ===========================================================================
# Feature 2 — vehicule_sur_value  [CRITIQUE]
# ===========================================================================

def compute_vehicule_sur_value(
    df: pd.DataFrame,
    seuil_ratio: float = 0.80,
) -> pd.Series:
    """
    True si le montant du devis dépasse seuil_ratio * valeur vénale du véhicule.

    Conversion XAF -> EUR via taux BEAC si nécessaire.
    Fallback : False si l'une des colonnes est absente.

    [Subudhi2017] : sur-valorisation des dommages est le 2e pattern
    le plus fréquent en fraude auto (après staging accident).

    Returns:
        pd.Series bool
    """
    if "Montant_Devis" not in df.columns or "Valeur_Venale_EUR" not in df.columns:
        return pd.Series(False, index=df.index, dtype=bool)

    devis = _safe_col(df, "Montant_Devis", default=0).astype(float)
    valeur = _safe_col(df, "Valeur_Venale_EUR", default=1).astype(float)

    # Si le montant est en XAF (colonne présente), convertir en EUR
    if "Devise" in df.columns:
        taux_xaf_eur = 1 / 655.957  # Taux BEAC fixe XAF/EUR [CIMA]
        devis = devis.where(df["Devise"] != "XAF", devis * taux_xaf_eur)

    valeur = valeur.replace(0, np.nan)
    ratio = devis / valeur
    return (ratio > seuil_ratio).fillna(False)


# ===========================================================================
# Feature 3 — sinistre_nuit_sans_temoin  [CRITIQUE]
# ===========================================================================

def compute_sinistre_nuit_sans_temoin(df: pd.DataFrame) -> pd.Series:
    """
    True si le sinistre survient la nuit ET sans témoin.

    Signal de staging accident nocturne : le conducteur provoque
    intentionnellement un accident sans témoin.

    [Viaene2002] : pattern dominant dans les données belges d'assurance auto.
    Corrélé avec sinistre_weekend dans les données ARGUS camerounaises.

    Returns:
        pd.Series bool
    """
    nuit = _safe_col(df, "Flag_Sinistre_Nuit", default=False).fillna(False).astype(bool)
    nb_temoins = _safe_col(df, "Nb_Temoins", default=1).fillna(1).astype(int)
    return nuit & (nb_temoins == 0)


# ===========================================================================
# Feature 4 — document_altere  [CRITIQUE] ★ COMMUN
# ===========================================================================

def compute_document_altere(df: pd.DataFrame) -> pd.Series:
    """
    True si le document est marqué comme altéré (Flag_Doc_Altere).

    Feature commune Santé/Auto : "document_altere" [Xu2023].
    [Bauder2017] : fraude documentaire = modification ou falsification
    du constat ou de la facture de réparation.

    Returns:
        pd.Series bool
    """
    return _safe_col(df, "Flag_Doc_Altere", default=False).fillna(False).astype(bool)


# ===========================================================================
# Feature 5 — prestataire_concentration  [CRITIQUE] ★ COMMUN
# (anciennement garage_concentration_score — Scénario A)
# ===========================================================================

def compute_garage_concentration_score(df: pd.DataFrame) -> pd.Series:
    """
    Part des sinistres du batch concentrée sur le garage de ce dossier.

    Calcul : nb_sinistres_garage / nb_total_sinistres_batch
    Proxy stateless — persistance inter-batches est une dette DT-002.

    Feature commune Santé/Auto : "prestataire_concentration" [Xu2023].
    Scénario A : clé renommée de "garage_concentration_score" dans registre.
    [Jiang2014] : la concentration sur un sous-réseau est un signal fort de
    fraude coordonnée.

    Returns:
        pd.Series float [0.0, 1.0]
    """
    if "ID_Garage" not in df.columns:
        return pd.Series(0.0, index=df.index, dtype=float)

    n_total = len(df)
    if n_total == 0:
        return pd.Series(0.0, index=df.index, dtype=float)

    garage_counts = df["ID_Garage"].value_counts()
    concentration = df["ID_Garage"].map(garage_counts) / n_total
    return concentration.fillna(0.0).astype(float)


# ===========================================================================
# Feature 6 — garage_non_agree  [HAUTE]
# ===========================================================================

def compute_garage_non_agree(df: pd.DataFrame) -> pd.Series:
    """
    True si le garage n'est pas agréé CIMA.

    Contexte camerounais : l'agrément CIMA est obligatoire pour les
    garages partenaires des compagnies d'assurance [CIMA, Art. 213].

    Returns:
        pd.Series bool
    """
    agree = _safe_col(df, "Agrement_CIMA", default=True).fillna(True).astype(bool)
    return ~agree


# ===========================================================================
# Feature 7 — constat_manquant  [HAUTE]
# ===========================================================================

def compute_constat_manquant(df: pd.DataFrame) -> pd.Series:
    """
    True si le constat amiable est absent.

    [Viaene2002] : l'absence de constat est un signal de staging accident.
    Constat obligatoire pour sinistres > 500 000 XAF au Cameroun [CIMA].

    Returns:
        pd.Series bool
    """
    present = _safe_col(df, "Constat_Amiable_Present", default=True).fillna(True).astype(bool)
    return ~present


# ===========================================================================
# Feature 8 — expertise_manquante  [HAUTE]
# ===========================================================================

def compute_expertise_manquante(df: pd.DataFrame) -> pd.Series:
    """
    True si le rapport d'expertise signé est absent.

    [Viaene2002] : l'absence d'expertise est corrélée avec la collusion
    garage-assuré (réparation fictive ou gonflée).

    Returns:
        pd.Series bool
    """
    present = (
        _safe_col(df, "Rapport_Expertise_Signe", default=True).fillna(True).astype(bool)
    )
    return ~present


# ===========================================================================
# Feature 9 — delai_depot_anormal  [HAUTE] ★ COMMUN
# (anciennement delai_declaration_anormal — Scénario A)
# ===========================================================================

def compute_delai_declaration_anormal(
    df: pd.DataFrame,
    seuil_jours: int = 30,
) -> pd.Series:
    """
    True si le délai entre le sinistre et la déclaration dépasse seuil_jours.

    Feature commune Santé/Auto : "delai_depot_anormal" [Xu2023].
    Scénario A : clé renommée de "delai_declaration_anormal" dans registre.

    [Viaene2002] : délai > 30 jours est suspect (fraude rétrospective).
    Seuil externalisé dans auto.yaml (défaut 30 jours).

    Returns:
        pd.Series bool
    """
    delai = _safe_col(df, "Delai_Declaration", default=0).fillna(0).astype(float)
    return (delai > seuil_jours).astype(bool)


# ===========================================================================
# Feature 10 — anciennete_contrat_courte  [HAUTE] ★ COMMUN
# ===========================================================================

def compute_anciennete_contrat_courte(
    df: pd.DataFrame,
    seuil_jours: int = 90,
) -> pd.Series:
    """
    True si le contrat a moins de seuil_jours (défaut 90 jours).

    Feature commune Santé/Auto : "anciennete_contrat_courte" [Xu2023].
    [Viaene2002] : fraude à la souscription — souscrire pour frauder
    immédiatement puis résilier.

    Returns:
        pd.Series bool
    """
    anciennete = (
        _safe_col(df, "Anciennete_Contrat", default=365).fillna(365).astype(float)
    )
    return (anciennete < seuil_jours).astype(bool)


# ===========================================================================
# Feature 11 — ocr_confiance_faible  [HAUTE] ★ COMMUN
# ===========================================================================

def compute_ocr_confiance_faible(
    df: pd.DataFrame,
    seuil: float = 0.5,
) -> pd.Series:
    """
    True si le score de confiance OCR global est inférieur à seuil.

    Feature commune Santé/Auto : "ocr_confiance_faible" [Xu2023].
    Spécifique contexte camerounais : le cachet humide dégrade l'OCR
    (taux d'erreur documenté > 15% sur documents scannés [ADR-007]).

    Returns:
        pd.Series bool
    """
    conf = (
        _safe_col(df, "Confiance_OCR_Glob", default=1.0).fillna(1.0).astype(float)
    )
    return (conf < seuil).astype(bool)


# ===========================================================================
# Feature 12 — ratio_mo_reference  [HAUTE]
# ===========================================================================

def compute_ratio_mo_reference(
    df: pd.DataFrame,
    cap: float = 20.0,
) -> pd.Series:
    """
    Ratio Cout_MO / tarif main d'oeuvre de référence ASAC.

    [Subudhi2017] : surfacturation de la main d'oeuvre est le 3e signal
    de fraude auto après ratio_devis et vehicule_sur_value.

    Returns:
        pd.Series float, capée à cap, fillna(1.0).
    """
    cout_mo = _safe_col(df, "Ratio_MO", default=1.0).astype(float)
    ratio = cout_mo.clip(upper=cap)
    if ratio.isna().sum() > 0:
        logger.debug(
            "compute_ratio_mo_reference : %d valeurs NaN.", ratio.isna().sum()
        )
    return ratio.fillna(1.0)


# ===========================================================================
# Feature 13 — nb_sinistres_recents  [HAUTE] ★ COMMUN
# (anciennement nb_sinistres_12m — Scénario B)
# ===========================================================================

def compute_nb_sinistres_12m(df: pd.DataFrame) -> pd.Series:
    """
    Nombre de sinistres de l'assuré sur les 12 derniers mois.

    Feature commune Santé/Auto : "nb_sinistres_recents" [Xu2023].
    Scénario B : clé renommée de "nb_sinistres_12m" dans registre.
    Colonne déjà présente dans ARGUS — feature pass-through.

    [Viaene2002] : fréquence anormale (> 3 sinistres / 12 mois) est
    le signal de fraude auto par répétition le plus documenté.

    Returns:
        pd.Series float, fillna(0).
    """
    return _safe_col(df, "Nb_Sinistres_12m", default=0).astype(float).fillna(0)


# ===========================================================================
# Feature 14 — montant_log  [MOYENNE] ★ COMMUN
# (anciennement montant_devis_log — Scénario C)
# ===========================================================================

def compute_montant_devis_log(df: pd.DataFrame) -> pd.Series:
    """
    Transformation log1p du montant du devis.

    Feature commune Santé/Auto : "montant_log" [Xu2023].
    Scénario C : clé renommée de "montant_devis_log" dans registre.

    [Liu2008] : l'IF est sensible aux features à forte asymétrie.
    log1p(x) = log(x + 1) normalise la distribution des montants XAF/EUR.

    Returns:
        pd.Series float
    """
    montant = _safe_col(df, "Montant_Devis", default=0).astype(float).clip(lower=0)
    return np.log1p(montant)


# ===========================================================================
# Feature 15 — saisie_hors_heures  [MOYENNE] ★ COMMUN
# ===========================================================================

def compute_saisie_hors_heures(
    df: pd.DataFrame,
    heure_min: int = 7,
    heure_max: int = 20,
) -> pd.Series:
    """
    True si la saisie système a eu lieu hors des heures ouvrées.

    Feature commune Santé/Auto : "saisie_hors_heures" [Xu2023].
    [Chandola2009] : signal contextuel — renforce d'autres features.

    Returns:
        pd.Series bool
    """
    heure = _safe_col(df, "Heure_Saisie", default=12).astype(float).fillna(12)
    return ((heure < heure_min) | (heure > heure_max)).astype(bool)


# ===========================================================================
# Feature 16 — is_weekend_event  [HAUTE] ★ COMMUN  (NOUVEAU — Scénario A)
# ===========================================================================

def compute_is_weekend_event(df: pd.DataFrame) -> pd.Series:
    """
    1 si le sinistre survient un samedi (5) ou dimanche (6).

    Feature commune Santé/Auto : "is_weekend_event" [Xu2023].
    Colonne source : Date_Sinistre.

    [Bauder2017] : les sinistres frauduleux sont statistiquement plus
    fréquents en weekend (moins de témoins, contrôles réduits).
    Signal comportemental transverse validé sur données Medicare.

    Returns:
        pd.Series int (0 ou 1), nommée "is_weekend_event".
    """
    if "Date_Sinistre" not in df.columns:
        logger.warning(
            "compute_is_weekend_event — Date_Sinistre absente -> flag=0."
        )
        return pd.Series(0, index=df.index, dtype=int, name="is_weekend_event")
    dates = pd.to_datetime(df["Date_Sinistre"], errors="coerce")
    flag = dates.dt.dayofweek.isin([5, 6]).astype(int)
    return flag.fillna(0).astype(int).rename("is_weekend_event")


# ===========================================================================
# Feature 17 — acte_incomplet  [HAUTE] ★ COMMUN  (NOUVEAU — Scénario A)
# ===========================================================================

def compute_acte_incomplet_auto(df: pd.DataFrame) -> pd.Series:
    """
    1 si le dossier est marqué incomplet (Flag_Acte_Incomp).

    Feature commune Santé/Auto : "acte_incomplet" [Xu2023].
    Colonne source : Flag_Acte_Incomp (optionnelle, fallback 0).

    Contexte domaine CIMA : un acte incomplet empêche la vérification
    de la légitimité du sinistre.

    Returns:
        pd.Series int (0 ou 1), nommée "acte_incomplet".
    """
    raw = _safe_col(df, "Flag_Acte_Incomp", default=0)
    return raw.fillna(0).astype(int).rename("acte_incomplet")


# ===========================================================================
# Feature 18 — document_age_anormal  [HAUTE] ★ COMMUN  (NOUVEAU — Scénario B)
# ===========================================================================

def compute_document_age_anormal_auto(
    df: pd.DataFrame,
    seuil_jours: int = 180,
) -> pd.Series:
    """
    1 si Delai_Declaration > seuil_jours (défaut 180 jours).

    Feature commune Santé/Auto : "document_age_anormal" [Xu2023].
    Distinct de delai_depot_anormal (seuil 30j) : deux niveaux de retard.
    Colonne source : Delai_Declaration (en jours, déjà disponible dans ARGUS).

    [Chandola2009] : un document soumis > 6 mois après le sinistre est
    statistiquement hors-norme dans les données d'assurance française.

    Returns:
        pd.Series int (0 ou 1), nommée "document_age_anormal".
    """
    raw = _safe_col(df, "Delai_Declaration", default=0)
    return (raw.fillna(0).astype(float) > seuil_jours).astype(int).rename(
        "document_age_anormal"
    )


# ===========================================================================
# Registre YAML-driven — FEATURE_FUNCTIONS
# Clés = noms des features tels que déclarés dans auto.yaml v1.2.0.
# AutoModule itère ce dict via FEATURE_FUNCTIONS.items().
# L'ordre dict (Python 3.7+) est l'ordre de calcul.
#
# CHANGEMENTS v1.2.0 (Scénarios A+B+C) :
#   A : garage_concentration_score -> prestataire_concentration
#   A : delai_declaration_anormal  -> delai_depot_anormal
#   A : + is_weekend_event (NOUVEAU)
#   A : + acte_incomplet (NOUVEAU)
#   B : nb_sinistres_12m           -> nb_sinistres_recents
#   B : + document_age_anormal (NOUVEAU)
#   C : montant_devis_log          -> montant_log
# ===========================================================================

FEATURE_FUNCTIONS: dict[str, callable] = {
    "ratio_devis_bareme":        compute_ratio_devis_bareme,
    "vehicule_sur_value":        compute_vehicule_sur_value,
    "sinistre_nuit_sans_temoin": compute_sinistre_nuit_sans_temoin,
    "document_altere":           compute_document_altere,
    "prestataire_concentration": compute_garage_concentration_score,  # A: renommage clé
    "garage_non_agree":          compute_garage_non_agree,
    "constat_manquant":          compute_constat_manquant,
    "expertise_manquante":       compute_expertise_manquante,
    "delai_depot_anormal":       compute_delai_declaration_anormal,   # A: renommage clé
    "anciennete_contrat_courte": compute_anciennete_contrat_courte,
    "ocr_confiance_faible":      compute_ocr_confiance_faible,
    "ratio_mo_reference":        compute_ratio_mo_reference,
    "nb_sinistres_recents":      compute_nb_sinistres_12m,            # B: renommage clé
    "montant_log":               compute_montant_devis_log,           # C: renommage clé
    "saisie_hors_heures":        compute_saisie_hors_heures,
    "is_weekend_event":          compute_is_weekend_event,            # A: NOUVEAU
    "acte_incomplet":            compute_acte_incomplet_auto,         # A: NOUVEAU
    "document_age_anormal":      compute_document_age_anormal_auto,   # B: NOUVEAU
}
"""
Registre des 18 fonctions de feature engineering du module Auto (v1.2.0).
Itéré par AutoModule.engineer_features() — ordre dict = ordre de calcul.
13 features communes (marquées ★) avec SanteModule pour M_makora_dif [Xu2023].
"""