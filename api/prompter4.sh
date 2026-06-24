#!/bin/bash
# ============================================================
# prompter.sh — Générateur de contexte projet MAKORA
# Version 3.0 — Juin 2026
#
# SECTION 1 — Arborescence complète (TOUS les fichiers + taille)
#             Seuls __pycache__, .pytest_cache, node_modules,
#             venv et assimilés sont exclus. Tout le reste
#             apparaît : .env, data/, results/, docs/, etc.
#
# SECTION 2 — Contenu des fichiers selon ces règles :
#
#   EXCLUS TOTALEMENT (silencieux, ni S1 ni S2) :
#     → fichiers 0 octet (parasites : pd, sys, pytest...)
#     → project_context.txt (fichier de sortie)
#     → package-lock.json, yarn.lock, *.log, etc.
#
#   LISTING ONLY dans S2 (chemin + taille, pas de contenu) :
#     → extensions binaires : .pyc .joblib .pkl .npy .parquet
#                              .h5 .pt .bin .png .jpg .gif .ico
#                              .sqlite .jar .class .swp .bak .tmp
#     → data/raw/  data/processed/  data/splits/  data/models/
#     → JSON > 10K hors JSON_WHITELIST
#
#   CONTENU COMPLET (tout le reste) :
#     → code Python, YAML, Markdown, SQL, Shell
#     → .env, requirements*.txt, Dockerfile*, docker-compose*
#     → context/, docs/, modules/, core/, api/, tests/, scripts/
#     → JSON ≤ 10K + JSON dans JSON_WHITELIST (résultats clés)
#
# Robustesse à l'évolution :
#     → Règles basées sur extensions et noms de dossiers.
#       Ajouter un nouveau module (ex: vie/) → rien à changer.
#       Seul LISTING_ONLY_DIR_PREFIXES peut nécessiter une mise
#       à jour si la structure de data/ change.
#
# Usage :
#   ./prompter.sh                   # depuis la racine du projet
#   ./prompter.sh /chemin/projet
# ============================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────

DEFAULT_PROJECT_PATH="."
PROJECT_PATH="${1:-$DEFAULT_PROJECT_PATH}"
OUTPUT_FILENAME="project_context.txt"

# Dossiers exclus TOTALEMENT (S1 et S2) — exclusion par nom récursif
EXCLUDE_DIRS_BY_NAME=(
    "__pycache__"
    ".pytest_cache"
    "node_modules"
    "vendor"
    "build"
    "dist"
    "target"
    ".next"
    "venv"
    ".venv"
    "env"
    "storage"
)

# Dossiers listing-only dans S2 (visibles en S1)
# Préfixes de chemin relatif depuis la racine du projet
LISTING_ONLY_DIR_PREFIXES=(
    "data/raw/"
    "data/processed/"
    "data/splits/"
    "data/models/"
)

# Extensions listing-only dans S2 (binaires, images, données volumineuses)
# "csv" inclus : les CSV de referentials/ (60K chacun) sont du bruit pour l'IA.
# Les CSV utiles (sha256, petits configs) n'existent pas dans ce projet.
BINARY_EXTENSIONS=(
    "pyc" "joblib" "pkl" "npy" "parquet" "csv"
    "h5" "pt" "bin" "png" "jpg" "jpeg" "gif" "ico"
    "sqlite" "jar" "class" "swp" "bak" "tmp"
)

# Fichiers exclus totalement par nom exact
EXCLUDE_FILES_EXACT=(
    "$OUTPUT_FILENAME"
)

# Fichiers exclus totalement par pattern glob
EXCLUDE_FILES_PATTERN=(
    "package-lock.json"
    "yarn.lock"
    "composer.lock"
    "pnpm-lock.yaml"
    "*.log"
)

# JSON toujours inclus en contenu complet (résultats scientifiques clés)
JSON_WHITELIST=(
    "metrics_final.json"
    "t10_3_if_results.json"
    "t10_4_challengers_results.json"
    "t10_5_learning_curves.json"
    "t10_7_comparative_table.json"
    "convergence_report.json"
    "rif_results.json"
    "eda_overview.json"
    "eif_params.json"
    "model_card.json"
    "t12_1_models_metrics.json"
    "t12_2_delta_results.json"
    "split_metadata.json"
)

# Seuil taille JSON hors whitelist : au-delà → listing only
JSON_SIZE_THRESHOLD=10240   # 10 Ko

# ============================================================
# Fonctions utilitaires
# ============================================================

