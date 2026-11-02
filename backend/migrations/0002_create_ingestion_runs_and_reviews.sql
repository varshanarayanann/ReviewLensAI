CREATE TABLE ingestion_runs (
    id UUID PRIMARY KEY,
    target_id UUID NOT NULL REFERENCES analysis_targets(id),
    state VARCHAR(16) NOT NULL CHECK (state IN ('processing', 'succeeded', 'failed')),
    persisted_count INTEGER NOT NULL DEFAULT 0 CHECK (persisted_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE reviews (
    id UUID PRIMARY KEY,
    target_id UUID NOT NULL REFERENCES analysis_targets(id),
    run_id UUID NOT NULL REFERENCES ingestion_runs(id),
    review_text TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5)
);
