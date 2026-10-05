-- ============================================================
-- MIGRATION : V002__add_resolved_by_escalations.sql
-- PROJET    : MAKORA — Phase 1, item 1.2
-- DATE      : 2026-07-02
-- AUTEUR    : ATABONG EFON STEPHANE FRITZ
-- ============================================================
-- DESCRIPTION :
--   Ajoute la colonne resolved_by (UUID, nullable) à la table
--   escalations pour tracer quel auditeur a résolu l'escalade.
--
--   Avant : la résolution ne traçait pas l'acteur (Bug 6).
--   Après : resolved_by = UUID de l'auditeur qui a soumis la
--           résolution via PATCH /escalations/{id}/resolve.
--
-- RÉFÉRENCES :
--   [Amershi2019] §IV.D — traçabilité HITL : chaque décision
--   doit être attribuée à un acteur identifié pour audit trail.
-- ============================================================

BEGIN;

-- Ajout de la colonne
ALTER TABLE escalations
    ADD COLUMN IF NOT EXISTS resolved_by UUID
        REFERENCES users(id)
        ON DELETE SET NULL;

-- Commentaire de colonne pour documentation DB
COMMENT ON COLUMN escalations.resolved_by IS
    'Auditeur ayant clôturé l''escalade via PATCH /resolve. '
    'NULL si non encore résolue. Peuplé atomiquement avec resolved_at.';

-- Index pour requêtes "escalades résolues par auditeur X"
CREATE INDEX IF NOT EXISTS idx_escalations_resolved_by
    ON escalations(resolved_by)
    WHERE resolved_by IS NOT NULL;

COMMIT;