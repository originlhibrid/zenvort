"""002_strip_r2_urls

Revision ID: 002
Revises: 001
Create Date: 2026-04-26 00:00:00

Strip the R2_PUBLIC_URL prefix from existing input_url and output_url
values so they become plain storage keys. New code stores only keys,
not full URLs, and serves presigned URLs at response time.

Run this BEFORE deploying the updated api/storage.py:
    alembic upgrade head

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Strip https://<anything>/ prefix from input_url and output_url columns.
    # Rows that already contain plain storage keys (no "https://") are
    # unaffected because the pattern only matches when the prefix is present.
    op.execute("""
        UPDATE jobs
           SET input_url = regexp_replace(input_url, '^https://[^/]+/', '')
         WHERE input_url LIKE 'https://%'
           AND input_url IS NOT NULL
    """)
    op.execute("""
        UPDATE jobs
           SET output_url = regexp_replace(output_url, '^https://[^/]+/', '')
         WHERE output_url LIKE 'https://%'
           AND output_url IS NOT NULL
    """)


def downgrade() -> None:
    # No rollback — the down_revision 001 migration recreates tables fresh.
    # Existing data would be lost anyway; a rollback here would be misleading.
    pass