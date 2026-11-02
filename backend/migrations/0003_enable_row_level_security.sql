-- Supabase grants its public API roles (anon, authenticated) access to new tables
-- in the public schema, so without RLS anyone holding the publishable key could
-- read or write these tables through the Supabase Data API, bypassing the
-- backend's ownership checks. No policies are defined on purpose: all access goes
-- through the FastAPI backend, whose database role bypasses RLS.
ALTER TABLE analysis_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
