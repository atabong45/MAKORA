"""
MODULE : core/mercuriale/loader.py
DESCRIPTION : MercurialeLoader — brique générique du Kernel MAKORA pour le
              chargement et la consultation des référentiels de prix.

              Cette brique est AGNOSTIQUE de la branche d'assurance.
              Elle est utilisée par tout module ayant un champ `mercuriale`
              dans son fichier YAML (Santé, Auto, et futurs modules).

RÉFÉRENCES ACADÉMIQUES :
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection using
  machine learning methods. ICMLA.
  → Le ratio prix facturé / prix référentiel est la feature discriminante
    #1 dans les études de fraude assurance. Ce composant en est le socle.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems.
  NeurIPS.
  → Séparer le chargement des données de référence du code de feature
    engineering évite le couplage tacite et la dette cachée.
  → "Data dependencies are often the most costly form of technical debt."
- [Chandola2009] Chandola et al. (2009). Anomaly detection: A survey.
  ACM Computing Surveys.
  → La comparaison à un référentiel normatif (mercuriale) est une technique
    de détection d'anomalies par déviations par rapport à des normes connues,
    complémentaire à l'approche non-supervisée de l'IF.

DÉCISIONS DE CONCEPTION :
- MercurialeLoader vit dans core/ (Kernel) — pas dans un module métier.
  Raison : la logique de chargement est identique pour Santé et Auto.
  Seul le fichier YAML source change (déclaré dans le YAML du module).
- Le Loader supporte YAML et CSV comme formats source.
  → YAML pour les petits référentiels (<5000 codes) : lisible, versionnable.
  → CSV pour les gros référentiels (≥5000 codes) : performance chargement.
- from_dual_csv() charge deux CSV (FR + CM) simultanément et retourne un
  DualMercurialeIndex. C'est le cas réel du module Santé MAKORA :
  mercuriale_sante_fr.csv (Prix_Ref_EUR) + mercuriale_sante_cm.csv (Prix_Ref_XAF).
  Les deux fichiers partagent la même colonne Code_Acte (nomenclature commune).
- La conversion EUR→XAF est faite AU CHARGEMENT, pas à chaque lookup.
  Raison : performance sur 100k+ lookups. [INSURANCE_DOMAIN_CONTEXT §3.2]
- Le Loader est STATELESS entre les appels : chaque from_yaml_config()
  retourne un nouveau MercurialeIndex. La mise en cache est optionnelle
  via from_yaml_config(cache=True) et est thread-safe (verrou par chemin).
- Un code absent du référentiel ne lève PAS d'exception au niveau Loader
  (sauf en mode strict). Il retourne None et positionne le flag.
  → Choix assumé : robustesse > pureté. [Sculley2015]
"""

from __future__ import annotations

import csv
import logging
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from core.mercuriale.exceptions import (
    CodeAbsentError,
    MercurialeFileError,
    MercurialeFormatError,
)
from core.mercuriale.models import (
    TAUX_BEAC_EUR_XAF,
    DualMercurialeIndex,
    MercurialeEntry,
    MercurialeIndex,
)

logger = logging.getLogger("makora.mercuriale")

# Verrou global pour la mise en cache thread-safe
_cache_lock = threading.Lock()
_index_cache: dict[str, MercurialeIndex] = {}


