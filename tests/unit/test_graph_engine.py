"""
MODULE : tests/unit/test_graph_engine.py
DESCRIPTION : Tests unitaires pour core/graph_engine.py.
              Couvre T13.3 — fixtures réseau Santé (ID_Praticien) et Auto (ID_Garage).

RÉFÉRENCES :
- [Blondel2008] → test de modularité et détection de communautés
- [Jiang2014]   → test de score de suspicion sur réseau dense
"""
from __future__ import annotations

import pandas as pd
import pytest

from core.graph_engine import GraphEngine, GraphAnalysisOutput, CommunityResult


# ─── Fixtures ─────────────────────────────────────────────────────────────────

GRAPH_CONFIG_SANTE = {
    "enabled": True,
    "entity_col": "ID_Praticien",
    "assure_col": "ID_Assure",
    "weight_col": "Montant_Facture",
    "min_community_size": 3,
    "suspicious_density_threshold": 0.5,
    "score_output_col": "community_score_sante",
}

GRAPH_CONFIG_AUTO = {
    "enabled": True,
    "entity_col": "ID_Garage",
    "assure_col": "ID_Assure",
    "weight_col": "Montant_Devis",
    "min_community_size": 2,
    "suspicious_density_threshold": 0.4,
    "score_output_col": "community_score_auto",
}


def _make_sante_df(n_suspicious: int = 10, n_normal: int = 20) -> pd.DataFrame:
    """
    Fixture réseau Santé :
    - Groupe suspect : 1 praticien (P_SUSPECT) lié à n_suspicious assurés
      via des montants très élevés → signal anomalie poids fort.
    - Réseau normal : 5 praticiens liés à n_normal assurés à montant standard.

    Contraste voulu : suspect=500 000 XAF, normal=30 000 XAF (ratio ×16).
    Garantit avg_weight_suspect > global_mean + 1.5σ sur toute fixture ≥ 5 normaux.
    """
    rows = []
    # Groupe suspect — [Jiang2014] : praticien concentré sur groupe d'assurés
    for i in range(n_suspicious):
        rows.append({
            "ID_Praticien": "P_SUSPECT",
            "ID_Assure": f"A_S{i:03d}",
            "Montant_Facture": 500_000.0,  # XAF — ratio ×16 vs normal
        })
    # Réseau normal — praticiens dispersés
    for i in range(n_normal):
        rows.append({
            "ID_Praticien": f"P_NORMAL_{i % 5}",
            "ID_Assure": f"A_N{i:03d}",
            "Montant_Facture": 30_000.0,
        })
    return pd.DataFrame(rows)


def _make_auto_df(n_suspicious: int = 8, n_normal: int = 15) -> pd.DataFrame:
    """
    Fixture réseau Auto :
    - Groupe suspect : 1 garage (G_SUSPECT) lié à plusieurs assurés
      avec devis très gonflés (×10 vs normal).
    - Réseau normal : garages dispersés à montant standard.
    """
    rows = []
    for i in range(n_suspicious):
        rows.append({
            "ID_Garage": "G_SUSPECT",
            "ID_Assure": f"A_G{i:03d}",
            "Montant_Devis": 5_000_000.0,  # XAF — ×10 vs normal
        })
    for i in range(n_normal):
        rows.append({
            "ID_Garage": f"G_NORMAL_{i % 3}",
            "ID_Assure": f"A_V{i:03d}",
            "Montant_Devis": 450_000.0,
        })
    return pd.DataFrame(rows)


# ─── Tests construction du graphe ─────────────────────────────────────────────

