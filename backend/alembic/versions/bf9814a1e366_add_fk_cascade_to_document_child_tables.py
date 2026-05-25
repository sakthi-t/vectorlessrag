"""add_fk_cascade_to_document_child_tables

Revision ID: bf9814a1e366
Revises: 1f893d234cd9
Create Date: 2026-05-24 18:12:44.739505

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'bf9814a1e366'
down_revision: Union[str, Sequence[str], None] = '1f893d234cd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_chunks_document_id",
        "chunks", "documents",
        ["document_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_document_trees_document_id",
        "document_trees", "documents",
        ["document_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_bm25_stats_document_id",
        "bm25_stats", "documents",
        ["document_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_chunks_document_id", "chunks", type_="foreignkey")
    op.drop_constraint("fk_document_trees_document_id", "document_trees", type_="foreignkey")
    op.drop_constraint("fk_bm25_stats_document_id", "bm25_stats", type_="foreignkey")
