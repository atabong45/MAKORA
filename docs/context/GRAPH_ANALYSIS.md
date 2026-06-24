# GRAPH_ANALYSIS.md
## MAKORA Framework — Brique d'analyse de graphe
> Statut : V1 — Brique optionnelle, activable par configuration YAML
> Algorithme : NetworkX + Louvain Community Detection
> Dernière mise à jour : 17 avril 2026 — Phase 0

---

## 1. POURQUOI L'ANALYSE DE GRAPHE EST EN V1

La fraude en réseau (collusion prestataire-assuré, soins fantômes organisés) est **invisible à l'analyse individuelle des dossiers**. L'Isolation Forest analyse chaque dossier isolément — il ne peut pas voir qu'un praticien concentre 80% des sinistres d'un groupe d'assurés d'une même entreprise.

L'analyse de graphe comble cette lacune en modélisant les **relations entre entités** et en détectant les communautés anormalement denses.

---

## 2. STRUCTURE DU GRAPHE

### Nœuds
| Type | Identifiant | Attributs |
|---|---|---|
| Assuré | `ID_Assure` | Age, sexe, région, nb_sinistres |
| Praticien | `ID_Praticien` | Spécialité, région, ratio_prix_moyen |
| Établissement | `ID_Etablissement` | Type, région |
| Employeur | `ID_Employeur` | Secteur, taille |

### Arêtes
| Type | Entre | Poids |
|---|---|---|
| `A_CONSULTE` | Assuré → Praticien | Nombre de consultations |
| `FACTURE_PAR` | Sinistre → Praticien | Montant facturé |
| `EMPLOYE_PAR` | Assuré → Employeur | — |
| `SOIGNE_A` | Assuré → Établissement | Nombre de visites |

---

## 3. CODE DE RÉFÉRENCE

```python
# core/graph_engine.py

import networkx as nx
import pandas as pd
import numpy as np

try:
    from community import community_louvain
    LOUVAIN_AVAILABLE = True
except ImportError:
    LOUVAIN_AVAILABLE = False

def build_bipartite_graph(
    df: pd.DataFrame,
    node_entities: list[str],
    edge_weight_col: str
) -> nx.Graph:
    """
    Construit un graphe bipartite entre entités.
    node_entities = ["ID_Praticien", "ID_Assure"]
    """
    G = nx.Graph()

    for _, row in df.iterrows():
        source = row[node_entities[0]]
        target = row[node_entities[1]]
        weight = row.get(edge_weight_col, 1.0)

        if G.has_edge(source, target):
            G[source][target]["weight"] += weight
            G[source][target]["count"] += 1
        else:
            G.add_edge(source, target, weight=weight, count=1)

    return G

def detect_suspicious_communities(
    G: nx.Graph,
    algorithm: str = "louvain",
    min_community_size: int = 3
) -> list[dict]:
    """
    Détecte les communautés suspectes.
    Retourne une liste de communautés avec leurs métriques.
    """
    if algorithm == "louvain" and LOUVAIN_AVAILABLE:
        partition = community_louvain.best_partition(G)
    else:
        # Fallback : composantes connexes
        partition = {}
        for i, component in enumerate(nx.connected_components(G)):
            for node in component:
                partition[node] = i

    # Grouper par communauté
    communities = {}
    for node, comm_id in partition.items():
        if comm_id not in communities:
            communities[comm_id] = []
        communities[comm_id].append(node)

    # Calculer métriques par communauté
    suspicious = []
    for comm_id, nodes in communities.items():
        if len(nodes) < min_community_size:
            continue

        subgraph = G.subgraph(nodes)
        avg_weight = np.mean([d["weight"] for _, _, d in subgraph.edges(data=True)])
        density = nx.density(subgraph)

        suspicious.append({
            "community_id": comm_id,
            "size": len(nodes),
            "nodes": nodes,
            "avg_transaction_weight": avg_weight,
            "density": density,
            "is_suspicious": density > 0.5 and len(nodes) >= 5
        })

    return sorted(suspicious, key=lambda x: x["density"], reverse=True)

def compute_node_anomaly_flags(
    df: pd.DataFrame,
    suspicious_communities: list[dict],
    node_col: str = "ID_Praticien"
) -> pd.DataFrame:
    """
    Ajoute un flag graph_anomaly au DataFrame pour les nœuds dans des
    communautés suspectes.
    """
    df = df.copy()
    suspicious_nodes = set()

    for comm in suspicious_communities:
        if comm["is_suspicious"]:
            suspicious_nodes.update(comm["nodes"])

    df["graph_anomaly_flag"] = df[node_col].isin(suspicious_nodes).astype(int)
    df["graph_community_id"] = df[node_col].map(
        {node: comm["community_id"]
         for comm in suspicious_communities
         for node in comm["nodes"]}
    )
    return df
```

---

## 4. INTÉGRATION DANS LA SORTIE RCA

```json
{
  "graph_analysis": {
    "enabled": true,
    "community_id": 7,
    "community_size": 12,
    "community_density": 0.73,
    "is_suspicious_community": true,
    "rca_graph": {
      "category": "Fraude Intentionnelle",
      "subcategory": "Fraude en Réseau / Collusion",
      "explanation_fr": "Ce praticien appartient à une communauté de 12 entités présentant une densité de transactions anormalement élevée (0.73). Une investigation de réseau est recommandée."
    }
  }
}
```

---

## 5. CONTRAINTES SUR LE DATASET

Pour que la brique graphe soit activable, le dataset doit contenir :
- `ID_Praticien` : identifiant stable par praticien (hash pseudonymisé)
- `ID_Assure` : identifiant stable par assuré
- `ID_Employeur` : identifiant de l'employeur (optionnel mais fort signal)
- Minimum **50 dossiers par praticien** pour que le graphe soit dense
- Distribution **non-uniforme** des praticiens (sinon pas de communautés détectables)

---

*Fin du fichier GRAPH_ANALYSIS.md*
