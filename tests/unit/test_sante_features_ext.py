"""
TESTS : tests/unit/test_sante_features_ext.py
DESCRIPTION : Tests unitaires des 12 fonctions de features_ext.py (v0.5.0).
              Coverage cible : 100% des fonctions, tous les cas limites.

HISTORIQUE :
  v0.2.0 — 9 fonctions originales
  v0.5.0 — 12 fonctions :
    Renommages (Scénarios A/C) :
      delai_soin_depot_anormal → delai_depot_anormal (clé registre + Series)
      montant_normalise_log   → montant_log (clé registre + Series)
    Nouvelles (Scénarios A/B) :
      acte_incomplet (★ COMMUN) — Flag_Acte_Incomp
      document_age_anormal (★ COMMUN) — Date_Saisie_Systeme - Date_Soin > 180j
      nb_sinistres_recents (★ COMMUN) — Nb_Sinistres_12m

Lancer :
    pytest tests/unit/test_sante_features_ext.py -v
"""

import numpy as np
import pandas as pd
import pytest

from modules.sante.features_ext import (
    FEATURE_EXT_FUNCTIONS,
    compute_acte_incomplet,
    compute_anciennete_contrat_courte,
    compute_delai_soin_depot_anormal,
    compute_document_age_anormal_sante,
    compute_document_altere,
    compute_montant_normalise_log,
    compute_nb_sinistres_meme_iban,
    compute_nb_sinistres_recents_sante,
    compute_ocr_confiance_faible,
    compute_post_mortem_flag,
    compute_praticien_hors_agrement,
    compute_saisie_hors_heures,
)


# ===========================================================================
# Fixtures communes
# ===========================================================================

@pytest.fixture
def df_complet():
    """DataFrame avec toutes les colonnes optionnelles présentes."""
    return pd.DataFrame({
        "Flag_Doc_Altere":        [0, 1, 0, 1, 0],
        "Praticien_Actif":        [True, False, True, False, True],
        "Confiance_OCR_Glob":     [0.9, 0.3, 0.6, 0.1, 0.5],
        "Delai_Soin_Depot":       [5, 45, 10, 60, 30],
        "Anciennete_Contrat":     [365, 30, 180, 15, 90],
        "Heure_Saisie":           [10, 2, 14, 22, 9],
        "Montant_Facture":        [5000.0, 0.0, 15000.0, 100.0, 500.0],
        "Date_Soin":              ["2024-01-15", "2024-03-20", "2024-02-01",
                                   "2024-05-10", "2024-04-01"],
        "Date_Deces":             [pd.NaT, "2024-01-01", pd.NaT,
                                   "2024-06-01", "2024-05-15"],
        "Nb_Sinistres_Meme_IBAN": [1, 8, 2, 12, 1],
        # Colonnes v0.5.0
        "Flag_Acte_Incomp":       [0, 1, 0, 1, 0],
        "Date_Saisie_Systeme":    ["2024-01-20", "2024-12-01", "2024-02-15",
                                   "2024-05-25", "2025-02-01"],
        "Nb_Sinistres_12m":       [1, 5, 2, 8, 3],
    })


@pytest.fixture
def df_vide_colonnes():
    """DataFrame sans aucune des colonnes optionnelles — test dégradation gracieuse."""
    return pd.DataFrame({"ID_Sinistre": ["S001", "S002", "S003"]})


# ===========================================================================
# 1. compute_document_altere
# ===========================================================================

class TestDocumentAltere:

    def test_valeurs_normales(self, df_complet):
        result = compute_document_altere(df_complet)
        assert result.name == "document_altere"
        assert list(result) == [0, 1, 0, 1, 0]
        assert result.dtype == int

    def test_colonne_absente_retourne_zeros(self, df_vide_colonnes):
        result = compute_document_altere(df_vide_colonnes)
        assert (result == 0).all()
        assert len(result) == 3

    def test_nan_traite_comme_zero(self):
        df = pd.DataFrame({"Flag_Doc_Altere": [1, None, 0]})
        result = compute_document_altere(df)
        assert list(result) == [1, 0, 0]


