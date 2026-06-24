"""
MODULE : core/mercuriale/models.py
DESCRIPTION : Modèles de données pour la brique MercurialeLoader.

              MercurialeEntry  → une ligne du référentiel (un code + son prix)
              MercurialeIndex  → index complet chargé en mémoire, optimisé
                                 pour la lookup O(1) par code acte.

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Séparer les modèles de données des logiques de chargement évite la
    dette architecturale des "mega-classes" mêlant état et comportement.
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection. ICMLA.
  → Le ratio prix facturé / prix référentiel est la feature discriminante
    principale en fraude santé. La structure doit permettre sa computation
    rapide sur des DataFrames de 100k+ lignes (vectorisation Pandas).

DÉCISIONS DE CONCEPTION :
- MercurialeEntry est une dataclass frozen (immuable) — le référentiel
  ne doit jamais être modifié après chargement (immutabilité = thread-safe).
- MercurialeIndex expose une API de lookup vectorisé (Series → Series)
  pour éviter les apply() ligne par ligne sur les grands DataFrames.
- price_ref_xaf est TOUJOURS en XAF après normalisation, quelle que soit
  la devise source. La conversion EUR→XAF est faite au chargement.
  [INSURANCE_DOMAIN_CONTEXT §3.2] : taux BEAC fixe 1 EUR = 655.957 XAF.
- DualMercurialeIndex encapsule deux MercurialeIndex (FR + CM) pour le
  cas réel du module Santé : deux CSV séparés, même nomenclature de codes,
  prix en EUR pour la France et en XAF pour le Cameroun.
  Le dispatch se fait par colonne `Pays_Residence` (France / Cameroun).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

TAUX_BEAC_EUR_XAF: float = 655.957
"""Taux de change fixe EUR/XAF — Banque des États de l'Afrique Centrale."""


@dataclass(frozen=True)
class MercurialeEntry:
    """
    Représente une ligne du référentiel mercuriale.

    Attributs :
        code          : code acte/réparation (ex: 'GYNECO_001', 'REP_CARROS_01')
        libelle       : description officielle
        price_ref_xaf : prix de référence normalisé en XAF (après conversion si EUR)
        category      : catégorie métier (ex: 'Acte médical', 'Main d\'œuvre')
        price_ref_eur : prix source en EUR si disponible (None si source XAF)
    """
    code: str
    libelle: str
    price_ref_xaf: float
    category: str
    price_ref_eur: Optional[float] = None

    def __post_init__(self) -> None:
        if self.price_ref_xaf < 0:
            raise ValueError(
                f"MercurialeEntry({self.code}): price_ref_xaf ne peut pas être "
                f"négatif ({self.price_ref_xaf}). Vérifier le fichier référentiel."
            )