human_size() {
    local bytes="$1"
    if [ "$bytes" -ge 1048576 ]; then
        # Mo avec 1 décimale, calcul entier (insensible à la locale)
        local whole=$(( bytes / 1048576 ))
        local frac=$(( (bytes % 1048576) * 10 / 1048576 ))
        printf "%d.%dM" "$whole" "$frac"
    elif [ "$bytes" -ge 1024 ]; then
        printf "%dK" "$(( bytes / 1024 ))"
    else
        printf "%dB" "$bytes"
    fi
}

file_size() {
    stat -c%s "$1" 2>/dev/null || stat -f%z "$1" 2>/dev/null || echo 0
}

is_in_listing_only_dir() {
    local rel=""$1""
    for prefix in "${LISTING_ONLY_DIR_PREFIXES[@]}"; do
        [[ "$rel" == "$prefix"* ]] && return 0
    done
    return 1
}

has_binary_ext() {
    local fname="$1"
    local ext="${fname##*.}"
    ext="${ext,,}"
    [[ "$fname" == "$ext" ]] && return 1   # pas d'extension
    for e in "${BINARY_EXTENSIONS[@]}"; do
        [[ "$ext" == "$e" ]] && return 0
    done
    return 1
}

is_json_whitelisted() {
    local fname="$1"
    for w in "${JSON_WHITELIST[@]}"; do
        [[ "$fname" == "$w" ]] && return 0
    done
    return 1
}

is_fully_excluded() {
    local fname="$2"
    local bytes="$3"
    [[ "$bytes" -eq 0 ]] && return 0
    for excl in "${EXCLUDE_FILES_EXACT[@]}"; do
        [[ "$fname" == "$excl" ]] && return 0
    done
    for pattern in "${EXCLUDE_FILES_PATTERN[@]}"; do
        case "$fname" in $pattern) return 0 ;; esac
    done
    return 1
}

# ── Construit le bloc -prune pour find ──────────────────────
# Utilisation : find BASE $(exclude_dirs_prune) -type f -print
exclude_dirs_prune() {
    local first=true
    printf '\('
    for d in "${EXCLUDE_DIRS_BY_NAME[@]}"; do
        $first || printf ' -o'
        printf ' -name "%s" -type d' "$d"
        first=false
    done
    printf ' \) -prune -o'
}

# ============================================================
# Initialisation
# ============================================================

PROJECT_PATH=$(realpath "$PROJECT_PATH")
OUTPUT_FILE="$PROJECT_PATH/$OUTPUT_FILENAME"
rm -f "$OUTPUT_FILE"

# ============================================================
# EN-TÊTE
# ============================================================
{
echo "Project Context — MAKORA Backend"
echo "Generated  : $(date)"
echo "Root       : $PROJECT_PATH"
echo "Strategy   :"
echo "  S1 = Arborescence complète (tous fichiers, hors dépendances)"
echo "  S2 = Contenu complet : code, configs, docs, petits JSON"
echo "       Listing only    : data/raw|processed|splits|models,"
echo "                         binaires, gros JSON (>10K hors whitelist)"
echo "       Exclus total    : fichiers 0B, __pycache__, locks, .log"
echo "==============================================================="
echo ""
} > "$OUTPUT_FILE"

# ============================================================
# SECTION 1 — ARBORESCENCE COMPLÈTE
# Tout apparaît ici sauf les dossiers de dépendances.
# Objectif : l'IA sait exactement ce qui existe sur disque.
# ============================================================
{
echo "==============================================================="
echo "SECTION 1 — ARBORESCENCE COMPLÈTE DU PROJET"
echo "(tous fichiers sur disque, hors dépendances compilées)"
echo "Colonnes : taille    chemin/relatif/depuis/racine"
echo "==============================================================="
echo ""
} >> "$OUTPUT_FILE"

find "$PROJECT_PATH" \
    \( -name "__pycache__" -o -name ".pytest_cache" -o \
       -name "node_modules" -o -name "venv" -o -name ".venv" -o \
       -name "build" -o -name "dist" -o -name "target" -o \
       -name ".next" -o -name "vendor" -o -name "storage" -o \
       -name "env" \
    \) -type d -prune \
    -o -type f -not -name "$OUTPUT_FILENAME" -print \
| sort \
| while IFS= read -r fpath; do
    rel="${fpath#$PROJECT_PATH/}"
    bytes=$(file_size "$fpath")
    hr=$(human_size "$bytes")
    printf "%-10s %s\n" "$hr" "$rel"
done >> "$OUTPUT_FILE"

{
echo ""
echo "// FIN SECTION 1"
echo ""
} >> "$OUTPUT_FILE"

