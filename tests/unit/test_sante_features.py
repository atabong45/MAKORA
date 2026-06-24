"""
TESTS : tests/unit/test_sante_features.py
DESCRIPTION : Tests unitaires des 5 fonctions V1 de modules/sante/features.py
              Miroir de test_sante_features_ext.py pour les features de base.

FONCTIONS TESTÉES :
  - compute_ratio_prix_mercuriale
  - compute_flag_incoherence_sexe_acte
  - compute_historique_ratio_praticien
  - compute_nb_sinistres_30j
  - compute_flag_weekend_care (Series nommée 'is_weekend_event' — Scénario A)

RÉFÉRENCES :
  - [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection.
  - [Viaene2002] Viaene et al. (2002). Automobile insurance fraud detection.
  - [Subudhi2017] Subudhi & Panigrahi (2017). Automobile insurance fraud.

NOTE v0.5.0 (Scénario A) :
  compute_flag_weekend_care conserve son nom de fonction interne mais
  retourne désormais une Series nommée 'is_weekend_event' (clé harmonisée
  avec AutoModule pour M_makora_dif [Xu2023]). Les tests vérifient ce nom.

Lancer :
    pytest tests/unit/test_sante_features.py -v
"""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from modules.sante.features import (
    compute_flag_incoherence_sexe_acte,
    compute_flag_weekend_care,
    compute_historique_ratio_praticien,
    compute_nb_sinistres_30j,
    compute_ratio_prix_mercuriale,
)


# ===========================================================================
# Fixtures communes
# ===========================================================================

@pytest.fixture
def df_complet():
    """DataFrame avec toutes les colonnes utilisées par features.py."""
    return pd.DataFrame({
        "ID_Sinistre":      ["S001", "S002", "S003", "S004", "S005"],
        "ID_Assure":        ["A001", "A001", "A002", "A003", "A001"],
        "ID_Praticien":     ["P001", "P001", "P002", "P003", "P001"],
        "Code_Acte":        ["76601001", "A_GYN_001", "76601001", "A_GYN_002", "76601001"],
        "Montant_Facture":  [100.0, 300.0, 200.0, 150.0, 100.0],
        "Prix_Unitaire_Ref":[100.0, 100.0, 100.0, 100.0, 100.0],
        "Sexe_Assure":      ["M", "M", "F", "F", "M"],
        "Date_Soin": pd.to_datetime([
            "2025-01-13",   # lundi
            "2025-01-11",   # samedi ← weekend
            "2025-01-15",   # mercredi
            "2025-01-12",   # dimanche ← weekend
            "2025-01-14",   # mardi
        ]),
        # ratio déjà calculé pour compute_historique_ratio_praticien
        "ratio_prix_mercuriale": [1.0, 3.0, 2.0, 1.5, 1.0],
    })


@pytest.fixture
def df_minimal():
    """DataFrame sans colonnes optionnelles — teste la dégradation gracieuse."""
    return pd.DataFrame({
        "ID_Sinistre":     ["S001", "S002"],
        "Montant_Facture": [100.0, 200.0],
    })


# ===========================================================================
# Tests — compute_ratio_prix_mercuriale
# ===========================================================================

