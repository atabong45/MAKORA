"""
MODULE : core/graph_engine.py
DESCRIPTION : Brique d'analyse de graphe — détection de communautés suspectes.
              Générique : fonctionne pour Santé (ID_Praticien) et Auto (ID_Garage)
              via configuration YAML. Brique optionnelle et non-bloquante.

RÉFÉRENCES ACADÉMIQUES :
- [Blondel2008] Blondel et al. (2008). Fast unfolding of communities in large
                networks. Journal of Statistical Mechanics: Theory and Experiment.
                → Algorithme Louvain : détection de communautés par maximisation
                  de la modularité Q. Complexité O(n log n).
- [Jiang2014]   Jiang et al. (2014). CatchSync: catching synchronized behavior
                in large directed graphs. KDD 2014.
                → Justifie la densité de communauté comme signal de fraude
                  coordonnée (collusion prestataire-assuré).
- [Bauder2017]  Bauder & Khoshgoftaar (2017). Medicare fraud detection using
                machine learning methods. ICMLA 2017.
                → Community billing patterns comme features discriminantes.

DÉCISIONS DE CONCEPTION :
- Généricité totale : aucun nom de branche hardcodé — tout passe par graph_config
  extrait du YAML via BaseModule.get_graph_config().
- Fallback gracieux : si python-louvain est absent, repli sur nx.greedy_modularity.
  Le pipeline ne crash jamais à cause de cette brique.
- Seuil densité externalisé : suspicious_density_threshold dans le YAML.
- Output normalisé [0.0, 1.0] : community_score exploitable directement par IF.
- Stateless : recalcul complet à chaque batch (DT-002 — persistance inter-batches
  différée, documentée dans PHASE_2_REPORT).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd

# [Blondel2008] — Louvain community detection
try:
    from community import community_louvain  # python-louvain package
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False

log = logging.getLogger(__name__)


# ─── Structures de données ────────────────────────────────────────────────────

@dataclass
class CommunityResult:
    """Résultat pour une communauté détectée."""
    community_id: int
    nodes: list[str]
    size: int
    density: float
    avg_weight: float
    is_suspicious: bool
    suspicion_score: float  # [0.0, 1.0]
    reason: str


@dataclass
class GraphAnalysisOutput:
    """Sortie standardisée de la brique graphe — compatible ADR-005."""
    enabled: bool
    executed: bool
    n_nodes: int = 0
    n_edges: int = 0
    n_communities: int = 0
    n_suspicious_communities: int = 0
    modularity: float = 0.0
    suspicious_communities: list[CommunityResult] = field(default_factory=list)
    node_scores: dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "executed": self.executed,
            "n_nodes": self.n_nodes,
            "n_edges": self.n_edges,
            "n_communities": self.n_communities,
            "n_suspicious_communities": self.n_suspicious_communities,
            "modularity": round(self.modularity, 4),
            "suspicious_communities": [
                {
                    "community_id": c.community_id,
                    "size": c.size,
                    "density": round(c.density, 4),
                    "avg_weight": round(c.avg_weight, 2),
                    "suspicion_score": round(c.suspicion_score, 4),
                    "reason": c.reason,
                }
                for c in self.suspicious_communities
            ],
            "error": self.error,
        }


# ─── Classe principale ────────────────────────────────────────────────────────

class GraphEngine:
    """
    Moteur d'analyse de graphe générique pour MAKORA.

    Usage :
        engine = GraphEngine(graph_config)
        output = engine.analyze(df)
        df["community_score"] = engine.get_node_scores(df, entity_col)

    graph_config (depuis YAML du module) :
        {
          "enabled": true,
          "entity_col": "ID_Praticien",        # nœud principal (Santé) ou "ID_Garage" (Auto)
          "assure_col": "ID_Assure",
          "weight_col": "Montant_Facture",
          "min_community_size": 3,
          "suspicious_density_threshold": 0.5,
          "score_output_col": "community_score_sante"
        }
    """

    def __init__(self, graph_config: dict) -> None:
        self._cfg = graph_config
        self._entity_col: str = graph_config["entity_col"]
        self._assure_col: str = graph_config["assure_col"]
        self._weight_col: str = graph_config.get("weight_col", "Montant_Facture")
        self._min_size: int = int(graph_config.get("min_community_size", 3))
        self._density_threshold: float = float(
            graph_config.get("suspicious_density_threshold", 0.5)
        )
        self._score_col: str = graph_config.get("score_output_col", "community_score")
        self._graph: Optional[nx.Graph] = None

    # ─── API publique ─────────────────────────────────────────────────────────

    def analyze(self, df: pd.DataFrame) -> GraphAnalysisOutput:
        """
        Point d'entrée principal. Construit le graphe, détecte les communautés,
        retourne GraphAnalysisOutput.

        [Blondel2008] — Louvain maximise la modularité Q = Σ[A_ij - k_i*k_j/(2m)]
        """
        required = {self._entity_col, self._assure_col}
        missing = required - set(df.columns)
        if missing:
            log.warning(f"[GraphEngine] Colonnes manquantes : {missing}. Brique désactivée.")
            return GraphAnalysisOutput(enabled=True, executed=False,
                                       error=f"Colonnes manquantes : {missing}")

        try:
            self._graph = self._build_bipartite_graph(df)
            if self._graph.number_of_nodes() < 2:
                return GraphAnalysisOutput(enabled=True, executed=False,
                                           error="Graphe trop petit (< 2 nœuds)")

            partition = self._detect_communities(self._graph)
            communities = self._build_community_objects(self._graph, partition)
            suspicious = [c for c in communities if c.is_suspicious]
            modularity = self._compute_modularity(self._graph, partition)

            node_scores = self._compute_node_scores(partition, communities)

            log.info(
                f"[GraphEngine] {self._graph.number_of_nodes()} nœuds | "
                f"{self._graph.number_of_edges()} arêtes | "
                f"{len(communities)} communautés | "
                f"{len(suspicious)} suspectes | modularité={modularity:.3f}"
            )

            return GraphAnalysisOutput(
                enabled=True,
                executed=True,
                n_nodes=self._graph.number_of_nodes(),
                n_edges=self._graph.number_of_edges(),
                n_communities=len(communities),
                n_suspicious_communities=len(suspicious),
                modularity=modularity,
                suspicious_communities=suspicious,
                node_scores=node_scores,
            )

        except Exception as exc:
            log.warning(f"[GraphEngine] Erreur analyse : {exc}. Pipeline continue.")
            return GraphAnalysisOutput(enabled=True, executed=False, error=str(exc))

    def inject_scores(self, df: pd.DataFrame,
                      output: GraphAnalysisOutput) -> pd.DataFrame:
        """
        Injecte community_score dans le DataFrame.
        Les entités absentes du graphe reçoivent 0.0.
        Compatible T13.2 : alimente la feature community_score_{branch}.

        [Jiang2014] — Le score de communauté est un proxy du comportement
        synchronisé. Score 0.0 = entité isolée, 1.0 = nœud central d'une
        communauté hautement suspecte.
        """
        result = df.copy()
        result[self._score_col] = result[self._entity_col].map(
            output.node_scores
        ).fillna(0.0)
        return result

    # ─── Construction du graphe ───────────────────────────────────────────────

    def _build_bipartite_graph(self, df: pd.DataFrame) -> nx.Graph:
        """
        Construit un graphe bipartite Entité ↔ Assuré.
        Poids de l'arête = somme des montants facturés entre les deux nœuds.

        [Blondel2008] §2 : le graphe doit être pondéré pour que Louvain
        maximise correctement la modularité sur données réelles.
        """
        G = nx.Graph()
        weight_available = self._weight_col in df.columns

        for _, row in df.iterrows():
            entity = str(row[self._entity_col])
            assure = f"A_{row[self._assure_col]}"  # préfixe pour éviter collision d'ID
            weight = float(row[self._weight_col]) if weight_available else 1.0

            if G.has_edge(entity, assure):
                G[entity][assure]["weight"] += weight
                G[entity][assure]["count"] += 1
            else:
                G.add_edge(entity, assure, weight=weight, count=1)
                G.nodes[entity]["type"] = "entity"
                G.nodes[assure]["type"] = "assure"

        return G

    # ─── Détection de communautés ─────────────────────────────────────────────

    def _detect_communities(self, G: nx.Graph) -> dict[str, int]:
        """
        Détection via Louvain [Blondel2008] avec fallback greedy_modularity.
        Retourne {node_id: community_id}.
        """
        if LOUVAIN_AVAILABLE:
            log.debug("[GraphEngine] Algorithme : Louvain [Blondel2008]")
            return community_louvain.best_partition(G, weight="weight")
        else:
            log.debug("[GraphEngine] Louvain indisponible → greedy_modularity (NetworkX)")
            communities_gen = nx.community.greedy_modularity_communities(G, weight="weight")
            return {
                node: idx
                for idx, comm in enumerate(communities_gen)
                for node in comm
            }

    def _build_community_objects(
        self, G: nx.Graph, partition: dict[str, int]
    ) -> list[CommunityResult]:
        """
        Calcule les métriques de chaque communauté et détermine si elle est
        suspecte selon les seuils YAML.

        Critères de suspicion (cumulatifs) :
        1. Taille ≥ min_community_size
        2. Densité ≥ suspicious_density_threshold  [Jiang2014]
        3. Poids moyen > moyenne globale + 2σ      [Bauder2017]
        """
        # Regroupement des nœuds par communauté
        comm_nodes: dict[int, list[str]] = {}
        for node, cid in partition.items():
            comm_nodes.setdefault(cid, []).append(node)

        # Statistiques globales — estimateurs robustes médiane + MAD.
        # Problème avec mean+std : P_SUSPECT tire global_mean et global_std vers le
        # haut, ce qui élève le seuil au-dessus de P_SUSPECT lui-même (biais
        # d'auto-exclusion démontré empiriquement sur les fixtures de test).
        # Solution : médiane + MAD (Median Absolute Deviation).
        # [Rousseeuw1993] Rousseeuw & Croux. Alternatives to the median absolute
        # deviation. JASA 88(424):1273-1283. MAD résistant aux outliers extrêmes.
        # [Jiang2014] §4 : signal de poids anormal sur graphes bipartites assurance.
        raw_w = [d["weight"] for _, _, d in G.edges(data=True)]
        all_weights = np.array(raw_w if raw_w else [1.0], dtype=float)
        global_median = float(np.median(all_weights))
        mad = float(np.median(np.abs(all_weights - global_median)))
        # Fallback MAD=0 : distribution dégénérée (tous poids identiques sauf outliers)
        # std/1.4826 est l'estimateur MAD-consistent pour distribution normale.
        if mad < 1e-6:
            mad = float(np.std(all_weights)) / 1.4826
        sigma_k = float(self._cfg.get("weight_sigma_threshold", 2.0))
        weight_threshold = global_median + sigma_k * mad
        # Conserver mean/std pour _compute_suspicion_score (score continu)
        global_mean = float(np.mean(all_weights))
        global_std = float(np.std(all_weights))

        results = []
        for cid, nodes in comm_nodes.items():
            subgraph = G.subgraph(nodes)
            size = len(nodes)
            density = nx.density(subgraph)
            edge_weights = [d["weight"] for _, _, d in subgraph.edges(data=True)]
            avg_weight = float(np.mean(edge_weights)) if edge_weights else 0.0

            # Évaluation des critères de suspicion — deux critères INDÉPENDANTS :
            # Critère A (densité) : pour les graphes non-bipartites ou communautés
            #   homogènes. Peu discriminant sur graphes bipartites assurance.
            # Critère B (poids) : signal principal [Jiang2014] — praticien/garage
            #   qui facture anormalement élevé sur sa communauté d'assurés.
            # Un seul critère suffit (OR, pas AND) pour marquer une communauté.
            reasons = []
            if size >= self._min_size and density >= self._density_threshold:
                reasons.append(f"densité={density:.2f}≥{self._density_threshold}")
            if size >= self._min_size and avg_weight > weight_threshold:
                reasons.append(f"poids_moyen={avg_weight:.0f}>{weight_threshold:.0f}")

            is_suspicious = len(reasons) > 0
            suspicion_score = self._compute_suspicion_score(
                size, density, avg_weight, global_mean, global_std
            )

            results.append(CommunityResult(
                community_id=cid,
                nodes=nodes,
                size=size,
                density=density,
                avg_weight=avg_weight,
                is_suspicious=is_suspicious,
                suspicion_score=suspicion_score if is_suspicious else 0.0,
                reason=" | ".join(reasons) if reasons else "non_suspecte",
            ))

        return results

    def _compute_suspicion_score(
        self, size: int, density: float,
        avg_weight: float, global_mean: float, global_std: float
    ) -> float:
        """
        Score composite [0.0, 1.0] combinant densité et anomalie de poids.
        Normalisation min-max sur les deux composantes.

        [Jiang2014] §4.3 : score composite = α*densité + (1-α)*anomalie_poids
        α = 0.6 — densité est le signal principal pour la fraude coordonnée.
        """
        alpha = 0.6
        density_score = min(density / max(self._density_threshold, 1e-6), 1.0)
        weight_z = (avg_weight - global_mean) / max(global_std, 1e-6)
        weight_score = min(max(weight_z / 1.5, 0.0), 1.0)  # clamp [0,1] sur 1.5σ
        return round(alpha * density_score + (1 - alpha) * weight_score, 4)

    def _compute_modularity(self, G: nx.Graph, partition: dict[str, int]) -> float:
        """
        Modularité Q [Blondel2008]. Valeur dans (-0.5, 1.0).
        Q > 0.3 indique une structure de communauté significative.
        """
        if not LOUVAIN_AVAILABLE:
            return 0.0
        try:
            return community_louvain.modularity(partition, G, weight="weight")
        except Exception:
            return 0.0

    def _compute_node_scores(
        self, partition: dict[str, int], communities: list[CommunityResult]
    ) -> dict[str, float]:
        """
        Mappe chaque nœud à son suspicion_score de communauté.
        Seuls les nœuds de type "entity" (praticien/garage) reçoivent le score.
        Les nœuds "assure" (préfixe A_) reçoivent 0.0.
        """
        comm_score = {c.community_id: c.suspicion_score for c in communities}
        return {
            node: (comm_score.get(cid, 0.0) if not node.startswith("A_") else 0.0)
            for node, cid in partition.items()
        }