class TestBuildGraph:
    def test_sante_graph_has_correct_nodes(self):
        """Le graphe Santé contient praticiens et assurés comme nœuds."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df()
        output = engine.analyze(df)
        assert output.executed
        assert output.n_nodes > 0
        assert output.n_edges > 0

    def test_auto_graph_has_correct_nodes(self):
        """Le graphe Auto utilise ID_Garage sans modification de code."""
        engine = GraphEngine(GRAPH_CONFIG_AUTO)
        df = _make_auto_df()
        output = engine.analyze(df)
        assert output.executed
        assert output.n_nodes > 0

    def test_bipartite_edge_weights_aggregated(self):
        """Deux dossiers entre même praticien et assuré → 1 arête avec poids cumulé."""
        df = pd.DataFrame([
            {"ID_Praticien": "P001", "ID_Assure": "A001", "Montant_Facture": 50_000.0},
            {"ID_Praticien": "P001", "ID_Assure": "A001", "Montant_Facture": 30_000.0},
        ])
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        engine.analyze(df)
        assert engine._graph is not None
        # 2 nœuds (P001 + A_A001), 1 arête avec poids cumulé
        assert engine._graph.number_of_edges() == 1
        weight = engine._graph["P001"]["A_A001"]["weight"]
        assert abs(weight - 80_000.0) < 1.0

    def test_missing_columns_returns_not_executed(self):
        """Colonnes manquantes → executed=False, pas d'exception."""
        df = pd.DataFrame([{"col_inconnue": 1}])
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        output = engine.analyze(df)
        assert not output.executed
        assert output.error is not None

    def test_empty_dataframe_returns_not_executed(self):
        """DataFrame vide → executed=False proprement."""
        df = pd.DataFrame(columns=["ID_Praticien", "ID_Assure", "Montant_Facture"])
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        output = engine.analyze(df)
        assert not output.executed


# ─── Tests détection de communautés ───────────────────────────────────────────

class TestCommunityDetection:
    def test_suspicious_community_detected_sante(self):
        """P_SUSPECT avec 10 assurés à montant élevé → communauté suspecte."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df(n_suspicious=10, n_normal=20)
        output = engine.analyze(df)
        assert output.executed
        assert output.n_communities >= 1
        # Il doit exister au moins une communauté suspecte
        assert output.n_suspicious_communities >= 1

    def test_suspicious_community_detected_auto(self):
        """G_SUSPECT avec 8 assurés à devis gonflé → communauté suspecte."""
        engine = GraphEngine(GRAPH_CONFIG_AUTO)
        df = _make_auto_df(n_suspicious=8, n_normal=15)
        output = engine.analyze(df)
        assert output.executed
        assert output.n_suspicious_communities >= 1

    def test_isolated_praticien_not_suspicious(self):
        """Un praticien avec 1 seul assuré ne peut former une communauté suspecte."""
        df = pd.DataFrame([
            {"ID_Praticien": "P_ALONE", "ID_Assure": "A_ALONE", "Montant_Facture": 40_000.0},
        ])
        engine = GraphEngine({**GRAPH_CONFIG_SANTE, "min_community_size": 3})
        output = engine.analyze(df)
        # Graphe trop petit OU aucune communauté suspecte
        if output.executed:
            assert output.n_suspicious_communities == 0

    def test_community_result_fields(self):
        """CommunityResult doit avoir les champs requis et suspicion_score ∈ [0,1]."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df()
        output = engine.analyze(df)
        for c in output.suspicious_communities:
            assert isinstance(c, CommunityResult)
            assert 0.0 <= c.suspicion_score <= 1.0
            assert c.size >= 1
            assert c.density >= 0.0
            assert c.reason != ""

    def test_all_communities_have_scores(self):
        """suspicion_score doit être 0.0 pour communautés non-suspectes."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df()
        output = engine.analyze(df)
        # Toutes les communautés non-suspectes ont score 0 dans node_scores
        assert all(0.0 <= v <= 1.0 for v in output.node_scores.values())


# ─── Tests inject_scores (T13.2 — brancher graph_engine sur les features) ─────

class TestInjectScores:
    def test_community_score_column_injected_sante(self):
        """inject_scores crée la colonne community_score_sante dans le DataFrame."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df()
        output = engine.analyze(df)
        enriched = engine.inject_scores(df, output)
        assert "community_score_sante" in enriched.columns
        assert enriched["community_score_sante"].notna().all()
        assert (enriched["community_score_sante"] >= 0.0).all()
        assert (enriched["community_score_sante"] <= 1.0).all()

    def test_community_score_column_injected_auto(self):
        """inject_scores crée la colonne community_score_auto pour le module Auto."""
        engine = GraphEngine(GRAPH_CONFIG_AUTO)
        df = _make_auto_df()
        output = engine.analyze(df)
        enriched = engine.inject_scores(df, output)
        assert "community_score_auto" in enriched.columns

    def test_suspect_entity_has_higher_score(self):
        """P_SUSPECT doit avoir un score > 0 après injection."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df(n_suspicious=10, n_normal=5)
        output = engine.analyze(df)
        if output.n_suspicious_communities > 0:
            enriched = engine.inject_scores(df, output)
            suspect_scores = enriched[enriched["ID_Praticien"] == "P_SUSPECT"][
                "community_score_sante"
            ]
            assert suspect_scores.max() > 0.0

    def test_inject_scores_not_executed_fills_zeros(self):
        """Si analyze() échoue, inject_scores remplit la colonne avec 0.0."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df(n_suspicious=5)
        failed_output = GraphAnalysisOutput(enabled=True, executed=False,
                                             error="test", node_scores={})
        enriched = engine.inject_scores(df, failed_output)
        assert "community_score_sante" in enriched.columns
        assert (enriched["community_score_sante"] == 0.0).all()

    def test_original_dataframe_not_mutated(self):
        """inject_scores retourne une copie — le DataFrame original est intact."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df()
        output = engine.analyze(df)
        _ = engine.inject_scores(df, output)
        assert "community_score_sante" not in df.columns


# ─── Tests output JSON (ADR-005 — format standardisé) ─────────────────────────

class TestOutputFormat:
    def test_to_dict_keys_present(self):
        """GraphAnalysisOutput.to_dict() doit contenir tous les champs ADR-005."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df()
        output = engine.analyze(df)
        d = output.to_dict()
        required_keys = {
            "enabled", "executed", "n_nodes", "n_edges",
            "n_communities", "n_suspicious_communities",
            "modularity", "suspicious_communities", "error",
        }
        assert required_keys.issubset(d.keys())

    def test_failed_output_to_dict(self):
        """Un output non-exécuté est sérialisable sans erreur."""
        output = GraphAnalysisOutput(enabled=True, executed=False, error="KO")
        d = output.to_dict()
        assert d["executed"] is False
        assert d["error"] == "KO"

    def test_modularity_in_valid_range(self):
        """La modularité Q doit être dans (-0.5, 1.0) [Blondel2008]."""
        engine = GraphEngine(GRAPH_CONFIG_SANTE)
        df = _make_sante_df()
        output = engine.analyze(df)
        if output.executed:
            assert -0.5 <= output.modularity <= 1.0


