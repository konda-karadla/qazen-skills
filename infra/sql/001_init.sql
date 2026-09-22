-- QAZen Agentic QA Framework -- Phase 0 schema
-- Minimal starting model per plan: runs, artifacts, skill_executions, human_reviews,
-- test_cases, test_executions, knowledge_items.
-- LangGraph's Postgres checkpointer manages its own tables in this same database
-- (created automatically on first use) -- not defined here.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- runs: one row per pipeline invocation (one Orchestrator/LangGraph run)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    run_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requirement_id    TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'running', 'paused', 'completed', 'failed', 'cancelled')),
    current_stage     TEXT,               -- e.g. 'S1', 'H1', 'S3', ...
    framework_version TEXT,
    rulebook_version  TEXT,               -- AGENT_INSTRUCTIONS.md version this run is bound to
    model_version      TEXT,               -- LLM Gateway backend/model identifier
    base_url          TEXT,               -- New Run Application / Base URL (passthrough)
    environment       TEXT,               -- New Run environment label (passthrough)
    branch            TEXT,               -- New Run branch label (passthrough)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- artifacts: every versioned output a skill produces (S1..S11), immutable once written
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id        UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    type          TEXT NOT NULL,          -- e.g. 's1_normalized_requirement', 's3_test_case', 's5_automation_model'
    version       INTEGER NOT NULL DEFAULT 1,
    content       JSONB NOT NULL,         -- the schema-validated skill output
    storage_uri   TEXT,                   -- MinIO pointer, if the artifact also has a file form (e.g. .spec.ts)
    checksum      TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, type, version)
);

-- ---------------------------------------------------------------------------
-- skill_executions: one row per LLM Gateway call (S1..S11 invocation record)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skill_executions (
    execution_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    skill           TEXT NOT NULL,        -- 'S1'..'S11'
    prompt_version  TEXT,                 -- skill.md content hash/version used
    model           TEXT,                 -- LLM model identifier used for this call
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'succeeded', 'failed', 'escalated', 'schema_invalid_retry')),
    retry_count     INTEGER NOT NULL DEFAULT 0,
    escalation_reason TEXT,
    input_ref       UUID REFERENCES artifacts(artifact_id),
    output_ref      UUID REFERENCES artifacts(artifact_id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- human_reviews: one row per human decision at a gate (H1..H5)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS human_reviews (
    review_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id           UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    gate             TEXT NOT NULL CHECK (gate IN ('H1', 'H2', 'H3', 'H4', 'H5')),
    artifact_id      UUID REFERENCES artifacts(artifact_id),
    artifact_version INTEGER,
    decision         TEXT NOT NULL DEFAULT 'pending'
                     CHECK (decision IN ('pending', 'approved', 'rejected', 'changes_requested')),
    reviewer         TEXT,
    comment          TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at       TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- test_cases: versioned, requirement-linked (S3 output, denormalized for querying)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS test_cases (
    test_case_id        TEXT NOT NULL,     -- e.g. 'TC-001', stable across versions
    run_id               UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    version              INTEGER NOT NULL DEFAULT 1,
    source_requirement_id TEXT NOT NULL,
    layer                TEXT NOT NULL CHECK (layer IN ('UI', 'API', 'both')),
    obligation           TEXT,
    expected_result      TEXT,
    expected_result_basis TEXT,
    duplicate_of         TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, test_case_id, version)
);

-- ---------------------------------------------------------------------------
-- test_executions: S6 results + S7 classification, one row per test per run
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS test_executions (
    execution_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    test_case_id    TEXT NOT NULL,
    correlation_id  TEXT,
    status          TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'skip')),
    classification  TEXT CHECK (classification IN (
                        'APPLICATION_BUG', 'AUTOMATION_ERROR', 'TEST_DATA_ERROR',
                        'ENVIRONMENT_FAILURE', 'NETWORK_FAILURE', 'FLAKINESS',
                        'UNCLASSIFIED_PENDING_TRIAGE')),
    retry_attempts  INTEGER NOT NULL DEFAULT 0,
    evidence_manifest JSONB,              -- pointers into MinIO
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- knowledge_items: Domain Knowledge Store, versioned rules, never deleted
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_items (
    knowledge_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain         TEXT NOT NULL,          -- project/feature area
    rule           TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'confirmed'
                   CHECK (status IN ('confirmed', 'superseded')),
    source         TEXT,                   -- e.g. 'H1 decision on run <id>'
    supersedes     UUID REFERENCES knowledge_items(knowledge_id),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_skill_executions_run_id ON skill_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_human_reviews_run_id_gate ON human_reviews(run_id, gate);
CREATE INDEX IF NOT EXISTS idx_test_cases_run_id ON test_cases(run_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_run_id ON test_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_domain ON knowledge_items(domain);
