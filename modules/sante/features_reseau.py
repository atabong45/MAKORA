"""
MODULE : modules/sante/features_reseau.py
DESCRIPTION : Features de détection réseau et doublons pour le module Santé.
              Complète features.py et features_ext.py sans les modifier.
              À importer dans sante_module.py via FEATURE_RESEAU_FUNCTIONS_SANTE.

NOUVELLES FEATURES (3) :
  · flag_doublon         : dossier soumis plusieurs fois (Duplicate Billing)
  · community_score      : appartenance à une communauté suspecte (réseau de fraude)
  · prestataire_concentration : part des sinistres concentrée sur ce praticien
                                dans le batch courant (proxy réseau sans graphe)

RÉFÉRENCES ACADÉMIQUES :
  [Jiang2014] Jiang et al. (2014). CatchSync: catching synchronized behavior
              in large directed graphs. KDD.
              Justifie community_score comme signal de fraude coordonnée.
  [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection using
               machine learning methods. ICMLA.
               Duplicate Billing (Flag_Doublon) est le 2e pattern de fraude
               le plus fréquent dans les données Medicare.
  [Blondel2008] Blondel et al. (2008). Fast unfolding of communities in large
                networks. Journal of Statistical Mechanics.
                community_id_sante calculé par Louvain dans graph_engine.py.
                Ici on lit le résultat pré-calculé dans le dataset.
  [Xu2023] Xu et al. (2023). Deep Isolation Forest for Anomaly Detection.
           IEEE Transactions on Knowledge and Data Engineering.
           Ces 3 features font partie des 13 features communes
           pour M_makora_dif (flag_doublon, community_score,
           prestataire_concentration).

DÉCISIONS DE CONCEPTION :
  - Ces features lisent des colonnes DÉJÀ présentes dans le dataset v2
    (Flag_Doublon, community_id_sante) — elles ne recalculent pas le graphe.
  - Le graphe complet (NetworkX + Louvain) est activé via graph_engine.py (T13.1).
    Ces features sont le "pont" qui permet à l'IF de consommer le signal réseau.
  - prestataire_concentration est calculé en-ligne sur le batch (stateless)
    car la persistance inter-batches est une dette DT-002 non résolue.
  - Toutes les valeurs nulles sont gérées vers 0.0 (pas de NaN dans l'IF).
  - Invariant : result.name == clé du registre FEATURE_RESEAU_FUNCTIONS_SANTE.
    Vérifié par TestRegistreFonctions.test_noms_series_coherents.

CHANGEMENTS v0.5.0 (Scénario A) :
  - Clé registre "flag_doublon_sante" -> "flag_doublon" (feature commune)
  - Clé registre "community_score_sante" -> "community_score" (feature commune)
  - Clé registre "praticien_concentration" -> "prestataire_concentration" (feature commune)
  - .rename() ajouté dans chaque fonction pour garantir l'invariant name == clé
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ─── Feature 1 — Doublon de soumission ────────────────────────────────────────

def compute_flag_doublon_sante(df: pd.DataFrame) -> pd.Series:
    """
    Retourne 1 si le dossier est marqué comme doublon, 0 sinon.

    Source : colonne Flag_Doublon ajoutée par t10_0_enrich_sante.py.
    Fallback : 0 si la colonne est absente (pipeline ne crashe pas).

    Feature commune Santé/Auto : "flag_doublon" [Xu2023].
    [Bauder2017] — Duplicate Billing : 2e cause de fraude Medicare par volume.

    Returns:
        pd.Series nommée "flag_doublon", dtype int8, valeurs 0 ou 1.
    """
    if "Flag_Doublon" not in df.columns:
        return pd.Series(0, index=df.index, dtype="int8").rename("flag_doublon")
    return df["Flag_Doublon"].fillna(False).astype("int8").rename("flag_doublon")


# ─── Feature 2 — Score de communauté suspecte ─────────────────────────────────

def compute_community_score_sante(df: pd.DataFrame) -> pd.Series:
    """
    Score d'appartenance à une communauté de fraude réseau [0.0 - 1.0].

    Calcul :
      - community_id_sante == 0  -> score = 0.0  (pas de communauté)
      - community_id_sante > 0   -> score = taille_communauté / MAX_TAILLE
        normalisé entre 0.1 et 1.0

    Plus la communauté est grande, plus le score est élevé.
    Une communauté de 2 dossiers = score faible.
    Une communauté de 60 dossiers = score proche de 1.0.

    Feature commune Santé/Auto : "community_score" [Xu2023].
    [Jiang2014] — la taille de la communauté est corrélée avec l'ampleur
    de la fraude coordonnée (kickbacks, soins fantômes organisés).
    [Blondel2008] — community_id calculé par Louvain sur le graphe
    praticien/assuré construit par graph_engine.py (T13.1).

    Returns:
        pd.Series nommée "community_score", dtype float32, valeurs [0.0, 1.0].
    """
    if "community_id_sante" not in df.columns:
        return pd.Series(0.0, index=df.index, dtype="float32").rename("community_score")

    comm_id = df["community_id_sante"].fillna(0).astype(int)

    # Taille de chaque communauté dans le batch [Blondel2008]
    comm_sizes = comm_id[comm_id > 0].value_counts()
    max_size = comm_sizes.max() if len(comm_sizes) > 0 else 1

    def _score(cid: int) -> float:
        if cid == 0:
            return 0.0
        size = comm_sizes.get(cid, 1)
        # Score minimum 0.1 pour tout membre d'une communauté [Jiang2014]
        return float(np.clip(0.1 + 0.9 * (size / max_size), 0.0, 1.0))

    return comm_id.map(_score).astype("float32").rename("community_score")


# ─── Feature 3 — Concentration prestataire ────────────────────────────────────

def compute_praticien_concentration(df: pd.DataFrame) -> pd.Series:
    """
    Part des sinistres du batch concentrée sur le praticien de ce dossier.

    Calcul : nb_sinistres_praticien / nb_total_sinistres_batch

    Un praticien normal représente < 0.5% des dossiers.
    Un praticien fraudeur concentré peut représenter 30-40% (Pareto).

    Feature commune Santé/Auto : "prestataire_concentration" [Xu2023].
    [Bauder2017] — la concentration des actes sur un petit nombre de
    prestataires est le signal le plus robuste de fraude Medicare.
    [Jiang2014] — corrélé avec la densité du graphe praticien/assuré.

    Note : proxy stateless — persistance inter-batches est une dette DT-002.

    Returns:
        pd.Series nommée "prestataire_concentration", dtype float32, valeurs [0.0, 1.0].
    """
    if "ID_Praticien" not in df.columns:
        return pd.Series(0.0, index=df.index, dtype="float32").rename(
            "prestataire_concentration"
        )

    n_total = len(df)
    if n_total == 0:
        return pd.Series(0.0, index=df.index, dtype="float32").rename(
            "prestataire_concentration"
        )

    prat_counts = df["ID_Praticien"].value_counts()
    concentration = df["ID_Praticien"].map(prat_counts) / n_total
    return (
        concentration.fillna(0.0).astype("float32").rename("prestataire_concentration")
    )


# ─── Registre YAML-driven ─────────────────────────────────────────────────────
# Clés = noms des features tels que déclarés dans sante.yaml v0.5.0.
# Invariant : result.name == clé pour toute fn dans ce dict.
# Scénario A : 3 renommages par rapport à v0.4.0.

FEATURE_RESEAU_FUNCTIONS_SANTE: dict[str, callable] = {
    "flag_doublon":              compute_flag_doublon_sante,        # était flag_doublon_sante
    "community_score":           compute_community_score_sante,     # était community_score_sante
    "prestataire_concentration": compute_praticien_concentration,   # était praticien_concentration
}