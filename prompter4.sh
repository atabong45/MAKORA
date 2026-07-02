#!/bin/bash
# ============================================================
# prompter.sh — Générateur de contexte projet MAKORA
# Version 4.1 — Juillet 2026
#
# CORRECTIFS v4.1 (par rapport à v4.0) :
#   1. .git/ exclu totalement (S1 et S2) — ajout au prune find
#   2. results/ ajouté en listing-only (JSON lourds : lime_sample,
#      top3_features, eda_signal_report, t12_3_fp_fn_all...)
#   3. prompter4.sh exclu par pattern glob (couvre api/prompter4.sh)
#   4. En-tête mis à jour pour refléter ces règles
#
# SECTION 1 — Arborescence complète (TOUS les fichiers + taille)
#             Seuls __pycache__, .pytest_cache, node_modules,
#             venv, .git et assimilés sont exclus. Tout le reste apparaît.
#
# SECTION 2 — Contenu des fichiers selon ces règles :
#
#   EXCLUS TOTALEMENT (silencieux, ni S1 ni S2) :
#     → fichiers 0 octet
#     → project_context.txt (fichier de sortie)
#     → prompter4.sh (ce script, où qu'il soit)               ← v4.1
#     → package-lock.json, yarn.lock, *.log, etc.
#
#   LISTING ONLY dans S2 (chemin + taille, pas de contenu) :
#     [BINARY]   → extensions binaires : .pyc .joblib .pkl .npy .parquet
#                   .h5 .pt .bin .png .jpg .gif .ico .sqlite .jar .swp
#                   .pdf .docx .doc .xlsx .xls .pptx .ppt
#     [DATA]     → data/raw|processed|splits|models|documents
#                   docs/context/
#                   results/                                    ← v4.1
#     [JSON-L]   → JSON > 10K hors JSON_WHITELIST
#     [SCRIPT-L] → scripts ML terminés (t10_* t12_* t13_* _ml_common)
#
#   CONTENU COMPLET (tout le reste) :
#     → code Python actif, YAML, Markdown de travail, SQL, Shell
#     → .env, requirements*.txt, Dockerfile*, docker-compose*
#     → docs/doc_frontend/, docs/session/, docs/*.md (cahiers des charges)
#     → core/, api/, modules/, scripts/ actifs (seeds, generate_*)
#     → JSON ≤ 10K + JSON dans JSON_WHITELIST (résultats scientifiques)
#
# Usage :
#   ./prompter4.sh                   # depuis la racine du projet
#   ./prompter4.sh /chemin/projet
# ============================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────

DEFAULT_PROJECT_PATH="."
PROJECT_PATH="${1:-$DEFAULT_PROJECT_PATH}"
OUTPUT_FILENAME="project_context.txt"

# Dossiers listing-only dans S2 (toujours visibles en S1)
# Préfixes de chemin relatif depuis la racine du projet
LISTING_ONLY_DIR_PREFIXES=(
    "data/raw/"
    "data/processed/"
    "data/splits/"
    "data/models/"
    "data/documents/"   # PDFs/docs uploadés par les sinistres (OCR testing)
    "docs/context/"     # Anciens fichiers contexte IA, doublons déjà en PK
    "results/"          # v4.1 — JSON lourds (lime_sample, top3_features, eda_signal...)
)

# Extensions listing-only (binaires, images, Office, données volumineuses)
BINARY_EXTENSIONS=(
    "pyc" "joblib" "pkl" "npy" "parquet" "csv"
    "h5" "pt" "bin" "png" "jpg" "jpeg" "gif" "ico"
    "sqlite" "jar" "class" "swp" "bak" "tmp"
    "pdf" "docx" "doc" "xlsx" "xls" "pptx" "ppt"
)

# Fichiers exclus totalement par nom exact (basename)
EXCLUDE_FILES_EXACT=(
    "$OUTPUT_FILENAME"
)

# Fichiers exclus totalement par pattern glob (basename)
# v4.1 : prompter4.sh exclu par pattern pour couvrir api/prompter4.sh aussi
EXCLUDE_FILES_PATTERN=(
    "prompter4.sh"
    "package-lock.json"
    "yarn.lock"
    "composer.lock"
    "pnpm-lock.yaml"
    "*.log"
)