class MercurialeLoader:
    """
    Chargeur générique de référentiels de prix pour le framework MAKORA.

    Supporte deux formats source :
    - YAML : pour les référentiels de taille moyenne (< 5000 codes)
    - CSV  : pour les grands référentiels (≥ 5000 codes)

    Usage depuis un module :
    ─────────────────────────
        # Dans sante_module.py ou auto_module.py
        from core.mercuriale.loader import MercurialeLoader

        loader = MercurialeLoader.from_module_config(
            config=self.config["mercuriale"],
            branch=self.branch,
        )
        df["ratio_prix_mercuriale"] = loader.index.compute_ratio_series(
            amounts=df["Montant_Facture_XAF"],
            codes=df["Code_Acte"],
        )

    Usage direct (tests, scripts) :
    ─────────────────────────────────
        loader = MercurialeLoader(
            path=Path("data/referentials/mercuriale_cima_sante.yaml"),
            code_column="Code_Acte",
            price_column="Prix_Ref_XAF",
            currency="XAF",
            branch="sante",
        )
    """

    # Colonnes requises minimales dans tout fichier référentiel
    REQUIRED_COLUMNS = {"code", "price"}

    def __init__(
        self,
        path: Path,
        code_column: str = "Code_Acte",
        price_column: str = "Prix_Ref_XAF",
        libelle_column: str = "Libelle_Officiel",
        category_column: str = "Categorie",
        currency: str = "XAF",
        tolerance_pct: float = 5.0,
        branch: str = "",
        strict: bool = False,
    ) -> None:
        """
        Args:
            path            : chemin vers le fichier référentiel (.yaml ou .csv)
            code_column     : nom de la colonne codes dans le fichier source
            price_column    : nom de la colonne prix dans le fichier source
            libelle_column  : nom de la colonne libellé (optionnel)
            category_column : nom de la colonne catégorie (optionnel)
            currency        : devise source ('XAF' ou 'EUR')
            tolerance_pct   : jitter de tolérance % [INSURANCE_DOMAIN_CONTEXT §3.2]
            branch          : nom de la branche (pour logging seulement)
            strict          : si True, CodeAbsentError est levée au lieu de
                              retourner None sur les codes absents
        """
        self.path = Path(path)
        self.code_column = code_column
        self.price_column = price_column
        self.libelle_column = libelle_column
        self.category_column = category_column
        self.currency = currency.upper()
        self.tolerance_pct = tolerance_pct
        self.branch = branch
        self.strict = strict

        self._index: Optional[MercurialeIndex] = None

    # ------------------------------------------------------------------
    # Constructeurs alternatifs (factory methods)
    # ------------------------------------------------------------------

    @classmethod
    def from_module_config(
        cls,
        config: dict[str, Any],
        branch: str = "",
        base_path: Optional[Path] = None,
    ) -> "MercurialeLoader":
        """
        Construit un MercurialeLoader depuis le bloc `mercuriale` du YAML module.

        Format YAML attendu dans sante.yaml / auto.yaml :
        ─────────────────────────────────────────────────
            mercuriale:
              path: "data/referentials/mercuriale_cima_sante.yaml"
              currency: "XAF"
              tolerance_pct: 5
              code_column: "Code_Acte"
              price_column: "Prix_Ref_XAF"
              libelle_column: "Libelle_Officiel"   # optionnel
              category_column: "Categorie"         # optionnel
              strict: false                         # optionnel

        Args:
            config    : sous-dict `config["mercuriale"]` du module
            branch    : nom de la branche (pour logging)
            base_path : répertoire de base si le chemin dans config est relatif
                        (défaut : répertoire courant d'exécution)
        """
        raw_path = Path(config["path"])
        if not raw_path.is_absolute() and base_path is not None:
            raw_path = base_path / raw_path

        return cls(
            path=raw_path,
            code_column=config.get("code_column", "Code_Acte"),
            price_column=config.get("price_column", "Prix_Ref_XAF"),
            libelle_column=config.get("libelle_column", "Libelle_Officiel"),
            category_column=config.get("category_column", "Categorie"),
            currency=config.get("currency", "XAF"),
            tolerance_pct=float(config.get("tolerance_pct", 5.0)),
            branch=branch,
            strict=bool(config.get("strict", False)),
        )

    # ------------------------------------------------------------------
    # Accès à l'index (chargement lazy)
    # ------------------------------------------------------------------

    @property
    def index(self) -> MercurialeIndex:
        """
        Retourne l'index chargé, en le chargeant à la première demande (lazy).

        Le chargement est idempotent : appeler .index plusieurs fois ne recharge
        pas le fichier si le Loader est réutilisé dans le même processus.
        """
        if self._index is None:
            self._index = self._load()
        return self._index

    # ------------------------------------------------------------------
    # Méthodes de chargement
    # ------------------------------------------------------------------

    def _load(self) -> MercurialeIndex:
        """Dispatch vers le bon parser selon l'extension du fichier."""
        if not self.path.exists():
            raise MercurialeFileError(
                f"Fichier référentiel introuvable : {self.path}. "
                f"Vérifier le champ 'mercuriale.path' dans le YAML du module '{self.branch}'."
            )

        suffix = self.path.suffix.lower()
        if suffix in (".yaml", ".yml"):
            entries = self._load_yaml()
        elif suffix == ".csv":
            entries = self._load_csv()
        else:
            raise MercurialeFileError(
                f"Format non supporté : '{suffix}'. "
                f"Utiliser .yaml/.yml ou .csv. Fichier : {self.path}"
            )

        logger.info(
            "MercurialeLoader [%s] — %d codes chargés depuis %s (devise=%s)",
            self.branch,
            len(entries),
            self.path.name,
            self.currency,
        )

        return MercurialeIndex(
            entries=entries,
            branch=self.branch,
            source_currency=self.currency,
            tolerance_pct=self.tolerance_pct,
        )

    def _load_yaml(self) -> list[MercurialeEntry]:
        """
        Charge un référentiel au format YAML.

        Format attendu :
        ────────────────
            entries:
              - code: "GYNECO_001"
                Libelle_Officiel: "Consultation gynécologique"
                Prix_Ref_XAF: 15000
                Categorie: "Acte médical"
              - code: "REP_CARROS_01"
                Libelle_Officiel: "Carrosserie — débosselage aile avant"
                Prix_Ref_XAF: 45000
                Categorie: "Main d'oeuvre"

        Ou format plat (dict code → prix) pour les référentiels simples :
        ─────────────────────────────────────────────────────────────────
            GYNECO_001: 15000
            GYNECO_002: 12000
        """
        try:
            with open(self.path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise MercurialeFormatError(
                f"Erreur de parsing YAML dans {self.path} : {exc}"
            ) from exc
        except OSError as exc:
            raise MercurialeFileError(
                f"Impossible de lire {self.path} : {exc}"
            ) from exc

        if data is None:
            raise MercurialeFormatError(f"Fichier YAML vide : {self.path}")

        # Format liste d'entrées structurées
        if isinstance(data, dict) and "entries" in data:
            return self._parse_entry_list(data["entries"])

        # Format plat dict {code: prix}
        if isinstance(data, dict) and all(
            isinstance(v, (int, float)) for v in data.values()
        ):
            return self._parse_flat_dict(data)

        raise MercurialeFormatError(
            f"Structure YAML non reconnue dans {self.path}. "
            f"Formats supportés : 'entries: [...]' ou '{{code: prix, ...}}'."
        )

    def _load_csv(self) -> list[MercurialeEntry]:
        """
        Charge un référentiel au format CSV.

        Le CSV doit avoir au minimum les colonnes déclarées dans
        self.code_column et self.price_column.
        """
        try:
            with open(self.path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except OSError as exc:
            raise MercurialeFileError(
                f"Impossible de lire {self.path} : {exc}"
            ) from exc

        if not rows:
            raise MercurialeFormatError(f"Fichier CSV vide : {self.path}")

        # Vérification des colonnes requises
        first_row = rows[0]
        if self.code_column not in first_row:
            raise MercurialeFormatError(
                f"Colonne '{self.code_column}' absente du CSV {self.path}. "
                f"Colonnes trouvées : {list(first_row.keys())}. "
                f"Vérifier le paramètre 'code_column' dans le YAML du module."
            )
        if self.price_column not in first_row:
            raise MercurialeFormatError(
                f"Colonne '{self.price_column}' absente du CSV {self.path}. "
                f"Colonnes trouvées : {list(first_row.keys())}. "
                f"Vérifier le paramètre 'price_column' dans le YAML du module."
            )

        entries = []
        for i, row in enumerate(rows):
            try:
                raw_price = float(row[self.price_column])
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "MercurialeLoader [%s] — ligne %d ignorée : prix invalide '%s' "
                    "pour code '%s'. Erreur : %s",
                    self.branch, i + 2, row.get(self.price_column), row.get(self.code_column), exc,
                )
                continue

            price_xaf = self._to_xaf(raw_price)
            entries.append(MercurialeEntry(
                code=str(row[self.code_column]).strip(),
                libelle=row.get(self.libelle_column, ""),
                price_ref_xaf=price_xaf,
                category=row.get(self.category_column, ""),
                price_ref_eur=raw_price if self.currency == "EUR" else None,
            ))

        if not entries:
            raise MercurialeFormatError(
                f"Aucune entrée valide dans {self.path} après parsing."
            )

        return entries

    # ------------------------------------------------------------------
    # Parseurs internes
    # ------------------------------------------------------------------

    def _parse_entry_list(self, entries_data: list[dict]) -> list[MercurialeEntry]:
        """Parse une liste de dicts YAML vers des MercurialeEntry."""
        if not isinstance(entries_data, list):
            raise MercurialeFormatError(
                f"'entries' doit être une liste YAML. Trouvé : {type(entries_data).__name__}"
            )

        entries = []
        for i, item in enumerate(entries_data):
            code_key = "code" if "code" in item else self.code_column
            price_key = self.price_column

            if code_key not in item:
                raise MercurialeFormatError(
                    f"Entrée #{i} : clé '{code_key}' manquante. "
                    f"Clés trouvées : {list(item.keys())}"
                )
            if price_key not in item:
                raise MercurialeFormatError(
                    f"Entrée #{i} (code={item.get(code_key, '?')}) : "
                    f"clé '{price_key}' manquante."
                )

            raw_price = float(item[price_key])
            price_xaf = self._to_xaf(raw_price)

            entries.append(MercurialeEntry(
                code=str(item[code_key]).strip(),
                libelle=item.get(self.libelle_column, item.get("libelle", "")),
                price_ref_xaf=price_xaf,
                category=item.get(self.category_column, item.get("categorie", "")),
                price_ref_eur=raw_price if self.currency == "EUR" else None,
            ))

        return entries

    def _parse_flat_dict(self, data: dict[str, float]) -> list[MercurialeEntry]:
        """Parse un dict plat {code: prix} vers des MercurialeEntry."""
        entries = []
        for code, raw_price in data.items():
            price_xaf = self._to_xaf(float(raw_price))
            entries.append(MercurialeEntry(
                code=str(code).strip(),
                libelle="",
                price_ref_xaf=price_xaf,
                category="",
                price_ref_eur=raw_price if self.currency == "EUR" else None,
            ))
        return entries

    # ------------------------------------------------------------------
    # Conversion de devise
    # ------------------------------------------------------------------

    def _to_xaf(self, price: float) -> float:
        """
        Convertit un prix vers XAF si la devise source est EUR.

        [INSURANCE_DOMAIN_CONTEXT §3.2] :
          Taux BEAC fixe : 1 EUR = 655.957 XAF.
          Conversion faite au chargement pour performance des lookups.
        """
        if self.currency == "EUR":
            return price * TAUX_BEAC_EUR_XAF
        return price

    # ------------------------------------------------------------------
    # API de lookup direct (wrappers de commodité)
    # ------------------------------------------------------------------

    def get_price_xaf(self, code: str) -> Optional[float]:
        """
        Retourne le prix de référence en XAF pour un code, ou None si absent.

        [INSURANCE_DOMAIN_CONTEXT §3.2] :
          Code absent → None (pas d'imputation silencieuse à 1.0).
        """
        price = self.index.get_price(code)
        if price is None and self.strict:
            raise CodeAbsentError(code=code, branch=self.branch)
        return price

    # ------------------------------------------------------------------
    # Mise en cache globale (optionnelle)
    # ------------------------------------------------------------------

    @classmethod
    def cached(cls, path: Path, **kwargs) -> "MercurialeLoader":
        """
        Retourne un Loader dont l'index est mis en cache par chemin de fichier.

        Utile en production pour ne charger qu'une seule fois le référentiel
        entre plusieurs requêtes API concurrentes.

        Thread-safe via verrou global.
        """
        cache_key = str(path.resolve())
        with _cache_lock:
            if cache_key not in _index_cache:
                loader = cls(path=path, **kwargs)
                _index_cache[cache_key] = loader.index
            # Retourne un Loader avec l'index déjà chargé
            loader = cls(path=path, **kwargs)
            loader._index = _index_cache[cache_key]
        return loader

    @classmethod
    def from_dual_csv(
        cls,
        path_fr: Path,
        path_cm: Path,
        code_column: str = "Code_Acte",
        price_column_fr: str = "Prix_Ref_EUR",
        price_column_cm: str = "Prix_Ref_XAF",
        libelle_column: str = "Libelle_Officiel",
        category_column: str = "Categorie",
        tolerance_pct: float = 5.0,
        branch: str = "sante",
    ) -> "DualMercurialeIndex":
        """
        Charge deux CSV (France + Cameroun) et retourne un DualMercurialeIndex.

        C'est le cas réel du module Santé MAKORA :
          - mercuriale_sante_fr.csv : Code_Acte, Libelle_Officiel, Prix_Ref_EUR, Categorie
          - mercuriale_sante_cm.csv : Code_Acte, Libelle_Officiel, Prix_Ref_XAF, Categorie

        Les deux fichiers partagent la même colonne Code_Acte.
        Le fichier FR est en EUR → converti en XAF au chargement (taux BEAC).
        Le fichier CM est déjà en XAF.

        Usage depuis SanteModule :
        ──────────────────────────
            dual_index = MercurialeLoader.from_dual_csv(
                path_fr=Path("data/referentials/mercuriale_sante_fr.csv"),
                path_cm=Path("data/referentials/mercuriale_sante_cm.csv"),
                branch="sante",
            )
            df["ratio_prix_mercuriale"] = dual_index.compute_ratio_series(
                amounts=df["Montant_Facture"],
                codes=df["Code_Acte"],
                pays=df["Pays_Residence"],
                devise=df["Devise"],
            )

        Args:
            path_fr          : chemin vers le CSV France (Prix_Ref_EUR)
            path_cm          : chemin vers le CSV Cameroun (Prix_Ref_XAF)
            code_column      : nom de la colonne codes (identique dans les 2 CSV)
            price_column_fr  : nom de la colonne prix dans le CSV France
            price_column_cm  : nom de la colonne prix dans le CSV Cameroun
            libelle_column   : nom de la colonne libellé
            category_column  : nom de la colonne catégorie
            tolerance_pct    : jitter de tolérance % [INSURANCE_DOMAIN_CONTEXT §3.2]
            branch           : nom de la branche (pour logging)

        Returns:
            DualMercurialeIndex prêt à l'emploi
        """
        loader_fr = cls(
            path=Path(path_fr),
            code_column=code_column,
            price_column=price_column_fr,
            libelle_column=libelle_column,
            category_column=category_column,
            currency="EUR",           # sera converti en XAF au chargement
            tolerance_pct=tolerance_pct,
            branch=f"{branch}_fr",
        )
        loader_cm = cls(
            path=Path(path_cm),
            code_column=code_column,
            price_column=price_column_cm,
            libelle_column=libelle_column,
            category_column=category_column,
            currency="XAF",
            tolerance_pct=tolerance_pct,
            branch=f"{branch}_cm",
        )
        logger.info(
            "MercurialeLoader.from_dual_csv [%s] — FR: %d codes, CM: %d codes",
            branch,
            loader_fr.index.size,
            loader_cm.index.size,
        )
        return DualMercurialeIndex(
            index_fr=loader_fr.index,
            index_cm=loader_cm.index,
        )

    @classmethod
    def clear_cache(cls) -> None:
        """Vide le cache global. Utile pour les tests."""
        with _cache_lock:
            _index_cache.clear()

    # ------------------------------------------------------------------
    # Représentation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        loaded = "chargé" if self._index is not None else "non chargé"
        return (
            f"MercurialeLoader(branch={self.branch!r}, "
            f"path={self.path.name!r}, currency={self.currency}, "
            f"index={loaded})"
        )