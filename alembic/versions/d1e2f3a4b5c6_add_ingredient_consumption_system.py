"""Add ingredient and product consumption system

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-04-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ingredient',
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('unit', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('min_stock', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('ingredient_id'),
    )

    op.create_table(
        'ingredientstockmovement',
        sa.Column('movement_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('system_user_id', sa.Integer(), nullable=False),
        sa.Column('movement_type', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('related_order_id', sa.Integer(), nullable=True),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('movement_date', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.ingredient_id']),
        sa.ForeignKeyConstraint(['related_order_id'], ['order.order_id']),
        sa.ForeignKeyConstraint(['system_user_id'], ['systemuser.system_user_id']),
        sa.PrimaryKeyConstraint('movement_id'),
    )

    op.create_table(
        'productconsumption',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('quantity_used', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredient.ingredient_id']),
        sa.ForeignKeyConstraint(['product_id'], ['product.product_id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add notes column to inventorymovement if not present (was missing from schema)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    inv_cols = {col['name'] for col in inspector.get_columns('inventorymovement')}
    if 'notes' not in inv_cols:
        op.add_column(
            'inventorymovement',
            sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('productconsumption')
    op.drop_table('ingredientstockmovement')
    op.drop_table('ingredient')

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    inv_cols = {col['name'] for col in inspector.get_columns('inventorymovement')}
    if 'notes' in inv_cols:
        op.drop_column('inventorymovement', 'notes')