# ===========================================================================
# 2. compute_praticien_hors_agrement
# ===========================================================================

class TestPraticienHorsAgrement:

    def test_valeurs_normales(self, df_complet):
        result = compute_praticien_hors_agrement(df_complet)
        assert result.name == "praticien_hors_agrement"
        # True → actif → 0 ; False → hors agrément → 1
        assert list(result) == [0, 1, 0, 1, 0]

    def test_colonne_absente_retourne_zeros(self, df_vide_colonnes):
        result = compute_praticien_hors_agrement(df_vide_colonnes)
        assert (result == 0).all()

    def test_nan_traite_comme_actif(self):
        df = pd.DataFrame({"Praticien_Actif": [True, None, False]})
        result = compute_praticien_hors_agrement(df)
        # NaN → fillna(True) → actif → 0
        assert list(result) == [0, 0, 1]


# ===========================================================================
# 3. compute_ocr_confiance_faible  (★ COMMUN)
# ===========================================================================

class TestOcrConfianceFaible:

    def test_seuil_defaut_05(self, df_complet):
        result = compute_ocr_confiance_faible(df_complet)
        assert result.name == "ocr_confiance_faible"
        # 0.9→0, 0.3→1, 0.6→0, 0.1→1, 0.5→0 (0.5 n'est PAS < 0.5)
        assert list(result) == [0, 1, 0, 1, 0]

    def test_seuil_personnalise(self, df_complet):
        result = compute_ocr_confiance_faible(df_complet, seuil=0.7)
        # 0.9→0, 0.3→1, 0.6→1, 0.1→1, 0.5→1
        assert list(result) == [0, 1, 1, 1, 1]

    def test_colonne_absente(self, df_vide_colonnes):
        result = compute_ocr_confiance_faible(df_vide_colonnes)
        # default=1.0 → 1.0 < 0.5 → False → 0
        assert (result == 0).all()

    def test_nan_traite_comme_confiant(self):
        df = pd.DataFrame({"Confiance_OCR_Glob": [0.9, None, 0.2]})
        result = compute_ocr_confiance_faible(df)
        assert list(result) == [0, 0, 1]


# ===========================================================================
# 4. compute_delai_soin_depot_anormal  (★ COMMUN — Series 'delai_depot_anormal')
# ===========================================================================

class TestDelaiDepotAnormal:
    """
    Scénario A : la fonction conserve son nom interne
    compute_delai_soin_depot_anormal mais retourne une Series nommée
    'delai_depot_anormal' (clé du registre harmonisée pour M_makora_dif).
    """

    def test_seuil_defaut_30j(self, df_complet):
        result = compute_delai_soin_depot_anormal(df_complet)
        assert result.name == "delai_depot_anormal"
        # 5→0, 45→1, 10→0, 60→1, 30→0 (30 n'est PAS > 30)
        assert list(result) == [0, 1, 0, 1, 0]

    def test_seuil_personnalise(self, df_complet):
        result = compute_delai_soin_depot_anormal(df_complet, seuil_jours=10)
        # 5→0, 45→1, 10→0 (10 n'est PAS > 10), 60→1, 30→1
        assert list(result) == [0, 1, 0, 1, 1]

    def test_colonne_absente(self, df_vide_colonnes):
        result = compute_delai_soin_depot_anormal(df_vide_colonnes)
        # default=0 → 0 > 30 → False → 0
        assert (result == 0).all()

    def test_nom_series_renomme(self, df_complet):
        """Vérifie explicitement le renommage Scénario A."""
        result = compute_delai_soin_depot_anormal(df_complet)
        assert result.name == "delai_depot_anormal"


# ===========================================================================
# 5. compute_anciennete_contrat_courte  (★ COMMUN)
# ===========================================================================