# ============================================================
# SECTION 2 — CONTENU DES FICHIERS
# ============================================================
{
echo "==============================================================="
echo "SECTION 2 — CONTENU DES FICHIERS"
echo "  [BINARY] = extension binaire, contenu non textuel"
echo "  [DATA]   = dossier data volumineuse (raw/processed/splits/models)"
echo "  [JSON-L] = JSON > 10K hors whitelist"
echo "==============================================================="
echo ""
} >> "$OUTPUT_FILE"

error_count=0

while IFS= read -r FILE_PATH; do
    RELATIVE_PATH="${FILE_PATH#$PROJECT_PATH/}"
    FILENAME=$(basename "$FILE_PATH")
    BYTES=$(file_size "$FILE_PATH")
    HR=$(human_size "$BYTES")
    EXT="${FILENAME##*.}"; EXT="${EXT,,}"

    # 1. Exclusion totale (0B, locks, .log, output lui-même)
    if is_fully_excluded "$RELATIVE_PATH" "$FILENAME" "$BYTES"; then
        continue
    fi


    # 2. Extension binaire → listing only
    if has_binary_ext "$FILENAME"; then
        echo "// [BINARY] $RELATIVE_PATH  ($HR)" >> "$OUTPUT_FILE"
        continue
    fi

    # 3. JSON whitelisté → contenu complet immédiat, peu importe le dossier.
    # DOIT être avant le filtre dossier : eif_params.json, model_card.json et
    # split_metadata.json sont dans data/models/ ou data/splits/ et seraient
    # capturés par LISTING_ONLY_DIR_PREFIXES avant d'arriver à la whitelist.
    if [[ "$EXT" == "json" ]] && is_json_whitelisted "$FILENAME"; then
        {
            echo "// ────────────────────────────────────────────────────────"
            echo "// FILE: $RELATIVE_PATH  ($HR)"
            echo "// ────────────────────────────────────────────────────────"
            echo ""
            if ! cat "$FILE_PATH" 2>/dev/null; then
                echo "[Erreur de lecture]"
                (( error_count++ ))
            fi
            echo ""
            echo "// END: $RELATIVE_PATH"
            echo ""
        } >> "$OUTPUT_FILE"
        continue
    fi

    # 4. Dossier data volumineuse → listing only
    if is_in_listing_only_dir "$RELATIVE_PATH"; then
        echo "// [DATA]   $RELATIVE_PATH  ($HR)" >> "$OUTPUT_FILE"
        continue
    fi

    # 5. JSON lourd hors whitelist → listing only
    # (la whitelist a déjà été traitée à l'étape 3, pas besoin de revérifier)
    if [[ "$EXT" == "json" ]] && [ "$BYTES" -gt "$JSON_SIZE_THRESHOLD" ]; then
        echo "// [JSON-L] $RELATIVE_PATH  ($HR)" >> "$OUTPUT_FILE"
        continue
    fi


    # 6. Contenu complet
    {
        echo "// ────────────────────────────────────────────────────────"
        echo "// FILE: $RELATIVE_PATH  ($HR)"
        echo "// ────────────────────────────────────────────────────────"
        echo ""
        if ! cat "$FILE_PATH" 2>/dev/null; then
            echo "[Erreur de lecture]"
            (( error_count++ ))
        fi
        echo ""
        echo "// END: $RELATIVE_PATH"
        echo ""
    } >> "$OUTPUT_FILE"

done < <(
    find "$PROJECT_PATH" \
        \( -name "__pycache__" -o -name ".pytest_cache" -o \
           -name "node_modules" -o -name "venv" -o -name ".venv" -o \
           -name "build" -o -name "dist" -o -name "target" -o \
           -name ".next" -o -name "vendor" -o -name "storage" -o \
           -name "env" \
        \) -type d -prune \
        -o -type f -not -name "$OUTPUT_FILENAME" -print \
    | sort
)

# ── Résumé final ─────────────────────────────────────────────
TOTAL_SIZE=$(file_size "$OUTPUT_FILE")
TOTAL_HR=$(human_size "$TOTAL_SIZE")

{
echo ""
echo "==============================================================="
echo "FIN DU CONTEXTE MAKORA"
echo "Fichier : $OUTPUT_FILE"
echo "Taille  : $TOTAL_HR"
[ "$error_count" -gt 0 ] && echo "ATTENTION : $error_count erreur(s) de lecture."
echo "==============================================================="
} >> "$OUTPUT_FILE"

if [ "$error_count" -gt 0 ]; then
    echo "⚠ $error_count erreur(s) de lecture." >&2
    exit 1
fi

echo "✓ Contexte généré : $OUTPUT_FILE  ($TOTAL_HR)"
exit 0