class MercurialeIndex:
    """
    Index en mémoire du référentiel mercuriale, optimisé pour lookup O(1).

    Usage :
        index = MercurialeIndex(entries, branch="sante")

        # Lookup unitaire
        entry = index.get("GYNECO_001")         # → MercurialeEntry | None
        price = index.get_price("GYNECO_001")   # → float | None

        # Lookup vectorisé (DataFrame entier)
        df["prix_ref"] = index.lookup_series(df["Code_Acte"])
        df["flag_absent"] = index.flag_absent_series(df["Code_Acte"])

    [Bauder2017] : la computation vectorisée permet de traiter 100k dossiers
    sans boucles Python, critère de performance pour un prototype robuste.
    """

    def __init__(
        self,
        entries: list[MercurialeEntry],
        branch: str = "",
        source_currency: str = "XAF",
        tolerance_pct: float = 5.0,
    ) -> None:
        """
        Args:
            entries        : liste de MercurialeEntry chargées depuis le fichier
            branch         : nom de la branche (pour logging)
            source_currency: devise source du fichier ('XAF' ou 'EUR')
            tolerance_pct  : jitter de tolérance en % (défaut : 5%)
                             [INSURANCE_DOMAIN_CONTEXT §3.2]
        """
        self.branch = branch
        self.source_currency = source_currency
        self.tolerance_pct = tolerance_pct
        self._index: dict[str, MercurialeEntry] = {e.code: e for e in entries}
        self._price_series: pd.Series = pd.Series(
            {e.code: e.price_ref_xaf for e in entries},
            dtype=float,
            name="Prix_Ref_XAF",
        )

    # ------------------------------------------------------------------
    # Propriétés
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Nombre de codes dans le référentiel."""
        return len(self._index)

    @property
    def codes(self) -> list[str]:
        """Liste de tous les codes du référentiel."""
        return list(self._index.keys())

    # ------------------------------------------------------------------
    # Lookups unitaires
    # ------------------------------------------------------------------

    def get(self, code: str) -> Optional[MercurialeEntry]:
        """Retourne l'entrée pour un code, ou None si absent."""
        return self._index.get(code)

    def get_price(self, code: str) -> Optional[float]:
        """
        Retourne le prix de référence en XAF pour un code, ou None si absent.

        Conforme [INSURANCE_DOMAIN_CONTEXT §3.2] :
          "Code inconnu → ratio = None, ne pas imputer à 1.0 silencieusement."
        """
        entry = self._index.get(code)
        return entry.price_ref_xaf if entry is not None else None

    def contains(self, code: str) -> bool:
        """Vérifie si un code est présent dans le référentiel."""
        return code in self._index

    # ------------------------------------------------------------------
    # Lookups vectorisés (optimisés DataFrame)
    # ------------------------------------------------------------------

    def lookup_series(self, codes: pd.Series) -> pd.Series:
        """
        Mappe une Series de codes vers leurs prix de référence en XAF.

        Les codes absents du référentiel → NaN (pas 0, pas 1.0).
        Conserve l'index de la Series d'entrée.

        Args:
            codes : pd.Series de codes actes (dtype string/object)

        Returns:
            pd.Series de float (NaN si code absent), même index que codes.
        """
        return codes.map(self._price_series)

    def flag_absent_series(self, codes: pd.Series) -> pd.Series:
        """
        Retourne une Series booléenne True si le code est ABSENT du référentiel.

        Usage : df["flag_code_hors_mercuriale"] = index.flag_absent_series(df["Code_Acte"])

        [INSURANCE_DOMAIN_CONTEXT §3.2] : les codes hors référentiel ne doivent
        pas générer de faux positifs — ils doivent être flaggés et exclus du
        calcul de ratio.
        """
        return ~codes.isin(self._price_series.index)

    def compute_ratio_series(
        self,
        amounts: pd.Series,
        codes: pd.Series,
    ) -> pd.Series:
        """
        Calcule ratio = montant_facturé / prix_référence pour chaque dossier.

        Les dossiers avec code absent → ratio = NaN.
        Cap à 50.0 pour éviter que les outliers extrêmes saturent SHAP.

        [Bauder2017] : seuil de surfacturation à ratio > 1.5.
        [INSURANCE_DOMAIN_CONTEXT §3.2] : jitter tolérance ±tolerance_pct%.

        Args:
            amounts : pd.Series des montants facturés en XAF
            codes   : pd.Series des codes actes (même index)

        Returns:
            pd.Series de float [NaN si code absent, sinon ratio clampé à 50.0]
        """
        prix_ref = self.lookup_series(codes)
        # Division vectorisée — NaN propagé automatiquement si prix_ref=NaN
        ratio = amounts / prix_ref
        # Cap outliers pour stabilité SHAP [Lundberg2017]
        return ratio.clip(upper=50.0)

    def is_within_tolerance(self, codes: pd.Series, amounts: pd.Series) -> pd.Series:
        """
        Retourne True si le montant est dans la tolérance ±tolerance_pct% du prix ref.

        [INSURANCE_DOMAIN_CONTEXT §3.2] : jitter ±5% considéré conforme
        car la mercuriale est révisée périodiquement.

        Returns:
            pd.Series booléenne (NaN si code absent)
        """
        ratio = self.compute_ratio_series(amounts, codes)
        lower = 1.0 - self.tolerance_pct / 100.0
        upper = 1.0 + self.tolerance_pct / 100.0
        return ratio.between(lower, upper)

    # ------------------------------------------------------------------
    # Représentation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"MercurialeIndex(branch={self.branch!r}, "
            f"size={self.size}, currency={self.source_currency})"
        )