class TestAncienneteContratCourte:

    def test_seuil_defaut_90j(self, df_complet):
        result = compute_anciennete_contrat_courte(df_complet)
        assert result.name == "anciennete_contrat_courte"
        # 365→0, 30→1, 180→0, 15→1, 90→0 (90 n'est PAS < 90)
        assert list(result) == [0, 1, 0, 1, 0]

    def test_colonne_absente(self, df_vide_colonnes):
        result = compute_anciennete_contrat_courte(df_vide_colonnes)
        # default=365 → 365 < 90 → False → 0
        assert (result == 0).all()


# ===========================================================================
# 6. compute_saisie_hors_heures  (★ COMMUN)
# ===========================================================================

class TestSaisieHorsHeures:

    def test_valeurs_normales(self, df_complet):
        result = compute_saisie_hors_heures(df_complet)
        assert result.name == "saisie_hors_heures"
        # 10→0, 2→1, 14→0, 22→1, 9→0
        assert list(result) == [0, 1, 0, 1, 0]

    def test_heures_limites(self):
        df = pd.DataFrame({"Heure_Saisie": [7, 6, 20, 21, 0, 23]})
        result = compute_saisie_hors_heures(df)
        # 7→0, 6→1, 20→0, 21→1, 0→1, 23→1
        assert list(result) == [0, 1, 0, 1, 1, 1]

    def test_colonne_absente(self, df_vide_colonnes):
        result = compute_saisie_hors_heures(df_vide_colonnes)
        # default=12 → dans les heures → 0
        assert (result == 0).all()

    def test_seuils_personnalises(self):
        df = pd.DataFrame({"Heure_Saisie": [8, 17, 6, 19]})
        result = compute_saisie_hors_heures(df, heure_min=8, heure_max=18)
        # 8→0, 17→0, 6→1, 19→1
        assert list(result) == [0, 0, 1, 1]


# ===========================================================================
# 7. compute_montant_normalise_log  (★ COMMUN — Series 'montant_log')
# ===========================================================================

class TestMontantLog:
    """
    Scénario C : la fonction conserve son nom interne
    compute_montant_normalise_log mais retourne une Series nommée
    'montant_log'. Source : colonne Montant_Facture.
    """

    def test_transformation_log1p(self, df_complet):
        result = compute_montant_normalise_log(df_complet)
        assert result.name == "montant_log"
        # log1p(5000) ≈ 8.517
        assert abs(result.iloc[0] - np.log1p(5000.0)) < 1e-9
        # log1p(0) = 0.0
        assert result.iloc[1] == pytest.approx(0.0)

    def test_montant_nul(self):
        df = pd.DataFrame({"Montant_Facture": [0.0]})
        result = compute_montant_normalise_log(df)
        assert result.iloc[0] == pytest.approx(0.0)

    def test_montant_negatif_clipe_a_zero(self):
        df = pd.DataFrame({"Montant_Facture": [-500.0, 100.0]})
        result = compute_montant_normalise_log(df)
        # -500 → clip → 0 → log1p(0) = 0
        assert result.iloc[0] == pytest.approx(0.0)
        assert result.iloc[1] == pytest.approx(np.log1p(100.0))

    def test_colonne_absente(self, df_vide_colonnes):
        result = compute_montant_normalise_log(df_vide_colonnes)
        # default=0.0 → log1p(0) = 0 (valeur exacte)
        assert (result == 0.0).all()

    def test_nan_traite_comme_zero(self):
        df = pd.DataFrame({"Montant_Facture": [1000.0, None, 500.0]})
        result = compute_montant_normalise_log(df)
        assert result.iloc[1] == pytest.approx(0.0)

    def test_nom_series_renomme(self, df_complet):
        """Vérifie explicitement le renommage Scénario C."""
        result = compute_montant_normalise_log(df_complet)
        assert result.name == "montant_log"


