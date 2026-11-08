DO $$
DECLARE
    state_attnum SMALLINT;
    state_constraints TEXT[];
    state_constraint_definition TEXT;
    expected_constraint_definition TEXT;
    expected_table_name TEXT;
    expected_table_oid OID;
BEGIN
    SELECT attnum
    INTO state_attnum
    FROM pg_attribute
    WHERE attrelid = 'public.ingestion_runs'::regclass
      AND attname = 'state'
      AND NOT attisdropped;

    SELECT array_agg(conname::TEXT)
    INTO state_constraints
    FROM pg_constraint
    WHERE conrelid = 'public.ingestion_runs'::regclass
      AND contype = 'c'
      AND state_attnum = ANY (conkey);

    IF state_attnum IS NULL OR COALESCE(array_length(state_constraints, 1), 0) <> 1 THEN
        RAISE EXCEPTION
            'Expected exactly one CHECK constraint on ingestion_runs.state';
    END IF;

    SELECT pg_get_expr(conbin, conrelid)
    INTO state_constraint_definition
    FROM pg_constraint
    WHERE conrelid = 'public.ingestion_runs'::regclass
      AND conname = state_constraints[1];

    expected_table_name := '_expected_ingestion_state_'
        || pg_backend_pid()::TEXT || '_' || txid_current()::TEXT;
    EXECUTE
        'CREATE TEMPORARY TABLE ' || quote_ident(expected_table_name) || ' (
            state VARCHAR(16) NOT NULL
                CHECK (state IN (''processing'', ''succeeded'', ''failed''))
        ) ON COMMIT DROP';

    SELECT oid
    INTO expected_table_oid
    FROM pg_class
    WHERE relnamespace = pg_my_temp_schema()
      AND relname = expected_table_name;

    SELECT pg_get_expr(conbin, conrelid)
    INTO expected_constraint_definition
    FROM pg_constraint
    WHERE conrelid = expected_table_oid
      AND contype = 'c';

    IF state_constraint_definition IS DISTINCT FROM expected_constraint_definition THEN
        RAISE EXCEPTION
            'ingestion_runs.state CHECK does not match the expected original restriction';
    END IF;

    EXECUTE 'ALTER TABLE public.ingestion_runs DROP CONSTRAINT '
        || quote_ident(state_constraints[1]);

    EXECUTE
        'ALTER TABLE public.ingestion_runs
            ADD COLUMN rejected_count INTEGER NOT NULL DEFAULT 0
            CONSTRAINT ingestion_runs_rejected_count_check
                CHECK (rejected_count >= 0)';

    EXECUTE 'DROP TABLE pg_temp.' || quote_ident(expected_table_name);

    ALTER TABLE public.ingestion_runs
        ADD CONSTRAINT ingestion_runs_state_check
        CHECK (state IN ('processing', 'succeeded', 'partial', 'failed'));
END
$$;
