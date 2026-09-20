"""Library totals: literature 500, primary 100, examples 10. Not a per-drop limit.

Revision ID: 0003_split_library_caps
Revises: 0002_reference_cap_10
"""

from alembic import op

revision = "0003_split_library_caps"
down_revision = "0002_reference_cap_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_reference_file_cap()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          IF NEW.source_role = 'literature' THEN
            IF (
              SELECT count(*) FROM "references"
              WHERE user_id = NEW.user_id AND source_role = 'literature'
                AND file_id IS DISTINCT FROM NEW.file_id
            ) >= 500 THEN
              RAISE EXCEPTION 'Literature cap of 500 files reached'
                USING ERRCODE = 'P0001';
            END IF;
          ELSIF NEW.source_role = 'primary' THEN
            IF (
              SELECT count(*) FROM "references"
              WHERE user_id = NEW.user_id AND source_role = 'primary'
                AND file_id IS DISTINCT FROM NEW.file_id
            ) >= 100 THEN
              RAISE EXCEPTION 'Original research cap of 100 files reached'
                USING ERRCODE = 'P0001';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$
        """
    )
    op.execute("DROP TRIGGER IF EXISTS references_file_cap ON \"references\"")
    op.execute(
        """
        CREATE TRIGGER references_file_cap
          BEFORE INSERT OR UPDATE OF source_role ON "references"
          FOR EACH ROW
          EXECUTE FUNCTION enforce_reference_file_cap()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS references_file_cap ON \"references\"")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_reference_file_cap()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          IF (SELECT count(*) FROM "references" WHERE user_id = NEW.user_id) >= 10 THEN
            RAISE EXCEPTION 'Reference cap of 10 files reached'
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
