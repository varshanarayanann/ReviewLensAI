CREATE TABLE analysis_targets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES auth.users (id),
    name VARCHAR(120) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    source_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT review_platform CHECK (platform IN ('google_maps'))
);

CREATE INDEX ix_analysis_targets_owner_id ON analysis_targets (owner_id);