class TestComputeRatioPrixMercuriale:
    """
    [Bauder2017] : ratio_prix_mercuriale est la feature CRITIQUE pour
    détecter la surfacturation vs la mercuriale CIMA.
    """

    def test_ratio_normal(self, df_complet):
        result = compute_ratio_prix_mercuriale(df_complet)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df_complet)

    def test_ratio_exact_calcul(self):
        """100 / 100 = 1.0 ; 300 / 100 = 3.0 — surfacturation 3x."""
        df = pd.DataFrame({
            "Montant_Facture":  [100.0, 300.0, 50.0],
            "Prix_Unitaire_Ref":[100.0, 100.0, 100.0],
        })
        result = compute_ratio_prix_mercuriale(df)
        assert pytest.approx(result.iloc[0]) == 1.0
        assert pytest.approx(result.iloc[1]) == 3.0
        assert pytest.approx(result.iloc[2]) == 0.5

    def test_ratio_sans_colonne_prix_ref(self, df_minimal):
        """Dégradation gracieuse : Prix_Unitaire_Ref absente → valeur neutre (1.0)."""
        result = compute_ratio_prix_mercuriale(df_minimal)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df_minimal)
        assert not result.isna().any(), "Ne doit pas contenir de NaN"

    def test_ratio_prix_ref_zero_ne_crash_pas(self):
        """Division par zéro sur Prix_Unitaire_Ref=0 → gestion propre (fillna 1.0)."""
        df = pd.DataFrame({
            "Montant_Facture":  [100.0],
            "Prix_Unitaire_Ref":[0.0],
        })
        result = compute_ratio_prix_mercuriale(df)
        assert isinstance(result, pd.Series)
        assert len(result) == 1

    def test_retourne_series_nommee(self, df_complet):
        result = compute_ratio_prix_mercuriale(df_complet)
        assert result.name == "ratio_prix_mercuriale"

    def test_ratio_positif(self, df_complet):
        """Tous les ratios doivent être positifs ou nuls."""
        result = compute_ratio_prix_mercuriale(df_complet)
        assert (result.dropna() >= 0).all()


# ===========================================================================
# Tests — compute_flag_incoherence_sexe_acte
# ===========================================================================

class TestComputeFlagIncoherenceSexeActe:
    """
    [Bauder2017] : incohérence sexe/acte = signal fort de phantom billing
    ou d'usurpation d'identité (acte gynécologique facturé pour un homme).
    Dette DT-003 : liste _ACTES_FEMININS incomplète (ASAC partiel).
    """

    def test_homme_acte_feminin_flag_1(self):
        """Homme + acte gynécologique → flag=1.
        Utilise GYNECO_001 — nomenclature réelle de _ACTES_FEMININS dans features.py.
        """
        df = pd.DataFrame({
            "Sexe_Assure": ["M"],
            "Code_Acte":   ["GYNECO_001"],
        })
        result = compute_flag_incoherence_sexe_acte(df)
        assert result.iloc[0] == 1

    def test_femme_acte_feminin_flag_0(self):
        """Femme + acte gynécologique → flag=0 (cohérent)."""
        df = pd.DataFrame({
            "Sexe_Assure": ["F"],
            "Code_Acte":   ["GYNECO_001"],
        })
        result = compute_flag_incoherence_sexe_acte(df)
        assert result.iloc[0] == 0

    def test_acte_neutre_flag_0(self):
        """Acte non listé dans les listes genrées → flag=0 (pas de fausse alerte)."""
        df = pd.DataFrame({
            "Sexe_Assure": ["M", "F"],
            "Code_Acte":   ["76601001", "76601001"],
        })
        result = compute_flag_incoherence_sexe_acte(df)
        assert (result == 0).all()

    def test_sans_colonne_sexe(self, df_minimal):
        """Dégradation gracieuse : Sexe_Assure absent → flag=0 partout."""
        result = compute_flag_incoherence_sexe_acte(df_minimal)
        assert isinstance(result, pd.Series)
        assert (result == 0).all()

    def test_retourne_series_nommee(self, df_complet):
        result = compute_flag_incoherence_sexe_acte(df_complet)
        assert result.name == "flag_incoherence_sexe_acte"

    def test_valeurs_binaires(self, df_complet):
        """La feature est strictement binaire : {0, 1}."""
        result = compute_flag_incoherence_sexe_acte(df_complet)
        assert set(result.unique()).issubset({0, 1})


# ===========================================================================
# Tests — compute_historique_ratio_praticien
# ===========================================================================

