"""paper-centric schema: users, files, vectors, papers, pins, notes

Revision ID: 0001_initial
Revises:
"""

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

MINILM = "sentence-transformers/all-MiniLM-L6-v2"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE users (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          email TEXT NOT NULL UNIQUE CHECK (email = lower(email)),
          password_hash TEXT NOT NULL,
          full_name TEXT,
          email_confirmed_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE user_llm_settings (
          user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          openai_key_enc TEXT,
          xai_key_enc TEXT,
          anthropic_key_enc TEXT,
          openai_last4 TEXT,
          xai_last4 TEXT,
          anthropic_last4 TEXT,
          chat_provider TEXT NOT NULL DEFAULT 'xai'
            CHECK (chat_provider IN ('openai', 'xai', 'anthropic')),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE email_tokens (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          purpose TEXT NOT NULL CHECK (purpose IN ('confirm', 'reset')),
          token_hash TEXT NOT NULL UNIQUE,
          expires_at TIMESTAMPTZ NOT NULL,
          used_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_email_tokens_user_id ON email_tokens(user_id)")
    op.execute(
        """
        CREATE TABLE "references" (
          file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          document_type TEXT NOT NULL DEFAULT 'reference'
            CHECK (document_type = 'reference'),
          file_name TEXT NOT NULL CHECK (file_name ~* '\\.(pdf|docx|txt)$'),
          file_size INTEGER NOT NULL CHECK (file_size > 0 AND file_size <= 10485760),
          file_path TEXT NOT NULL,
          file_type TEXT NOT NULL,
          source_role TEXT NOT NULL DEFAULT 'literature'
            CHECK (source_role IN ('literature', 'primary')),
          status TEXT NOT NULL DEFAULT 'processing'
            CHECK (status IN ('processing', 'ready', 'failed')),
          embedding_model TEXT,
          chunk_count INTEGER NOT NULL DEFAULT 0,
          error_message TEXT,
          citation_text TEXT,
          bibliographic JSONB,
          uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (file_id, user_id)
        )
        """
    )
    op.execute('CREATE INDEX idx_references_user_id ON "references"(user_id)')
    op.execute(
        """
        CREATE TABLE examples (
          file_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          document_type TEXT NOT NULL DEFAULT 'example'
            CHECK (document_type = 'example'),
          file_name TEXT NOT NULL CHECK (file_name ~* '\\.(pdf|docx|txt)$'),
          file_size INTEGER NOT NULL CHECK (file_size > 0 AND file_size <= 10485760),
          file_path TEXT NOT NULL,
          file_type TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'processing'
            CHECK (status IN ('processing', 'ready', 'failed')),
          embedding_model TEXT,
          chunk_count INTEGER NOT NULL DEFAULT 0,
          error_message TEXT,
          uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (file_id, user_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_examples_user_id ON examples(user_id)")
    op.execute(
        f"""
        CREATE TABLE reference_vectors (
          vector_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          file_id UUID NOT NULL REFERENCES "references"(file_id) ON DELETE CASCADE,
          vector vector(384) NOT NULL,
          chunk_text TEXT NOT NULL,
          chunk_index INTEGER NOT NULL,
          section TEXT,
          page INTEGER,
          embedding_model TEXT NOT NULL,
          chunk_role TEXT CHECK (
            chunk_role IS NULL OR chunk_role IN (
              'claim','finding','evaluation','method','context',
              'experience','citation','boilerplate'
            )
          ),
          chunk_tsv tsvector GENERATED ALWAYS AS
            (to_tsvector('english', chunk_text)) STORED,
          UNIQUE (vector_id, file_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_reference_vectors_file_id ON reference_vectors(file_id)")
    op.execute(
        "CREATE INDEX idx_reference_vectors_chunk_tsv ON reference_vectors USING gin (chunk_tsv)"
    )
    op.execute(
        """
        CREATE TABLE example_vectors (
          vector_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          file_id UUID NOT NULL REFERENCES examples(file_id) ON DELETE CASCADE,
          vector vector(384) NOT NULL,
          chunk_text TEXT NOT NULL,
          chunk_index INTEGER NOT NULL,
          section TEXT,
          page INTEGER,
          embedding_model TEXT NOT NULL,
          chunk_role TEXT CHECK (
            chunk_role IS NULL OR chunk_role IN (
              'claim','finding','evaluation','method','context',
              'experience','citation','boilerplate'
            )
          ),
          chunk_tsv tsvector GENERATED ALWAYS AS
            (to_tsvector('english', chunk_text)) STORED,
          UNIQUE (vector_id, file_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_example_vectors_file_id ON example_vectors(file_id)")
    op.execute(
        "CREATE INDEX idx_example_vectors_chunk_tsv ON example_vectors USING gin (chunk_tsv)"
    )
    op.execute(
        """
        CREATE TABLE user_papers (
          paper_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL,
          content TEXT NOT NULL DEFAULT '',
          sections TEXT[],
          paper_type TEXT NOT NULL CHECK (
            paper_type IN (
              'Empirical Study',
              'Literature Review',
              'Theoretical Paper',
              'Case Study'
            )
          ),
          citation_style TEXT NOT NULL DEFAULT 'APA'
            CHECK (citation_style IN ('APA', 'MLA', 'Chicago')),
          output_format TEXT NOT NULL DEFAULT 'markdown'
            CHECK (output_format IN ('markdown', 'word')),
          version INTEGER NOT NULL DEFAULT 1,
          status TEXT NOT NULL DEFAULT 'draft'
            CHECK (status IN ('draft', 'completed')),
          research_prompt TEXT NOT NULL DEFAULT '',
          outline TEXT NOT NULL DEFAULT '',
          attribution JSONB NOT NULL DEFAULT '[]'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (paper_id, user_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_user_papers_user_id ON user_papers(user_id)")
    op.execute(
        "CREATE INDEX idx_user_papers_user_title_version ON user_papers(user_id, title, version)"
    )
    op.execute(
        """
        CREATE TABLE paper_references (
          paper_id UUID NOT NULL REFERENCES user_papers(paper_id) ON DELETE CASCADE,
          file_id UUID NOT NULL REFERENCES "references"(file_id) ON DELETE CASCADE,
          PRIMARY KEY (paper_id, file_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE pinned_passages (
          pin_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          paper_id UUID NOT NULL,
          file_id UUID NOT NULL,
          vector_id UUID NOT NULL,
          target_section TEXT CHECK (
            target_section IS NULL OR target_section IN (
              'Abstract', 'Introduction', 'Literature Review', 'Methods',
              'Results', 'Discussion', 'Conclusion', 'References'
            )
          ),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          UNIQUE (paper_id, vector_id),
          FOREIGN KEY (paper_id, user_id)
            REFERENCES user_papers (paper_id, user_id) ON DELETE CASCADE,
          FOREIGN KEY (file_id, user_id)
            REFERENCES "references" (file_id, user_id) ON DELETE CASCADE,
          FOREIGN KEY (vector_id, file_id)
            REFERENCES reference_vectors (vector_id, file_id) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX idx_pinned_passages_user_id ON pinned_passages(user_id)")
    op.execute("CREATE INDEX idx_pinned_passages_paper_id ON pinned_passages(paper_id)")
    op.execute(
        """
        CREATE TABLE interrogation_turns (
          turn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          paper_id UUID NOT NULL,
          role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
          content TEXT NOT NULL CHECK (
            char_length(content) > 0 AND char_length(content) <= 20000
          ),
          sources TEXT[] NOT NULL DEFAULT ARRAY['literature']::text[]
            CHECK (
              sources <@ ARRAY['literature', 'primary', 'examples']::text[]
              AND cardinality(sources) >= 1
            ),
          filter_role TEXT CHECK (
            filter_role IS NULL
            OR filter_role IN ('literature', 'primary', 'both')
          ),
          passages JSONB NOT NULL DEFAULT '[]'::jsonb,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          FOREIGN KEY (paper_id, user_id)
            REFERENCES user_papers (paper_id, user_id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_interrogation_turns_paper_created "
        "ON interrogation_turns(paper_id, created_at)"
    )
    op.execute("CREATE INDEX idx_interrogation_turns_user_id ON interrogation_turns(user_id)")
    op.execute(
        """
        CREATE FUNCTION enforce_reference_file_cap()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          IF (SELECT count(*) FROM "references" WHERE user_id = NEW.user_id) >= 500 THEN
            RAISE EXCEPTION 'Reference cap of 500 files reached'
              USING ERRCODE = 'P0001';
          END IF;
          RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER references_file_cap
          BEFORE INSERT ON "references"
          FOR EACH ROW
          EXECUTE FUNCTION enforce_reference_file_cap()
        """
    )
    op.execute(
        """
        CREATE FUNCTION enforce_example_file_cap()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          IF (SELECT count(*) FROM examples WHERE user_id = NEW.user_id) >= 10 THEN
            RAISE EXCEPTION 'Example cap of 10 files reached'
              USING ERRCODE = 'P0001';
          END IF;
          RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER examples_file_cap
          BEFORE INSERT ON examples
          FOR EACH ROW
          EXECUTE FUNCTION enforce_example_file_cap()
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION match_reference_chunks(
          query_embedding vector(384),
          match_count integer,
          filter_user uuid,
          filter_role text DEFAULT NULL,
          prefer_section text DEFAULT NULL,
          filter_model text DEFAULT '{MINILM}',
          query_text text DEFAULT NULL
        )
        RETURNS TABLE (
          vector_id uuid,
          file_id uuid,
          chunk_text text,
          section text,
          source_role text,
          score double precision,
          page integer,
          chunk_role text
        )
        LANGUAGE sql
        STABLE
        AS $$
          WITH params AS (
            SELECT
              LEAST(GREATEST(COALESCE(match_count, 12), 1), 20) AS k,
              LEAST(GREATEST(COALESCE(match_count, 12), 1) * 2, 40) AS pool,
              nullif(btrim(query_text), '') AS qtext,
              coalesce(nullif(btrim(filter_model), ''), '{MINILM}') AS model
          ),
          filtered AS (
            SELECT
              v.vector_id,
              v.file_id,
              v.chunk_text,
              v.section,
              v.page,
              v.chunk_role,
              v.chunk_tsv,
              r.source_role,
              (v.vector <=> query_embedding) AS dist
            FROM reference_vectors v
            JOIN "references" r ON r.file_id = v.file_id
            WHERE r.user_id = filter_user
              AND v.embedding_model = (SELECT model FROM params)
              AND (
                filter_role IS NULL
                OR filter_role = 'both'
                OR r.source_role = filter_role
              )
          ),
          vec AS (
            SELECT vector_id, rnk FROM (
              SELECT vector_id, ROW_NUMBER() OVER (ORDER BY dist) AS rnk
              FROM filtered
            ) ranked
            WHERE rnk <= (SELECT pool FROM params)
          ),
          fts AS (
            SELECT vector_id, rnk FROM (
              SELECT
                vector_id,
                ROW_NUMBER() OVER (
                  ORDER BY ts_rank_cd(
                    chunk_tsv, plainto_tsquery('english', (SELECT qtext FROM params))
                  ) DESC
                ) AS rnk
              FROM filtered
              WHERE (SELECT qtext FROM params) IS NOT NULL
                AND chunk_tsv @@ plainto_tsquery('english', (SELECT qtext FROM params))
            ) ranked
            WHERE rnk <= (SELECT pool FROM params)
          ),
          fused AS (
            SELECT
              f.vector_id,
              f.file_id,
              f.chunk_text,
              f.section,
              f.source_role,
              f.page,
              f.chunk_role,
              (1 - f.dist)::double precision AS cosine_score,
              COALESCE(
                (SELECT 1.0 / (60 + vec.rnk) FROM vec WHERE vec.vector_id = f.vector_id), 0
              )
                + COALESCE(
                  (SELECT 1.0 / (60 + fts.rnk) FROM fts WHERE fts.vector_id = f.vector_id), 0
                ) AS rrf
            FROM filtered f
            WHERE f.vector_id IN (SELECT vector_id FROM vec UNION SELECT vector_id FROM fts)
          )
          SELECT
            fused.vector_id,
            fused.file_id,
            fused.chunk_text,
            fused.section,
            fused.source_role,
            fused.cosine_score AS score,
            fused.page,
            fused.chunk_role
          FROM fused
          ORDER BY
            CASE
              WHEN prefer_section IS NULL OR btrim(prefer_section) = '' THEN 0
              WHEN lower(coalesce(fused.section, '')) = lower(btrim(prefer_section)) THEN 0
              ELSE 1
            END,
            fused.rrf DESC,
            fused.cosine_score DESC
          LIMIT (SELECT k FROM params);
        $$
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION match_example_chunks(
          query_embedding vector(384),
          match_count integer,
          filter_user uuid,
          prefer_section text DEFAULT NULL,
          filter_model text DEFAULT '{MINILM}',
          query_text text DEFAULT NULL
        )
        RETURNS TABLE (
          vector_id uuid,
          file_id uuid,
          chunk_text text,
          section text,
          score double precision,
          page integer
        )
        LANGUAGE sql
        STABLE
        AS $$
          WITH params AS (
            SELECT
              LEAST(GREATEST(COALESCE(match_count, 6), 1), 10) AS k,
              LEAST(GREATEST(COALESCE(match_count, 6), 1) * 2, 20) AS pool,
              nullif(btrim(query_text), '') AS qtext,
              coalesce(nullif(btrim(filter_model), ''), '{MINILM}') AS model
          ),
          filtered AS (
            SELECT
              v.vector_id,
              v.file_id,
              v.chunk_text,
              v.section,
              v.page,
              v.chunk_tsv,
              (v.vector <=> query_embedding) AS dist
            FROM example_vectors v
            JOIN examples e ON e.file_id = v.file_id
            WHERE e.user_id = filter_user
              AND v.embedding_model = (SELECT model FROM params)
          ),
          vec AS (
            SELECT vector_id, rnk FROM (
              SELECT vector_id, ROW_NUMBER() OVER (ORDER BY dist) AS rnk
              FROM filtered
            ) ranked
            WHERE rnk <= (SELECT pool FROM params)
          ),
          fts AS (
            SELECT vector_id, rnk FROM (
              SELECT
                vector_id,
                ROW_NUMBER() OVER (
                  ORDER BY ts_rank_cd(
                    chunk_tsv, plainto_tsquery('english', (SELECT qtext FROM params))
                  ) DESC
                ) AS rnk
              FROM filtered
              WHERE (SELECT qtext FROM params) IS NOT NULL
                AND chunk_tsv @@ plainto_tsquery('english', (SELECT qtext FROM params))
            ) ranked
            WHERE rnk <= (SELECT pool FROM params)
          ),
          fused AS (
            SELECT
              f.vector_id,
              f.file_id,
              f.chunk_text,
              f.section,
              f.page,
              (1 - f.dist)::double precision AS cosine_score,
              COALESCE(
                (SELECT 1.0 / (60 + vec.rnk) FROM vec WHERE vec.vector_id = f.vector_id), 0
              )
                + COALESCE(
                  (SELECT 1.0 / (60 + fts.rnk) FROM fts WHERE fts.vector_id = f.vector_id), 0
                ) AS rrf
            FROM filtered f
            WHERE f.vector_id IN (SELECT vector_id FROM vec UNION SELECT vector_id FROM fts)
          )
          SELECT
            fused.vector_id,
            fused.file_id,
            fused.chunk_text,
            fused.section,
            fused.cosine_score AS score,
            fused.page
          FROM fused
          ORDER BY
            CASE
              WHEN prefer_section IS NULL OR btrim(prefer_section) = '' THEN 0
              WHEN lower(coalesce(fused.section, '')) = lower(btrim(prefer_section)) THEN 0
              ELSE 1
            END,
            fused.rrf DESC,
            fused.cosine_score DESC
          LIMIT (SELECT k FROM params);
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS match_example_chunks")
    op.execute("DROP FUNCTION IF EXISTS match_reference_chunks")
    op.execute("DROP TRIGGER IF EXISTS examples_file_cap ON examples")
    op.execute("DROP TRIGGER IF EXISTS references_file_cap ON \"references\"")
    op.execute("DROP FUNCTION IF EXISTS enforce_example_file_cap")
    op.execute("DROP FUNCTION IF EXISTS enforce_reference_file_cap")
    op.execute("DROP TABLE IF EXISTS interrogation_turns")
    op.execute("DROP TABLE IF EXISTS pinned_passages")
    op.execute("DROP TABLE IF EXISTS paper_references")
    op.execute("DROP TABLE IF EXISTS user_papers")
    op.execute("DROP TABLE IF EXISTS example_vectors")
    op.execute("DROP TABLE IF EXISTS reference_vectors")
    op.execute("DROP TABLE IF EXISTS examples")
    op.execute('DROP TABLE IF EXISTS "references"')
    op.execute("DROP TABLE IF EXISTS email_tokens")
    op.execute("DROP TABLE IF EXISTS user_llm_settings")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP EXTENSION IF EXISTS vector")
