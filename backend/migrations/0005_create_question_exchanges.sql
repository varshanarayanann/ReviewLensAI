-- Saved Q&A inherits ownership through its AnalysisTarget.
CREATE TABLE question_exchanges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_id UUID NOT NULL REFERENCES analysis_targets(id) ON DELETE CASCADE,
    question TEXT NOT NULL CHECK (length(trim(question)) BETWEEN 1 AND 1000),
    answer TEXT,
    status VARCHAR(32) NOT NULL CHECK (
        status IN ('answered', 'insufficient_evidence', 'out_of_scope', 'no_reviews')
    ),
    review_count INTEGER NOT NULL CHECK (review_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        (status = 'no_reviews' AND answer IS NULL AND review_count = 0) OR
        (status <> 'no_reviews' AND answer IS NOT NULL
         AND length(trim(answer)) > 0 AND review_count > 0)
    )
);
CREATE INDEX question_exchanges_target_history_idx
    ON question_exchanges (target_id, created_at, id);

-- No public Data API access; the backend enforces verified parent ownership.
ALTER TABLE question_exchanges ENABLE ROW LEVEL SECURITY;
