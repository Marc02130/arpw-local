"""Lower reference file cap from 500 to 10 (RAGged-scale; 20-file drops failed).

Revision ID: 0002_reference_cap_10
Revises: 0001_initial
"""

from alembic import op

revision = "0002_reference_cap_10"
down_revision = "0001_initial"
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
          IF (SELECT count(*) FROM "references" WHERE user_id = NEW.user_id) >= 10 THEN
            RAISE EXCEPTION 'Reference cap of 10 files reached'
              USING ERRCODE = 'P0001';
          END IF;
          RETURN NEW;
        END;
        $$
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_reference_file_cap()
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
