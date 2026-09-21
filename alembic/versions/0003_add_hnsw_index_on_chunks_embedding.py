"""add hnsw index on chunks embedding

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-21 12:33:28.725705

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # HNSW = an approximate-nearest-neighbor index, the pgvector equivalent of a
    # btree index but for "find rows near this vector" instead of "find rows equal
    # to this value". cosine distance ops match the cosine_distance() comparator
    # used in chunk_repo.search_similar_chunks.
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")
