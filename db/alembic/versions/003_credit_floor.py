"""003_credit_floor_and_double_deduction_protection

Revision ID: 003
Revises: 002
Create Date: 2026-04-27 00:00:00

Enforces:
1. Credit floor — credits cannot go negative at DB level
2. Anti-double-deduction — unique partial index on credit_logs(job_id)
   where reason='conversion' prevents the same job from being charged twice
3. Wipes plaintext api_key values (now stored as hash only)

Run this after deploying the security audit fixes:
    alembic upgrade head

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Credit floor constraint
    op.execute("""
        ALTER TABLE users
        ADD CONSTRAINT credits_non_negative
        CHECK (credits >= 0)
    """)

    # 2. Prevent double credit deduction for same conversion job
    op.execute("""
        CREATE UNIQUE INDEX credit_logs_job_conversion_unique
        ON credit_logs (job_id)
        WHERE reason = 'conversion' AND job_id IS NOT NULL
    """)

    # 3. Wipe plaintext api_key values — store hash in both columns
    # Existing users: their plaintext key is replaced with the hash.
    # On next login they'll receive the hash as their apiKey (not ideal but safe).
    op.execute("""
        UPDATE users
           SET api_key = api_key_hash
         WHERE api_key != api_key_hash
           AND api_key_hash IS NOT NULL
    """)


def downgrade() -> None:
    # Remove constraints and index
    op.execute("ALTER TABLE users DROP CONSTRAINT credits_non_negative")
    op.execute("DROP INDEX IF EXISTS credit_logs_job_conversion_unique")

    # Downgrade does NOT restore plaintext keys — they are gone
    pass