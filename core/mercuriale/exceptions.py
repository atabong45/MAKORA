"""
MODULE : core/mercuriale/exceptions.py
DESCRIPTION : Hiérarchie d'exceptions dédiée à la brique MercurialeLoader.
              Toutes héritent de MAKORAError pour rester dans la hiérarchie
              d'exceptions du Kernel.

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems. NeurIPS.
  → Les erreurs du référentiel prix doivent être distinguées des erreurs de pipeline
    pour éviter les silences dangereux (un code absent ne doit JAMAIS être imputé
    silencieusement à 1.0).

DÉCISIONS DE CONCEPTION :
- MercurialeFileError   → problème de lecture du fichier référentiel (bloquant)
- MercurialeFormatError → fichier lisible mais structure invalide (bloquant)
- CodeAbsentError       → code acte absent du référentiel (non-bloquant, loggué)
  Le CodeAbsentError est volontairement NON bloquant : il produit un flag
  `flag_code_hors_mercuriale=True` et un ratio=None, sans interrompre le pipeline.
  [INSURANCE_DOMAIN_CONTEXT §3.2] : un code CCAM n'est pas comparable à un code ASAC.
"""


class MAKORAError(Exception):
    """Classe de base des exceptions MAKORA."""


class MercurialeError(MAKORAError):
    """Classe de base des exceptions de la brique Mercuriale."""


class MercurialeFileError(MercurialeError):
    """
    Levée quand le fichier référentiel est introuvable ou illisible.

    Bloquant : sans référentiel, la feature ratio_prix_mercuriale
    ne peut pas être calculée et le module ne peut pas démarrer.
    """


class MercurialeFormatError(MercurialeError):
    """
    Levée quand le fichier est lisible mais ne respecte pas
    la structure attendue (colonnes manquantes, types incorrects).

    Bloquant : une mercuriale mal formée est pire qu'une mercuriale absente
    car elle produit des ratios silencieusement erronés.
    """


class CodeAbsentError(MercurialeError):
    """
    Levée quand un code acte/réparation n'existe pas dans le référentiel.

    NON bloquant au niveau pipeline : catché par le Loader qui retourne
    None et positionne flag_code_hors_mercuriale=True.
    Peut être loggué en mode WARNING pour audit.

    [INSURANCE_DOMAIN_CONTEXT §3.2] :
      "Code inconnu : ratio_prix_mercuriale = None → ne pas imputer à 1.0
       silencieusement, mettre un flag flag_code_hors_mercuriale = True."
    """

    def __init__(self, code: str, branch: str = ""):
        self.code = code
        self.branch = branch
        msg = f"Code '{code}' absent du référentiel mercuriale"
        if branch:
            msg += f" (branche={branch})"
        super().__init__(msg)