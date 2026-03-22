-- Apriori Association Rules - Database Schema
-- This runs against the same PostgreSQL database as sales-insight-service

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

    -- Algorithm configuration
    min_support NUMERIC(6, 4) NOT NULL DEFAULT 0.01,
    min_confidence NUMERIC(6, 4) NOT NULL DEFAULT 0.20,
    min_lift NUMERIC(6, 2) NOT NULL DEFAULT 1.0,
    max_itemset_size INTEGER NOT NULL DEFAULT 3,
    max_rules INTEGER NOT NULL DEFAULT 500,

    -- Input filters
    fecha_inicio DATE,
    fecha_fin DATE,
    id_departamento VARCHAR(50),
    id_seccion VARCHAR(50),

    -- Execution metadata
    total_transactions INTEGER,
    total_products INTEGER,
    rules_generated INTEGER,
    execution_time_secs NUMERIC(8, 2),

    -- Error handling
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Extensible metadata
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_status ON analysis_runs(status);
CREATE INDEX IF NOT EXISTS idx_analysis_runs_created ON analysis_runs(created_at DESC);

-- Association rules table
CREATE TABLE IF NOT EXISTS association_rules (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,

    -- Rule components
    antecedents TEXT[] NOT NULL,
    consequents TEXT[] NOT NULL,
    antecedent_label TEXT NOT NULL,
    consequent_label TEXT NOT NULL,

    -- Metrics
    support NUMERIC(8, 6) NOT NULL,
    confidence NUMERIC(8, 6) NOT NULL,
    lift NUMERIC(8, 4) NOT NULL,
    conviction NUMERIC(10, 4),
    leverage NUMERIC(10, 6),

    -- Category info
    antecedent_section VARCHAR(50),
    consequent_section VARCHAR(50),
    antecedent_department VARCHAR(50),
    consequent_department VARCHAR(50),

    -- Strength classification
    strength VARCHAR(10) NOT NULL DEFAULT 'weak'
        CHECK (strength IN ('strong', 'medium', 'weak')),

    -- LLM interpretation cache
    llm_explanation TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for association_rules
CREATE INDEX IF NOT EXISTS idx_rules_run_id ON association_rules(run_id);
CREATE INDEX IF NOT EXISTS idx_rules_lift ON association_rules(lift DESC);
CREATE INDEX IF NOT EXISTS idx_rules_confidence ON association_rules(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_rules_antecedents ON association_rules USING gin(antecedents);
CREATE INDEX IF NOT EXISTS idx_rules_consequents ON association_rules USING gin(consequents);
CREATE INDEX IF NOT EXISTS idx_rules_strength ON association_rules(strength);