# ===========================================================================
# 8. compute_post_mortem_flag
# ===========================================================================

class TestPostMortemFlag:

    def test_detection_correcte(self, df_complet):
        result = compute_post_mortem_flag(df_complet)
        assert result.name == "post_mortem_flag"
        # Ligne 0 : Date_Deces=NaT → 0
        assert result.iloc[0] == 0
        # Ligne 1 : soin=2024-03-20 > deces=2024-01-01 → 1
        assert result.iloc[1] == 1
        # Ligne 2 : Date_Deces=NaT → 0
        assert result.iloc[2] == 0
        # Ligne 3 : soin=2024-05-10 < deces=2024-06-01 → 0
        assert result.iloc[3] == 0
        # Ligne 4 : soin=2024-04-01 < deces=2024-05-15 → 0
        assert result.iloc[4] == 0

    def test_colonnes_absentes(self, df_vide_colonnes):
        result = compute_post_mortem_flag(df_vide_colonnes)
        assert (result == 0).all()

    def test_date_soin_absente_seule(self):
        df = pd.DataFrame({"Date_Deces": ["2024-01-01", "2024-06-01"]})
        result = compute_post_mortem_flag(df)
        assert (result == 0).all()

    def test_dates_identiques_non_post_mortem(self):
        df = pd.DataFrame({
            "Date_Soin":  ["2024-03-15"],
            "Date_Deces": ["2024-03-15"],
        })
        result = compute_post_mortem_flag(df)
        # date_soin > date_deces = False quand égal
        assert result.iloc[0] == 0

    def test_dtype_integer(self, df_complet):
        result = compute_post_mortem_flag(df_complet)
        assert result.dtype == int


# ===========================================================================
# 9. compute_nb_sinistres_meme_iban
# ===========================================================================

class TestNbSinistresMemeIban:

    def test_valeurs_normales(self, df_complet):
        result = compute_nb_sinistres_meme_iban(df_complet)
        assert result.name == "nb_sinistres_meme_iban"
        assert list(result) == [1.0, 8.0, 2.0, 12.0, 1.0]
        assert result.dtype == float

    def test_colonne_absente(self, df_vide_colonnes):
        result = compute_nb_sinistres_meme_iban(df_vide_colonnes)
        # default=1 → tous à 1.0
        assert (result == 1.0).all()

    def test_nan_remplace_par_1(self):
        df = pd.DataFrame({"Nb_Sinistres_Meme_IBAN": [3, None, 7]})
        result = compute_nb_sinistres_meme_iban(df)
        assert result.iloc[1] == pytest.approx(1.0)


# ===========================================================================
# 10. compute_acte_incomplet  (★ COMMUN — NOUVEAU Scénario A)
# ===========================================================================

class TestActeIncomplet:
    """
    Scénario A : NOUVELLE feature commune ★.
    Source : Flag_Acte_Incomp. Fallback 0 si absente.
    """

    def test_valeurs_normales(self, df_complet):
        result = compute_acte_incomplet(df_complet)
        assert result.name == "acte_incomplet"
        # Flag_Acte_Incomp = [0, 1, 0, 1, 0]
        assert list(result) == [0, 1, 0, 1, 0]

    def test_dtype_int(self, df_complet):
        result = compute_acte_incomplet(df_complet)
        assert result.dtype == int

    def test_colonne_absente_retourne_zeros(self, df_vide_colonnes):
        result = compute_acte_incomplet(df_vide_colonnes)
        assert (result == 0).all()
        assert len(result) == 3

    def test_nan_traite_comme_zero(self):
        df = pd.DataFrame({"Flag_Acte_Incomp": [True, None, False, None]})
        result = compute_acte_incomplet(df)
        assert list(result) == [1, 0, 0, 0]

    def test_valeurs_binaires(self, df_complet):
        result = compute_acte_incomplet(df_complet)
        assert set(result.unique()).issubset({0, 1})


