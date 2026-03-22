-- Analysis tables for Apriori v2
-- Run against the shared sales_db database

-- Enum type for analysis status
DO $$ BEGIN
    CREATE TYPE analysis_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Analysis runs table
CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status analysis_status NOT NULL DEFAULT 'pending',
    min_support NUMERIC(6, 4) NOT NULL DEFAULT 0.01,
    min_confidence NUMERIC(6, 4) NOT NULL DEFAULT 0.20,
    min_lift NUMERIC(6, 2) NOT NULL DEFAULT 1.0,
    fecha_inicio TIMESTAMP WITHOUT TIME ZONE,
    fecha_fin TIMESTAMP WITHOUT TIME ZONE,
    id_departamento VARCHAR(50),
    id_seccion VARCHAR(50),
    total_transactions INTEGER,
    total_products INTEGER,
    rules_generated INTEGER,
    execution_time_secs NUMERIC(8, 2),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_status ON analysis_runs (status);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_created ON analysis_runs (created_at DESC);

-- Association rules table
CREATE TABLE IF NOT EXISTS association_rules (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    antecedents TEXT[] NOT NULL,
    consequents TEXT[] NOT NULL,
    support NUMERIC(8, 6) NOT NULL,
    confidence NUMERIC(8, 6) NOT NULL,
    lift NUMERIC(8, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rules_run_id ON association_rules (run_id);
CREATE INDEX IF NOT EXISTS idx_rules_lift ON association_rules (lift DESC);
CREATE INDEX IF NOT EXISTS idx_rules_confidence ON association_rules (confidence DESC);
CREATE INDEX IF NOT EXISTS idx_rules_antecedents ON association_rules USING GIN (antecedents);
CREATE INDEX IF NOT EXISTS idx_rules_consequents ON association_rules USING GIN (consequents);

-- Materialized views
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_transaction_summary AS
SELECT
    fecha,
    id_departamento,
    id_seccion,
    COUNT(DISTINCT id_pedido) AS total_transactions,
    COUNT(DISTINCT id_producto) AS total_products,
    COUNT(id_producto)::FLOAT / NULLIF(COUNT(DISTINCT id_pedido), 0) AS avg_products_per_purchase
FROM tickets
GROUP BY fecha, id_departamento, id_seccion
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_txn_summary
    ON mv_transaction_summary (fecha, id_departamento, id_seccion);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_top_products AS
SELECT
    fecha,
    id_departamento,
    id_seccion,
    nombre_producto,
    COUNT(DISTINCT id_pedido) AS transaction_count
FROM tickets
GROUP BY fecha, id_departamento, id_seccion, nombre_producto
WITH DATA;

CREATE INDEX IF NOT EXISTS idx_mv_top_products
    ON mv_top_products (fecha, id_departamento, id_seccion);
