"""
MODULE : modules/auto/features_reseau.py
DESCRIPTION : Features de détection réseau et doublons pour le module Auto.
              Même structure que modules/sante/features_reseau.py,
              adaptée au contexte garage/assuré.

FEATURES (3) :
  · flag_doublon             : double déclaration du même sinistre [COMMUN ★]
  · community_score          : appartenance à une communauté suspecte garage/assuré [COMMUN ★]
  · expert_garage_correlation : même expert valide systématiquement le même garage
                                (signal de collusion expert-garage — spécifique Auto)

RÉFÉRENCES ACADÉMIQUES :
  [Viaene2002]  Viaene et al. (2002). Automobile insurance fraud detection.
                Journal of Risk and Insurance.
                Collusion garage-expert : pattern le plus documenté en fraude auto.
  [Jiang2014]   Jiang et al. (2014). CatchSync: catching synchronized behavior
                in large directed graphs. KDD.
                Comportements synchronisés dans les graphes bipartites.
  [Blondel2008] Blondel et al. (2008). Fast unfolding of communities in large
                networks. Journal of Statistical Mechanics.
                community_id_auto calculé par Louvain sur graphe garage/assuré.
  [Xu2023]      Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
                flag_doublon et community_score font partie des 13 features
                communes pour M_makora_dif.

DÉCISIONS DE CONCEPTION :
  - Symétrique à features_reseau.py Santé : même structure, même patterns.
  - expert_garage_correlation est spécifique à l'Auto — pas d'équivalent Santé.
  - Toutes les valeurs nulles -> 0.0 (pas de NaN dans l'IF).
  - Invariant : result.name == clé du registre FEATURE_RESEAU_FUNCTIONS_AUTO.

CHANGEMENTS v1.2.0 (Scénario A) :
  - Clé "flag_doublon_auto"    -> "flag_doublon" (feature commune)
  - Clé "community_score_auto" -> "community_score" (feature commune)
  - .rename() ajouté dans les 2 fonctions renommées
  - expert_garage_correlation : clé inchangée (feature spécifique Auto)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ─── Feature 1 — Doublon de déclaration ───────────────────────────────────────

def compute_flag_doublon_auto(df: pd.DataFrame) -> pd.Series:
    """
    Retourne 1 si le sinistre est une double déclaration, 0 sinon.

    Source : colonne Flag_Doublon_Auto ajoutée par t10_0_enrich_auto.py.
    Fallback : 0 si la colonne est absente (pipeline ne crashe pas).

    Feature commune Santé/Auto : "flag_doublon" [Xu2023].
    [Viaene2002] : les doublons représentent ~2% des sinistres auto frauduleux.

    Returns:
        pd.Series nommée "flag_doublon", dtype int8, valeurs 0 ou 1.
    """
    if "Flag_Doublon_Auto" not in df.columns:
        return pd.Series(0, index=df.index, dtype="int8").rename("flag_doublon")
    return df["Flag_Doublon_Auto"].fillna(False).astype("int8").rename("flag_doublon")


# ─── Feature 2 — Score de communauté suspecte ─────────────────────────────────

def compute_community_score_auto(df: pd.DataFrame) -> pd.Series:
    """
    Score d'appartenance à une communauté garage/assuré frauduleuse [0.0 - 1.0].

    Même calcul que compute_community_score_sante :
      - community_id_auto == 0 -> score = 0.0
      - community_id_auto > 0  -> normalisé par taille max de communauté

    Feature commune Santé/Auto : "community_score" [Xu2023].
    [Jiang2014] : dans les réseaux de fraude auto, les communautés typiques
    regroupent 1-3 garages et 15-40 assurés complices.
    [Blondel2008] : community_id_auto calculé par Louvain sur graphe
    bipartite garage/assuré (T13.1).

    Returns:
        pd.Series nommée "community_score", dtype float32, valeurs [0.0, 1.0].
    """
    if "community_id_auto" not in df.columns:
        return pd.Series(0.0, index=df.index, dtype="float32").rename("community_score")

    comm_id = df["community_id_auto"].fillna(0).astype(int)
    comm_sizes = comm_id[comm_id > 0].value_counts()
    max_size = comm_sizes.max() if len(comm_sizes) > 0 else 1

    def _score(cid: int) -> float:
        if cid == 0:
            return 0.0
        size = comm_sizes.get(cid, 1)
        return float(np.clip(0.1 + 0.9 * (size / max_size), 0.0, 1.0))

    return comm_id.map(_score).astype("float32").rename("community_score")


# ─── Feature 3 — Corrélation expert/garage ────────────────────────────────────

def compute_expert_garage_correlation(df: pd.DataFrame) -> pd.Series:
    """
    Mesure si un expert valide systématiquement les mêmes garages.

    Calcul : pour chaque paire (ID_Expert_Stable, ID_Garage),
    compte le nombre de sinistres. Un expert normal voit des garages variés.
    Un expert corrompu valide quasi-exclusivement un ou deux garages.

    Score = nb_sinistres_paire / nb_sinistres_expert_total
    Proche de 1.0 si l'expert est lié à un seul garage.
    Proche de 0.0 si l'expert est distribué sur de nombreux garages.

    Feature spécifique Auto (pas d'équivalent Santé).
    [Viaene2002] : la corrélation expert-réparateur est le signal de
    collusion le plus fort dans les données auto françaises.

    Returns:
        pd.Series float32, valeurs [0.0, 1.0].
    """
    col_exp = "ID_Expert_Stable"
    col_gar = "ID_Garage"

    if col_exp not in df.columns or col_gar not in df.columns:
        return pd.Series(0.0, index=df.index, dtype="float32")

    # Compte par paire expert/garage [Jiang2014]
    pair_counts = df.groupby([col_exp, col_gar]).size().rename("pair_count")
    expert_totals = df.groupby(col_exp).size().rename("expert_total")

    df_tmp = df[[col_exp, col_gar]].copy()
    df_tmp = df_tmp.join(pair_counts, on=[col_exp, col_gar])
    df_tmp = df_tmp.join(expert_totals, on=col_exp)

    correlation = (df_tmp["pair_count"] / df_tmp["expert_total"]).fillna(0.0)
    return correlation.astype("float32")


# ─── Registre YAML-driven ─────────────────────────────────────────────────────
# Clés = noms des features tels que déclarés dans auto.yaml v1.2.0.
# Invariant : result.name == clé pour flag_doublon et community_score.
# Scénario A : 2 renommages (flag_doublon_auto, community_score_auto).

FEATURE_RESEAU_FUNCTIONS_AUTO: dict[str, callable] = {
    "flag_doublon":              compute_flag_doublon_auto,       # était flag_doublon_auto
    "community_score":           compute_community_score_auto,    # était community_score_auto
    "expert_garage_correlation": compute_expert_garage_correlation,  # inchangé
}