-- Action items belong to one AnalysisTarget and inherit ownership through it.
CREATE TABLE action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_id UUID NOT NULL REFERENCES analysis_targets(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
    description TEXT,
    priority VARCHAR(32) NOT NULL DEFAULT 'medium' CHECK (
        priority IN ('low', 'medium', 'high')
    ),
    status VARCHAR(32) NOT NULL DEFAULT 'open' CHECK (
        status IN ('open', 'in_progress', 'done')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX action_items_target_created_idx
    ON action_items (target_id, created_at, id);

-- No public Data API access; the backend enforces verified parent ownership.
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