class TestComputeHistoriqueRatioPraticien:
    """
    [Subudhi2017] : l'historique du praticien est un signal de comportement
    systématique — un praticien qui surfacture régulièrement a un ratio
    moyen élevé sur l'ensemble du batch courant.
    Dette DT-002 : stateless — fenêtre = batch courant uniquement.
    """

    def test_praticien_surfactureur_ratio_eleve(self):
        """Praticien P001 avec ratios 3.0, 3.0, 3.0 → historique = 3.0."""
        df = pd.DataFrame({
            "ID_Praticien":         ["P001", "P001", "P001"],
            "ratio_prix_mercuriale":[3.0,    3.0,    3.0],
        })
        result = compute_historique_ratio_praticien(df)
        for val in result:
            assert val == pytest.approx(3.0)

    def test_praticien_normal_ratio_un(self):
        """Praticien P002 avec ratio=1.0 partout → historique = 1.0."""
        df = pd.DataFrame({
            "ID_Praticien":         ["P002", "P002"],
            "ratio_prix_mercuriale":[1.0,    1.0],
        })
        result = compute_historique_ratio_praticien(df)
        for val in result:
            assert val == pytest.approx(1.0)

    def test_praticiens_differents_isoles(self):
        """Deux praticiens distincts ont des historiques indépendants."""
        df = pd.DataFrame({
            "ID_Praticien":         ["P001", "P002"],
            "ratio_prix_mercuriale":[4.0,    1.0],
        })
        result = compute_historique_ratio_praticien(df)
        assert result.iloc[0] == pytest.approx(4.0)
        assert result.iloc[1] == pytest.approx(1.0)

    def test_sans_colonne_ratio(self, df_minimal):
        """Dégradation gracieuse : ratio_prix_mercuriale absent → valeur neutre."""
        result = compute_historique_ratio_praticien(df_minimal)
        assert isinstance(result, pd.Series)
        assert not result.isna().any()

    def test_retourne_series_nommee(self, df_complet):
        result = compute_historique_ratio_praticien(df_complet)
        assert result.name == "historique_ratio_praticien"

    def test_longueur_egale_input(self, df_complet):
        result = compute_historique_ratio_praticien(df_complet)
        assert len(result) == len(df_complet)


# ===========================================================================
# Tests — compute_nb_sinistres_30j
# ===========================================================================

class TestComputeNbSinistres30j:
    """
    [Viaene2002] : la fréquence anormale de sinistres sur une fenêtre courte
    est un signal d'unbundling — découpage artificiel d'actes pour multiplier
    les remboursements.
    """

    def test_assure_avec_3_sinistres(self):
        """
        La fonction est un comptage cumulatif par assuré sur le batch courant.
        Chaque ligne = nb de sinistres de cet assuré jusqu'à cette date incluse.
        A001 : J1, J5, J10 → [1, 2, 3]  (croissant, dernier = 3)
        A002 : 1 seul dossier → [1]
        """
        df = pd.DataFrame({
            "ID_Assure": ["A001", "A001", "A001", "A002"],
            "Date_Soin": pd.to_datetime([
                "2025-01-01", "2025-01-05", "2025-01-10",
                "2025-01-01",
            ]),
        })
        result = compute_nb_sinistres_30j(df)
        a001_vals = list(result[df["ID_Assure"] == "A001"])
        a002_vals = list(result[df["ID_Assure"] == "A002"])
        assert a001_vals[-1] == 3, f"Dernier comptage A001 attendu 3, obtenu {a001_vals}"
        assert a001_vals == sorted(a001_vals), f"Comptage non monotone : {a001_vals}"
        assert a002_vals[0] == 1

    def test_assure_unique_retourne_1(self):
        """Un assuré avec un seul dossier → nb = 1."""
        df = pd.DataFrame({
            "ID_Assure": ["A001"],
            "Date_Soin": pd.to_datetime(["2025-06-01"]),
        })
        result = compute_nb_sinistres_30j(df)
        assert result.iloc[0] == 1

    def test_sans_colonne_assure(self, df_minimal):
        """Dégradation gracieuse : ID_Assure absent → valeur par défaut (1)."""
        result = compute_nb_sinistres_30j(df_minimal)
        assert isinstance(result, pd.Series)
        assert not result.isna().any()

    def test_retourne_series_nommee(self, df_complet):
        result = compute_nb_sinistres_30j(df_complet)
        assert result.name == "nb_sinistres_30j_assure"

    def test_valeurs_positives(self, df_complet):
        """Le nombre de sinistres est toujours >= 1."""
        result = compute_nb_sinistres_30j(df_complet)
        assert (result >= 1).all()

    def test_longueur_egale_input(self, df_complet):
        result = compute_nb_sinistres_30j(df_complet)
        assert len(result) == len(df_complet)


# ===========================================================================
# Tests — compute_flag_weekend_care (Series 'is_weekend_event' — Scénario A)
# ===========================================================================