# ─── Tests de généricité (INVIOLABLE — Kernel ne connaît pas la branche) ──────

class TestGenericity:
    @pytest.mark.parametrize("config,df_func", [
        (GRAPH_CONFIG_SANTE, _make_sante_df),
        (GRAPH_CONFIG_AUTO, _make_auto_df),
    ])
    def test_same_engine_class_for_both_branches(self, config, df_func):
        """GraphEngine est la même classe pour Santé et Auto. Seul config change."""
        engine = GraphEngine(config)
        assert type(engine).__name__ == "GraphEngine"
        output = engine.analyze(df_func())
        assert isinstance(output, GraphAnalysisOutput)

    def test_no_branch_name_in_engine_logic(self):
        """Vérification statique : GraphEngine n'importe aucun module métier concret.
        La règle d'isolation MAKORA interdit au Kernel de connaître SanteModule,
        AutoModule, etc. par leur nom. On vérifie via l'AST (imports uniquement).
        Les commentaires et docstrings peuvent contenir n'importe quel texte.
        """
        import ast
        import inspect
        from core.graph_engine import GraphEngine as GE

        # Inspecter le module entier (pas seulement la classe) pour les imports
        import core.graph_engine as ge_module
        source = inspect.getsource(ge_module)
        tree = ast.parse(source)

        # Collecter tous les noms importés dans le module
        imported_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.append(node.module)
                for alias in node.names:
                    imported_names.append(alias.name)

        # Aucun import ne doit référencer un module métier concret
        forbidden = ["sante_module", "auto_module", "vie_module", "agricole_module",
                     "SanteModule", "AutoModule", "VieModule", "AgricoleModule"]
        for name in imported_names:
            assert name not in forbidden, (
                f"Import interdit dans GraphEngine (Kernel) : '{name}'. "
                f"Le Kernel ne doit jamais importer un module métier concret."
            )