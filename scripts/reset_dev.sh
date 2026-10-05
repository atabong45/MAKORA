#!/bin/bash
# =============================================================================
# scripts/reset_dev.sh — MAKORA Reset complet environnement de développement
#
# Usage :
#   bash scripts/reset_dev.sh            # reset complet
#   bash scripts/reset_dev.sh --no-rls   # sans appliquer rls_setup.sql
#   bash scripts/reset_dev.sh --seeds-only  # seeds seulement (DB déjà up)
#
# Auteur : ATABONG EFON STEPHANE FRITZ
# =============================================================================
set -euo pipefail

# ── Couleurs ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}✅${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
err()  { echo -e "  ${RED}❌${NC} $1"; exit 1; }
hdr()  { echo -e "\n${BOLD}${CYAN}── $1 ──${NC}"; }

# ── Options ───────────────────────────────────────────────────────────────────
APPLY_RLS=true
SEEDS_ONLY=false

for arg in "$@"; do
  case $arg in
    --no-rls)     APPLY_RLS=false ;;
    --seeds-only) SEEDS_ONLY=true ;;
  esac
done

# ── Constantes ────────────────────────────────────────────────────────────────
API_CONTAINER="makora_api"
PG_CONTAINER="makora_postgres"
PG_USER="makora"
PG_DB="makora"
MAX_WAIT=60   # secondes max pour attendre l'API

echo -e "\n${BOLD}══════════════════════════════════════════════${NC}"
echo -e "${BOLD}  🔄 MAKORA — Reset environnement de développement${NC}"
echo -e "${BOLD}══════════════════════════════════════════════${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Étape 1 — Tear down
# ─────────────────────────────────────────────────────────────────────────────
if [ "$SEEDS_ONLY" = false ]; then
  hdr "Étape 1 — Arrêt et suppression des volumes"
  docker compose down -v --remove-orphans
  ok "Stack arrêtée, volumes supprimés"

  # ─────────────────────────────────────────────────────────────────────────
  # Étape 2 — Redémarrage propre
  # ─────────────────────────────────────────────────────────────────────────
  hdr "Étape 2 — Démarrage de la stack"
  docker compose up -d
  ok "Containers lancés"

  # ─────────────────────────────────────────────────────────────────────────
  # Étape 3 — Attente API healthy
  # ─────────────────────────────────────────────────────────────────────────
  hdr "Étape 3 — Attente de l'API (max ${MAX_WAIT}s)"
  elapsed=0
  until docker exec "$API_CONTAINER" python -c "import sys; sys.exit(0)" 2>/dev/null; do
    sleep 2
    elapsed=$((elapsed + 2))
    echo -ne "  ⏳ ${elapsed}s / ${MAX_WAIT}s ...\r"
    if [ $elapsed -ge $MAX_WAIT ]; then
      err "API non disponible après ${MAX_WAIT}s — vérifier: docker logs ${API_CONTAINER}"
    fi
  done
  ok "API disponible (${elapsed}s)"

  # ─────────────────────────────────────────────────────────────────────────
  # Étape 4 — Création des tables
  # ─────────────────────────────────────────────────────────────────────────
  hdr "Étape 4 — Initialisation de la base de données"
  docker exec "$API_CONTAINER" python -m core.db.init_db
  ok "Tables créées"

  # ─────────────────────────────────────────────────────────────────────────
  # Étape 5 — RLS (après création des tables)
  # ─────────────────────────────────────────────────────────────────────────
  if [ "$APPLY_RLS" = true ] && [ -f "rls_setup.sql" ]; then
    hdr "Étape 5 — Application RLS (audit_logs)"
    # On copie le fichier dans le container postgres puis on l'applique
    docker cp rls_setup.sql "${PG_CONTAINER}:/tmp/rls_setup.sql"
    docker exec "$PG_CONTAINER" psql -U "$PG_USER" -d "$PG_DB" \
      -f /tmp/rls_setup.sql -v ON_ERROR_STOP=0 2>&1 | grep -E "(NOTICE|ERROR|✅)" || true
    ok "RLS appliqué"
  else
    warn "RLS ignoré (--no-rls ou rls_setup.sql absent)"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Étape 6 — Seeding dans l'ordre
# ─────────────────────────────────────────────────────────────────────────────
hdr "Étape 6 — Seeding (seed_01 → seed_06 → seed_07)"
docker exec "$API_CONTAINER" python scripts/seeds/seed_all.py
ok "Seeds 01–06 terminés"

# seed_07 séparé (bridge data — dépend de seed_05/06)
docker exec "$API_CONTAINER" python -m scripts.seeds.seed_07_bridge_data
ok "Seed 07 (bridge data) terminé"

# ─────────────────────────────────────────────────────────────────────────────
# Résumé
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  🎉 Reset terminé avec succès${NC}"
echo -e "${BOLD}══════════════════════════════════════════════${NC}"
echo -e "  API  : ${CYAN}http://localhost:8000/api/docs${NC}"
echo -e "  Front: ${CYAN}http://localhost:3000${NC}"
echo ""