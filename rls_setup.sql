-- ============================================================
-- rls_setup.sql — Politique Row Level Security pour audit_logs
-- MAKORA Framework — Conformité CIMA Art.12 + RGPD Art.5
--
-- À exécuter UNE FOIS par le superadmin PostgreSQL après create_tables().
-- Le rôle applicatif (makora_api_role) peut uniquement insérer.
-- Aucun UPDATE ni DELETE n'est possible via ce rôle.
--
-- Usage :
--   psql -U postgres -d makora -f rls_setup.sql
-- ============================================================

-- 1. Créer le rôle applicatif s'il n'existe pas
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'makora_api_role') THEN
        CREATE ROLE makora_api_role LOGIN PASSWORD 'changeme_in_production';
        RAISE NOTICE 'Rôle makora_api_role créé.';
    END IF;
END
$$;

-- 2. Accorder les permissions nécessaires au rôle applicatif
GRANT CONNECT ON DATABASE makora TO makora_api_role;
GRANT USAGE ON SCHEMA public TO makora_api_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO makora_api_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO makora_api_role;

-- 3. Activer RLS sur audit_logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- 4. Politique : INSERT uniquement via le rôle applicatif
--    (aucune policy pour SELECT/UPDATE/DELETE = opérations bloquées)
DROP POLICY IF EXISTS audit_insert_only ON audit_logs;
CREATE POLICY audit_insert_only
    ON audit_logs
    FOR INSERT
    TO makora_api_role
    WITH CHECK (true);

-- 5. Révoquer UPDATE et DELETE explicitement sur audit_logs
REVOKE UPDATE, DELETE ON audit_logs FROM makora_api_role;

-- 6. Vérification
SELECT tablename, rowsecurity
FROM pg_tables
WHERE tablename = 'audit_logs';
-- Résultat attendu : rowsecurity = true

SELECT policyname, cmd, roles
FROM pg_policies
WHERE tablename = 'audit_logs';
-- Résultat attendu : audit_insert_only | INSERT | {makora_api_role}

\echo '✅ RLS configuré sur audit_logs — immuabilité garantie.'