class TestComputeFlagWeekendCare:
    """
    [Bauder2017] : soins du weekend sont associés à la facturation fictive
    antidatée dans les contextes où les cabinets sont fermés.
    0 = jour de semaine, 1 = weekend (samedi=5, dimanche=6).

    Scénario A : la fonction retourne une Series nommée 'is_weekend_event'
    (feature commune ★ avec AutoModule pour M_makora_dif [Xu2023]).
    """

    def test_samedi_flag_1(self):
        df = pd.DataFrame({
            "Date_Soin": pd.to_datetime(["2025-01-11"]),  # samedi
        })
        result = compute_flag_weekend_care(df)
        assert result.iloc[0] == 1

    def test_dimanche_flag_1(self):
        df = pd.DataFrame({
            "Date_Soin": pd.to_datetime(["2025-01-12"]),  # dimanche
        })
        result = compute_flag_weekend_care(df)
        assert result.iloc[0] == 1

    def test_lundi_flag_0(self):
        df = pd.DataFrame({
            "Date_Soin": pd.to_datetime(["2025-01-13"]),  # lundi
        })
        result = compute_flag_weekend_care(df)
        assert result.iloc[0] == 0

    def test_semaine_complete(self):
        """Lundi→dimanche : flags attendus = 0,0,0,0,0,1,1."""
        df = pd.DataFrame({
            "Date_Soin": pd.to_datetime([
                "2025-01-13",  # lundi
                "2025-01-14",  # mardi
                "2025-01-15",  # mercredi
                "2025-01-16",  # jeudi
                "2025-01-17",  # vendredi
                "2025-01-18",  # samedi
                "2025-01-19",  # dimanche
            ]),
        })
        result = compute_flag_weekend_care(df)
        expected = [0, 0, 0, 0, 0, 1, 1]
        assert list(result) == expected

    def test_sans_colonne_date(self, df_minimal):
        """Dégradation gracieuse : Date_Soin absente → flag=0 partout."""
        result = compute_flag_weekend_care(df_minimal)
        assert isinstance(result, pd.Series)
        assert (result == 0).all()

    def test_date_invalide_ne_crash_pas(self):
        """Date non parseable → dégradation sans exception."""
        df = pd.DataFrame({
            "Date_Soin": ["not-a-date", "2025-01-11"],
        })
        result = compute_flag_weekend_care(df)
        assert isinstance(result, pd.Series)
        assert len(result) == 2

    def test_retourne_series_nommee(self, df_complet):
        """Scénario A : la Series est nommée 'is_weekend_event'."""
        result = compute_flag_weekend_care(df_complet)
        assert result.name == "is_weekend_event"

    def test_valeurs_binaires(self, df_complet):
        result = compute_flag_weekend_care(df_complet)
        assert set(result.unique()).issubset({0, 1})


# ===========================================================================
# Tests transversaux — contrat commun aux 5 fonctions
# ===========================================================================

