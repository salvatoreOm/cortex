"""add api key hash to users

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-21 13:41:54.635732

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable + unique: existing rows (like the Phase 1 seeded dev user) get
    # NULL, which Postgres allows any number of under a unique constraint -
    # they just can never authenticate, which is fine, that account is retired.
    op.add_column("users", sa.Column("api_key_hash", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_api_key_hash", "users", ["api_key_hash"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_users_api_key_hash", "users", type_="unique")
    op.drop_column("users", "api_key_hash")