# v4.0 — Scripts ML terminés → listing-only par pattern de nom (basename)
# Training, évaluation, calibration, bootstrap CI : résultats figés en production
LISTING_ONLY_SCRIPTS=(
    "t10_*.py"
    "t12_*.py"
    "t13_*.py"
    "_ml_common.py"
)

# JSON toujours inclus en contenu complet (résultats scientifiques clés)
# Note : ces fichiers passent même s'ils sont dans un dossier listing-only
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
    local rel="$1"
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

# v4.0 — Retourne 0 si le fichier est un script ML terminé (listing-only)
is_listing_only_script() {
    local fname="$1"
    for pattern in "${LISTING_ONLY_SCRIPTS[@]}"; do
        case "$fname" in $pattern) return 0 ;; esac
    done
    return 1
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
echo "Version    : prompter4.sh v4.1"
echo "Strategy   :"
echo "  S1 = Arborescence complète (tous fichiers, hors .git et dépendances)"
echo "  S2 = Contenu complet : core/, api/, modules/, scripts/ actifs,"
echo "                          docs/doc_frontend/, docs/session/, docs/*.md"
echo "       [BINARY]   : binaires, PDF, Office"
echo "       [DATA]     : data/raw|processed|splits|models|documents, docs/context/, results/"
echo "       [JSON-L]   : JSON > 10K hors whitelist"
echo "       [SCRIPT-L] : scripts ML terminés (t10_* t12_* t13_* _ml_common)"
echo "       Exclus total: 0B, .git/, __pycache__, locks, .log, project_context.txt, prompter4.sh"
echo "==============================================================="
echo ""
} > "$OUTPUT_FILE"

# ============================================================
# SECTION 1 — ARBORESCENCE COMPLÈTE
# Tout apparaît ici sauf les dossiers de dépendances et .git.
# ============================================================
{
echo "==============================================================="
echo "SECTION 1 — ARBORESCENCE COMPLÈTE DU PROJET"
echo "(tous fichiers sur disque, hors .git et dépendances compilées)"
echo "Colonnes : taille    chemin/relatif/depuis/racine"
echo "==============================================================="
echo ""
} >> "$OUTPUT_FILE"

find "$PROJECT_PATH" \
    \( -name ".git" -o \
       -name "__pycache__" -o -name ".pytest_cache" -o \
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
echo "  [BINARY]   = extension binaire ou Office/PDF — contenu non textuel"
echo "  [DATA]     = dossier data volumineuse, docs/context/ ou results/"
echo "  [JSON-L]   = JSON > 10K hors whitelist"
echo "  [SCRIPT-L] = script ML terminé (training/évaluation) — résultats figés"
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

    # 1. Exclusion totale (0B, locks, .log, output, prompter4.sh)
    if is_fully_excluded "$RELATIVE_PATH" "$FILENAME" "$BYTES"; then
        continue
    fi

    # 2. Extension binaire (incl. PDF et Office) → listing only
    if has_binary_ext "$FILENAME"; then
        echo "// [BINARY]   $RELATIVE_PATH  ($HR)" >> "$OUTPUT_FILE"
        continue
    fi

    # 3. JSON whitelisté → contenu complet immédiat
    # Doit précéder le filtre dossier : certains JSON whitelistés sont dans
    # data/models/ ou data/splits/ (eif_params.json, split_metadata.json...)
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

    # 4. Script ML terminé → listing only
    if is_listing_only_script "$FILENAME"; then
        echo "// [SCRIPT-L] $RELATIVE_PATH  ($HR)" >> "$OUTPUT_FILE"
        continue
    fi

    # 5. Dossier data volumineuse, docs/context/ ou results/ → listing only
    if is_in_listing_only_dir "$RELATIVE_PATH"; then
        echo "// [DATA]     $RELATIVE_PATH  ($HR)" >> "$OUTPUT_FILE"
        continue
    fi

    # 6. JSON lourd hors whitelist → listing only
    if [[ "$EXT" == "json" ]] && [ "$BYTES" -gt "$JSON_SIZE_THRESHOLD" ]; then
        echo "// [JSON-L]   $RELATIVE_PATH  ($HR)" >> "$OUTPUT_FILE"
        continue
    fi

    # 7. Contenu complet
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
        \( -name ".git" -o \
           -name "__pycache__" -o -name ".pytest_cache" -o \
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
