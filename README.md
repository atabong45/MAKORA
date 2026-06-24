Voici les tableaux complets avec analyse.Trois enseignements majeurs à retenir pour le mémoire.

**PU Learning RF est la vraie découverte de la journée.** +9.3 pts de F1 sur Santé, +6.6 pts sur Auto par rapport à IF classique, et il est SHAP-compatible via TreeExplainer. La raison est simple : 6 684 dossiers RCA-confirmés (Santé) et 5 600 (Auto) ont servi de signal positif — le modèle exploite la connaissance métier déjà encodée dans ton moteur RCA. C'est la boucle vertueuse que [Elkan2008] décrit.

**HBOS est la surprise non-supervisée sur Santé** (F1=0.2795, meilleur FPR=0.0628 parmi les non-supervisés). Son hypothèse d'indépendance des features est naïve, mais sur 17 features peu corrélées elle tient.

**Deep IF a un AUC correct (0.64/0.68) mais un F1 désastreux** parce que son seuil est ultra-conservateur (FPR=0.003 Santé). Ce n'est pas un mauvais modèle — c'est un problème de calibrage du seuil. Avec une recherche de seuil sur le val set, ses résultats pourraient changer significativement.

Pour la mise à jour des fichiers contexte, pense à reporter ces nouvelles lignes dans `ML_PIPELINE.md` §2.2/§2.3 et dans les sections 2.3 de `MODULE_SANTE.md` et `MODULE_AUTO.md`.
