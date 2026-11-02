-- Preserve optional source fields without using them as ownership identifiers.
-- The default also makes existing rows readable as empty metadata objects.
ALTER TABLE reviews
    ADD COLUMN source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD CONSTRAINT reviews_source_metadata_object
        CHECK (jsonb_typeof(source_metadata) = 'object');
