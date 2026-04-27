"""Fix api_key: store raw key in api_key, hash in api_key_hash.

Revision ID: 004_fix_api_key_raw
Revises: 003_credit_floor
"""

from alembic import op
import sqlalchemy as sa
import hashlib
import secrets


revision = "004_fix_api_key_raw"
down_revision = "003"
branch_labels = None
depends_on = None


def generate_keys():
    raw = secrets.token_urlsafe(32)
    h = hashlib.sha256(raw.encode()).hexdigest()
    return raw, h


def upgrade():
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM users"))
    for (user_id,) in result:
        raw_key, key_hash = generate_keys()
        connection.execute(
            sa.text(
                "UPDATE users SET api_key = :raw, api_key_hash = :hash WHERE id = :id"
            ),
            {"raw": raw_key, "hash": key_hash, "id": user_id},
        )


def downgrade():
    pass