# ===========================================================================
# 11. compute_document_age_anormal_sante  (★ COMMUN — NOUVEAU Scénario B)
# ===========================================================================

class TestDocumentAgeAnormal:
    """
    Scénario B : NOUVELLE feature commune ★ (correction dette Session H).
    Source primaire : (Date_Saisie_Systeme - Date_Soin).days > seuil (180j).
    Fallback : Delai_Soin_Depot > seuil. Valeur neutre 0 sinon.
    """

    def test_calcul_depuis_dates_brutes(self, df_complet):
        """
        Date_Saisie_Systeme - Date_Soin :
          0 : 2024-01-20 - 2024-01-15 = 5j    → 0
          1 : 2024-12-01 - 2024-03-20 = 256j  → 1 (> 180)
          2 : 2024-02-15 - 2024-02-01 = 14j   → 0
          3 : 2024-05-25 - 2024-05-10 = 15j   → 0
          4 : 2025-02-01 - 2024-04-01 = 306j  → 1 (> 180)
        """
        result = compute_document_age_anormal_sante(df_complet)
        assert result.name == "document_age_anormal"
        assert list(result) == [0, 1, 0, 0, 1]

    def test_seuil_personnalise(self):
        df = pd.DataFrame({
            "Date_Saisie_Systeme": ["2024-01-20"],
            "Date_Soin":           ["2024-01-01"],
        })
        result = compute_document_age_anormal_sante(df, seuil_jours=10)
        # 19j > 10j → 1
        assert result.iloc[0] == 1

    def test_fallback_delai_soin_depot(self):
        """Sans Date_Saisie_Systeme → fallback sur Delai_Soin_Depot > 180."""
        df = pd.DataFrame({
            "Delai_Soin_Depot": [200, 50, 365],
        })
        result = compute_document_age_anormal_sante(df)
        assert result.name == "document_age_anormal"
        assert list(result) == [1, 0, 1]

    def test_aucune_source_retourne_zeros(self, df_vide_colonnes):
        result = compute_document_age_anormal_sante(df_vide_colonnes)
        assert (result == 0).all()
        assert result.name == "document_age_anormal"

    def test_dtype_int(self, df_complet):
        result = compute_document_age_anormal_sante(df_complet)
        assert result.dtype == int

    def test_dates_invalides_ne_crash_pas(self):
        df = pd.DataFrame({
            "Date_Saisie_Systeme": ["not-a-date", "2024-12-01"],
            "Date_Soin":           ["2024-01-15", "bad"],
        })
        result = compute_document_age_anormal_sante(df)
        assert isinstance(result, pd.Series)
        assert len(result) == 2
        assert result.isna().sum() == 0


# ===========================================================================
# 12. compute_nb_sinistres_recents_sante  (★ COMMUN — NOUVEAU Scénario B)
# ===========================================================================

class TestNbSinistreRecents:
    """
    Scénario B : NOUVELLE feature commune ★.
    Source : Nb_Sinistres_12m (pré-calculée). Fallback 0 si absente.
    """

    def test_passthrough_nb_sinistres(self, df_complet):
        result = compute_nb_sinistres_recents_sante(df_complet)
        assert result.name == "nb_sinistres_recents"
        # Nb_Sinistres_12m = [1, 5, 2, 8, 3]
        assert list(result) == [1.0, 5.0, 2.0, 8.0, 3.0]

    def test_dtype_float(self, df_complet):
        result = compute_nb_sinistres_recents_sante(df_complet)
        assert result.dtype == float

    def test_colonne_absente_retourne_zeros(self, df_vide_colonnes):
        result = compute_nb_sinistres_recents_sante(df_vide_colonnes)
        assert (result == 0).all()
        assert result.isna().sum() == 0

    def test_nan_remplace_par_zero(self):
        df = pd.DataFrame({"Nb_Sinistres_12m": [None, 3.0, None]})
        result = compute_nb_sinistres_recents_sante(df)
        assert result.isna().sum() == 0
        assert result.iloc[1] == 3.0

    def test_valeurs_positives(self, df_complet):
        result = compute_nb_sinistres_recents_sante(df_complet)
        assert (result >= 0).all()