class TestContratCommun:
    """
    Vérifie les invariants partagés par toutes les fonctions de features.py :
    retour pd.Series, longueur conservée, pas de crash sur df_minimal.
    [Sculley2015] : robustesse > pureté — dégradation gracieuse obligatoire.

    Le tuple ALL_FUNCTIONS utilise la clé du registre FEATURE_FUNCTIONS_SANTE_V1.
    Pour is_weekend_event (Scénario A), la clé est 'is_weekend_event'.
    """

    ALL_FUNCTIONS = [
        ("ratio_prix_mercuriale",       compute_ratio_prix_mercuriale),
        ("flag_incoherence_sexe_acte",  compute_flag_incoherence_sexe_acte),
        ("historique_ratio_praticien",  compute_historique_ratio_praticien),
        ("nb_sinistres_30j_assure",     compute_nb_sinistres_30j),
        ("is_weekend_event",            compute_flag_weekend_care),
    ]

    @pytest.mark.parametrize("name,fn", ALL_FUNCTIONS)
    def test_retourne_series(self, name, fn, df_complet):
        result = fn(df_complet)
        assert isinstance(result, pd.Series), (
            f"{name} doit retourner pd.Series, reçu : {type(result)}"
        )

    @pytest.mark.parametrize("name,fn", ALL_FUNCTIONS)
    def test_longueur_conservee(self, name, fn, df_complet):
        result = fn(df_complet)
        assert len(result) == len(df_complet), (
            f"{name} : longueur résultat {len(result)} != input {len(df_complet)}"
        )

    @pytest.mark.parametrize("name,fn", ALL_FUNCTIONS)
    def test_degrade_gracieusement_sur_df_minimal(self, name, fn, df_minimal):
        """Aucune fonction ne doit lever d'exception sur un DataFrame minimal."""
        try:
            result = fn(df_minimal)
            assert isinstance(result, pd.Series)
        except Exception as e:
            pytest.fail(
                f"{name} lève une exception sur df_minimal : {type(e).__name__}: {e}"
            )

    @pytest.mark.parametrize("name,fn", ALL_FUNCTIONS)
    def test_ne_modifie_pas_input(self, name, fn, df_complet):
        """Les fonctions sont STATELESS — elles ne modifient pas le DataFrame d'entrée."""
        cols_avant = set(df_complet.columns)
        fn(df_complet)
        cols_apres = set(df_complet.columns)
        assert cols_avant == cols_apres, (
            f"{name} a modifié le DataFrame d'entrée. "
            f"Colonnes ajoutées : {cols_apres - cols_avant}"
        )

    @pytest.mark.parametrize("name,fn", ALL_FUNCTIONS)
    def test_pas_de_nan_sur_df_complet(self, name, fn, df_complet):
        """Sur un DataFrame complet, aucune feature ne doit contenir de NaN."""
        result = fn(df_complet)
        assert not result.isna().any(), (
            f"{name} contient {result.isna().sum()} NaN sur df_complet"
        )

    @pytest.mark.parametrize("name,fn", ALL_FUNCTIONS)
    def test_nom_series_egale_cle_registre(self, name, fn, df_complet):
        """
        Invariant YAML-driven : result.name == clé de FEATURE_FUNCTIONS_SANTE_V1.
        Vérifie en particulier que compute_flag_weekend_care retourne bien
        'is_weekend_event' (Scénario A) et non l'ancien 'flag_weekend_care'.
        """
        result = fn(df_complet)
        assert result.name == name, (
            f"Nom incohérent : clé registre='{name}', Series.name='{result.name}'"
        )


# ===========================================================================
# Test de cohérence du registre V1
# ===========================================================================

class TestRegistreV1:
    """Validation du registre FEATURE_FUNCTIONS_SANTE_V1 (Scénario A)."""

    def test_registre_contient_5_fonctions(self):
        from modules.sante.features import FEATURE_FUNCTIONS_SANTE_V1
        assert len(FEATURE_FUNCTIONS_SANTE_V1) == 5

    def test_cles_attendues(self):
        from modules.sante.features import FEATURE_FUNCTIONS_SANTE_V1
        attendues = {
            "ratio_prix_mercuriale",
            "flag_incoherence_sexe_acte",
            "historique_ratio_praticien",
            "nb_sinistres_30j_assure",
            "is_weekend_event",          # Scénario A : renommé depuis flag_weekend_care
        }
        assert set(FEATURE_FUNCTIONS_SANTE_V1.keys()) == attendues

    def test_ordre_ratio_avant_historique(self):
        """
        L'ordre du dict garantit que ratio_prix_mercuriale est calculé
        avant historique_ratio_praticien (dépendance aval) [Sculley2015].
        """
        from modules.sante.features import FEATURE_FUNCTIONS_SANTE_V1
        keys = list(FEATURE_FUNCTIONS_SANTE_V1.keys())
        assert keys.index("ratio_prix_mercuriale") < keys.index("historique_ratio_praticien")

    def test_noms_series_coherents(self, df_complet):
        """Invariant : result.name == clé du registre pour chaque fonction."""
        from modules.sante.features import FEATURE_FUNCTIONS_SANTE_V1
        for name, fn in FEATURE_FUNCTIONS_SANTE_V1.items():
            result = fn(df_complet)
            assert result.name == name, (
                f"Nom incohérent : registre='{name}', Series.name='{result.name}'"
            )