"""Add label to tablespot

Revision ID: a1b2c3d4e5f6
Revises: b29b2eca06c7
Create Date: 2026-04-17 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b29b2eca06c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tablespot', sa.Column('label', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('tablespot', 'label')