class DualMercurialeIndex:
    """
    Index dual FR + CM pour les modules ayant deux fichiers référentiels
    séparés selon le marché (ex : module Santé).

    Cas réel MAKORA :
        - mercuriale_sante_fr.csv  → Prix_Ref_EUR  (flux France / CCAM/SNDS)
        - mercuriale_sante_cm.csv  → Prix_Ref_XAF  (flux Cameroun / ASAC/CIMA)

    Le dispatch se fait sur la colonne `Pays_Residence` du DataFrame :
        - "France"    → index FR, montant converti en XAF pour comparaison
        - "Cameroun"  → index CM, montant déjà en XAF

    [INSURANCE_DOMAIN_CONTEXT §3.2] :
      "Si le dataset contient des montants en EUR (flux France), convertir
       en XAF avant toute comparaison avec la mercuriale."

    Usage :
        dual = DualMercurialeIndex(index_fr=idx_fr, index_cm=idx_cm)
        df["ratio"] = dual.compute_ratio_series(
            amounts=df["Montant_Facture"],
            codes=df["Code_Acte"],
            pays=df["Pays_Residence"],
            devise=df["Devise"],
        )
    """

    def __init__(
        self,
        index_fr: MercurialeIndex,
        index_cm: MercurialeIndex,
        pays_column_fr: str = "France",
        pays_column_cm: str = "Cameroun",
    ) -> None:
        """
        Args:
            index_fr       : MercurialeIndex chargé depuis le CSV France (EUR → XAF)
            index_cm       : MercurialeIndex chargé depuis le CSV Cameroun (XAF)
            pays_column_fr : valeur attendue dans `Pays_Residence` pour la France
            pays_column_cm : valeur attendue dans `Pays_Residence` pour le Cameroun
        """
        self.index_fr = index_fr
        self.index_cm = index_cm
        self.pays_fr = pays_column_fr
        self.pays_cm = pays_column_cm

    @property
    def size_fr(self) -> int:
        return self.index_fr.size

    @property
    def size_cm(self) -> int:
        return self.index_cm.size

    def compute_ratio_series(
        self,
        amounts: "pd.Series",
        codes: "pd.Series",
        pays: "pd.Series",
        devise: "Optional[pd.Series]" = None,
    ) -> "pd.Series":
        """
        Calcule le ratio montant_facturé / prix_référence en tenant compte
        du marché (France vs Cameroun) et de la devise.

        Logique :
          - Pays = France  → index FR, montant en EUR converti en XAF avant ratio
          - Pays = Cameroun → index CM, montant déjà en XAF
          - Pays inconnu   → NaN + flag_code_hors_mercuriale

        [INSURANCE_DOMAIN_CONTEXT §3.2] : "Conversion obligatoire EUR→XAF
        avant toute comparaison avec la mercuriale."

        Args:
            amounts : pd.Series montants facturés (EUR ou XAF selon Devise)
            codes   : pd.Series codes actes
            pays    : pd.Series valeurs Pays_Residence ("France" / "Cameroun")
            devise  : pd.Series optionnelle ("EUR" / "XAF") — si None, inféré
                      depuis pays (France=EUR, Cameroun=XAF)

        Returns:
            pd.Series de float, NaN si code absent ou pays inconnu
        """
        import pandas as pd

        result = pd.Series(float("nan"), index=amounts.index)

        mask_fr = pays == self.pays_fr
        mask_cm = pays == self.pays_cm

        # ── Flux France : convertir EUR → XAF avant le ratio ──────────────
        if mask_fr.any():
            amounts_fr = amounts[mask_fr]
            codes_fr = codes[mask_fr]
            # Si la devise est fournie et déjà XAF sur certains dossiers FR (cas edge),
            # on respecte la devise déclarée ; sinon on suppose EUR pour France.
            if devise is not None:
                amounts_xaf = amounts_fr.where(
                    devise[mask_fr] == "XAF",
                    amounts_fr * TAUX_BEAC_EUR_XAF,
                )
            else:
                amounts_xaf = amounts_fr * TAUX_BEAC_EUR_XAF
            result[mask_fr] = self.index_fr.compute_ratio_series(amounts_xaf, codes_fr)

        # ── Flux Cameroun : montants déjà en XAF ──────────────────────────
        if mask_cm.any():
            result[mask_cm] = self.index_cm.compute_ratio_series(
                amounts[mask_cm], codes[mask_cm]
            )

        return result

    def flag_absent_series(
        self,
        codes: "pd.Series",
        pays: "pd.Series",
    ) -> "pd.Series":
        """
        Retourne True si le code est absent du référentiel correspondant au pays.

        Un code présent en FR mais absent en CM → True pour les dossiers CM.
        """
        import pandas as pd

        result = pd.Series(True, index=codes.index)  # défaut : absent

        mask_fr = pays == self.pays_fr
        mask_cm = pays == self.pays_cm

        if mask_fr.any():
            result[mask_fr] = self.index_fr.flag_absent_series(codes[mask_fr])
        if mask_cm.any():
            result[mask_cm] = self.index_cm.flag_absent_series(codes[mask_cm])

        return result

    def __repr__(self) -> str:
        return (
            f"DualMercurialeIndex("
            f"FR={self.size_fr} codes, "
            f"CM={self.size_cm} codes)"
        )