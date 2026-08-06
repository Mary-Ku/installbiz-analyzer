"""Создает таблицу files.

Revision ID: b03e4e5f9813
Revises:
Create Date: 2026-08-06 22:28:08.400083

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b03e4e5f9813'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Создает таблицу files."""
    op.create_table(
        'files',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )


def downgrade() -> None:
    """Удаляет таблицу files."""
    op.drop_table('files')
