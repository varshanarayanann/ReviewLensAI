# Database migrations

Version-controlled SQL migrations for the ReviewLens Postgres database (Supabase).

- One file per schema change, applied in filename order:
  `0001_create_analysis_targets.sql`, `0002_create_ingestion_runs.sql`, ...
- Never edit a migration that has already been applied to a shared database; add a new one instead.
- Apply a migration by running its SQL against the database in `DATABASE_URL`
  (Supabase Dashboard > SQL Editor, or `psql "$DATABASE_URL" -f <file>`).

Migration `0001_create_analysis_targets.sql` creates the AnalysisTarget table
with its Supabase Auth owner reference. Later migrations add IngestionRun and
Review as part of S1-022 and S1-023.

Migration `0003_enable_row_level_security.sql` turns on row level security with no
policies, so Supabase's public Data API roles cannot read or write ReviewLens tables
directly; only the backend can. **Every new table must enable RLS the same way.**

Migration `0005_create_question_exchanges.sql` adds target-owned saved Q&A pairs,
their stable history-order index, and RLS without public policies. Apply it before
deploying S3-006 backend changes: Q&A now commits history before returning success,
and target deletion explicitly removes history in its transaction. The migration
does not backfill exchanges from before persistence existed or change review data.

Migration `0006_create_action_items.sql` adds analysis-owned action items with
title, optional description, priority, status, timestamps, cascade delete with
the parent AnalysisTarget, and RLS without public policies. New rows default to
`open` status and `medium` priority. Apply it before deploying action-item APIs.
