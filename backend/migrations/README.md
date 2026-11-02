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