# ===========================================================================
# Test de cohérence du registre (v0.5.0 — 12 fonctions)
# ===========================================================================

class TestRegistreFonctions:

    def test_registre_contient_12_fonctions(self):
        assert len(FEATURE_EXT_FUNCTIONS) == 12

    def test_toutes_les_cles_attendues(self):
        attendues = {
            "document_altere",
            "praticien_hors_agrement",
            "ocr_confiance_faible",
            "delai_depot_anormal",          # Scénario A : renommé
            "anciennete_contrat_courte",
            "saisie_hors_heures",
            "montant_log",                  # Scénario C : renommé
            "post_mortem_flag",
            "nb_sinistres_meme_iban",
            "acte_incomplet",               # Scénario A : NOUVEAU
            "document_age_anormal",         # Scénario B : NOUVEAU
            "nb_sinistres_recents",         # Scénario B : NOUVEAU
        }
        assert set(FEATURE_EXT_FUNCTIONS.keys()) == attendues

    def test_toutes_les_fonctions_appelables(self):
        """Chaque fonction du registre tourne sans erreur sur un DataFrame minimal."""
        df_minimal = pd.DataFrame({
            "ID_Sinistre": ["S001", "S002"],
            "Montant_Facture": [1000.0, 500.0],
        })
        for name, fn in FEATURE_EXT_FUNCTIONS.items():
            result = fn(df_minimal)
            assert isinstance(result, pd.Series), f"{name} doit retourner une pd.Series"
            assert len(result) == 2, f"{name} doit retourner autant de lignes que l'input"

    def test_noms_series_coherents(self, df_complet):
        """Chaque fonction retourne une Series dont le nom == clé du registre."""
        for name, fn in FEATURE_EXT_FUNCTIONS.items():
            result = fn(df_complet)
            assert result.name == name, (
                f"Nom incohérent : registre='{name}', Series.name='{result.name}'"
            )

    def test_cles_renommees_presentes(self):
        """Les anciennes clés ne doivent plus exister (Scénarios A/C)."""
        keys = set(FEATURE_EXT_FUNCTIONS.keys())
        assert "delai_soin_depot_anormal" not in keys
        assert "montant_normalise_log" not in keys
        assert "delai_depot_anormal" in keys
        assert "montant_log" in keys


# ===========================================================================
# Test d'intégration — appel séquentiel sur DataFrame complet
# ===========================================================================

class TestIntegrationSeqComplete:

    def test_toutes_features_calculees_sans_erreur(self, df_complet):
        """Simule ce que fait SanteModule.engineer_features() pour les 12 features V2."""
        df = df_complet.copy()
        for feature_name, fn in FEATURE_EXT_FUNCTIONS.items():
            df[feature_name] = fn(df)

        for col in FEATURE_EXT_FUNCTIONS:
            assert col in df.columns, f"Feature '{col}' absente du DataFrame résultat"
            assert df[col].notna().all(), f"Feature '{col}' contient des NaN inattendus"

    def test_pas_de_nan_dans_features_binaires(self, df_complet):
        binaires = [
            "document_altere", "praticien_hors_agrement", "ocr_confiance_faible",
            "delai_depot_anormal", "anciennete_contrat_courte",
            "saisie_hors_heures", "post_mortem_flag",
            "acte_incomplet", "document_age_anormal",
        ]
        df = df_complet.copy()
        for name, fn in FEATURE_EXT_FUNCTIONS.items():
            df[name] = fn(df)

        for col in binaires:
            assert set(df[col].unique()).issubset({0, 1}), (
                f"Feature binaire '{col}' contient des valeurs hors {{0, 1}}"
            )