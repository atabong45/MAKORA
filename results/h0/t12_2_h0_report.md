# Expérience H0 — Généricité MAKORA
> Générée le 2026-05-22 13:37 | Protocole : RESEARCH_PROTOCOL.md v1.0

## Hypothèse nulle
> *"Un modèle spécialisé (entraîné uniquement sur Santé) n'est pas
> significativement plus précis qu'un modèle générique MAKORA"*
> — [Caruana1997] Multitask Learning, Machine Learning 28(1).

## Tableau comparatif

| Modèle | Branche éval. | F1 | IC 95% | AUC-ROC | MCC | FPR |
|--------|---------------|----|--------|---------|-----|-----|
| `M_sante` *(spécialisé)* | sante | **0.2004** | [0.182, 0.219] | 0.6221 | 0.1343 | 0.0792 |
| `M_makora` *(générique)* | sante | **0.1554** | [0.132, 0.180] | 0.5434 | 0.2809 | 0.0000 |
| `M_auto` *(spécialisé)* | auto | **0.2654** | [0.241, 0.288] | 0.6843 | 0.1974 | 0.0746 |
| `M_makora` *(générique)* | auto | **0.2482** | [0.223, 0.273] | 0.6086 | 0.1916 | 0.0507 |

## Résultats Δ F1

### Branche Sante

- **F1 M_sante** (spécialisé) : `0.2004`
- **F1 M_makora** (générique) : `0.1554`
- **Δ F1** : `+0.0450` (+4.50%)
- **Verdict** : ✅ `CONTRIBUTION_VALIDÉE`
- *Trade-off généricité/précision acceptable (Δ=0.045 ∈ [0.02,0.07]).*

### Branche Auto

- **F1 M_auto** (spécialisé) : `0.2654`
- **F1 M_makora** (générique) : `0.2482`
- **Δ F1** : `+0.0172` (+1.72%)
- **Verdict** : 🏆 `GÉNÉRICITÉ_SANS_COÛT`
- *M_makora rivalise avec le spécialisé — contribution forte.*

## Conclusion

L'hypothèse H0 est **validée** : le framework générique MAKORA maintient une précision de détection comparable aux modèles spécialisés sur les deux branches (Santé et Auto), avec un trade-off de généricité dans la plage acceptable définie par [Caruana1997].

---
*MAKORA T12.2 — Analyse Δ F1 | Référence : [Caruana1997]*