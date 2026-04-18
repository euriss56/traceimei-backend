-- ============================================================
-- TraceIMEI-BJ — Script SQL pour Supabase
-- Copie ce script dans l'éditeur SQL de ton dashboard Supabase
-- ============================================================

-- Table des enregistrements IMEI
CREATE TABLE IF NOT EXISTS imei_records (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    imei            VARCHAR(15) UNIQUE NOT NULL,
    brand           VARCHAR(100),
    model           VARCHAR(100),
    theft_date      DATE,
    location        VARCHAR(200),
    description     TEXT,
    reporter_id     UUID,
    is_stolen       BOOLEAN DEFAULT FALSE,
    status          VARCHAR(20) DEFAULT 'unknown',  -- 'clean', 'stolen', 'unknown'
    reported_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Table des vérifications (historique)
CREATE TABLE IF NOT EXISTS imei_checks (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    imei            VARCHAR(15) NOT NULL,
    result_stolen   BOOLEAN,
    ml_risk_level   VARCHAR(10),  -- 'low', 'medium', 'high', 'unknown'
    checked_at      TIMESTAMPTZ DEFAULT NOW(),
    checker_ip      VARCHAR(50)
);

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    password_hash   VARCHAR(64) NOT NULL,
    role            VARCHAR(20) DEFAULT 'user',  -- 'user', 'dealer', 'admin'
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour les recherches fréquentes
CREATE INDEX IF NOT EXISTS idx_imei_records_imei     ON imei_records(imei);
CREATE INDEX IF NOT EXISTS idx_imei_records_stolen   ON imei_records(is_stolen);
CREATE INDEX IF NOT EXISTS idx_imei_checks_imei      ON imei_checks(imei);
CREATE INDEX IF NOT EXISTS idx_imei_checks_date      ON imei_checks(checked_at);
CREATE INDEX IF NOT EXISTS idx_users_email           ON users(email);

-- Données de test (optionnel)
INSERT INTO imei_records (imei, brand, model, theft_date, location, is_stolen, status)
VALUES
    ('356938035643809', 'Samsung', 'Galaxy A54', '2024-11-15', 'Cotonou', TRUE, 'stolen'),
    ('352099001761481', 'Tecno',   'Spark 10',   '2024-12-01', 'Porto-Novo', TRUE, 'stolen'),
    ('013852003580595', 'Itel',    'A70',         '2025-01-10', 'Parakou', TRUE, 'stolen')
ON CONFLICT (imei) DO NOTHING;
