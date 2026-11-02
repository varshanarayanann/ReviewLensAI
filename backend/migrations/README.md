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
