"""
scripts/test_mercuriale_reel.py
Test rapide du MercurialeLoader sur les vrais fichiers CSV Santé (FR + CM).

Lancer depuis la racine du projet :
    python scripts/test_mercuriale_reel.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# S'assurer que le projet est dans le path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mercuriale.loader import MercurialeLoader

PATH_FR = Path("data/referentials/mercuriale_sante_fr.csv")
PATH_CM = Path("data/referentials/mercuriale_sante_cm.csv")

# ── 1. Chargement ────────────────────────────────────────────────────────────
print("=" * 60)
print("TEST MERCURIALE LOADER — Fichiers réels")
print("=" * 60)

for p in [PATH_FR, PATH_CM]:
    if not p.exists():
        print(f"❌ FICHIER INTROUVABLE : {p}")
        sys.exit(1)
    print(f"✅ Trouvé : {p}")

dual = MercurialeLoader.from_dual_csv(
    path_fr=PATH_FR,
    path_cm=PATH_CM,
    branch="sante",
)
print(f"\n{dual}")

# ── 2. Afficher les 5 premiers codes de chaque fichier ───────────────────────
print(f"\n--- 5 premiers codes FR (sur {dual.size_fr}) ---")
for code in list(dual.index_fr.codes)[:5]:
    print(f"  {code} → {dual.index_fr.get_price(code):.0f} XAF")

print(f"\n--- 5 premiers codes CM (sur {dual.size_cm}) ---")
for code in list(dual.index_cm.codes)[:5]:
    print(f"  {code} → {dual.index_cm.get_price(code):.0f} XAF")

# ── 3. Test vectorisé sur un mini DataFrame ──────────────────────────────────
# On prend les 2 premiers codes du vrai CSV pour le test
code_fr = list(dual.index_fr.codes)[0]
code_cm = list(dual.index_cm.codes)[0]
prix_fr_xaf = dual.index_fr.get_price(code_fr)
prix_cm_xaf = dual.index_cm.get_price(code_cm)

# Reconstruire le montant EUR correspondant pour avoir ratio = 1.0
from core.mercuriale.models import TAUX_BEAC_EUR_XAF
montant_fr_eur = prix_fr_xaf / TAUX_BEAC_EUR_XAF

df = pd.DataFrame({
    "Code_Acte":       [code_fr,        code_fr,            code_cm,     "CODE_ABSENT"],
    "Montant_Facture": [montant_fr_eur,  montant_fr_eur * 3, prix_cm_xaf, 9999.0],
    "Pays_Residence":  ["France",        "France",           "Cameroun",  "Cameroun"],
    "Devise":          ["EUR",           "EUR",              "XAF",       "XAF"],
})

df["ratio"] = dual.compute_ratio_series(
    amounts=df["Montant_Facture"],
    codes=df["Code_Acte"],
    pays=df["Pays_Residence"],
    devise=df["Devise"],
)
df["hors_mercuriale"] = dual.flag_absent_series(df["Code_Acte"], df["Pays_Residence"])

print("\n--- Résultats calcul ratio ---")
print(df[["Code_Acte", "Montant_Facture", "Pays_Residence", "ratio", "hors_mercuriale"]].to_string(index=False))

# ── 4. Assertions ────────────────────────────────────────────────────────────
print("\n--- Vérifications ---")

r0 = df["ratio"].iloc[0]
assert abs(r0 - 1.0) < 0.01, f"❌ Ratio FR exact attendu 1.0, obtenu {r0}"
print(f"✅ Ratio FR exact = {r0:.4f} (attendu 1.0)")

r1 = df["ratio"].iloc[1]
assert abs(r1 - 3.0) < 0.01, f"❌ Ratio FR ×3 attendu 3.0, obtenu {r1}"
print(f"✅ Ratio FR ×3 = {r1:.4f} (attendu 3.0) → FRAUDE DÉTECTABLE")

r2 = df["ratio"].iloc[2]
assert abs(r2 - 1.0) < 0.01, f"❌ Ratio CM exact attendu 1.0, obtenu {r2}"
print(f"✅ Ratio CM exact = {r2:.4f} (attendu 1.0)")

assert pd.isna(df["ratio"].iloc[3]), "❌ Code absent doit retourner NaN"
print("✅ Code absent → NaN (pas d'imputation silencieuse)")

assert df["hors_mercuriale"].iloc[3] == True
print("✅ Code absent → flag_hors_mercuriale = True")

print(f"\n✅ TAUX BEAC UTILISÉ : 1 EUR = {TAUX_BEAC_EUR_XAF} XAF")
print("\n🎉 TOUS LES TESTS OK — MercurialeLoader prêt pour T11 (Module Auto)")