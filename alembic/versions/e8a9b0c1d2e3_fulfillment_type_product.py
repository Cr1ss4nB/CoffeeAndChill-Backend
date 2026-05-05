"""fulfillment_type en product: política stock vs receta

Revision ID: e8a9b0c1d2e3
Revises: d1e2f3a4b5c6
Create Date: 2026-04-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "e8a9b0c1d2e3"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("product")}
    if "fulfillment_type" not in columns:
        op.add_column(
            "product",
            sa.Column(
                "fulfillment_type",
                sqlmodel.sql.sqltypes.AutoString(length=20),
                server_default=sa.text("'STOCK'"),
                nullable=False,
            ),
        )
    # Datos: con receta → INGREDIENTS (cupo = insumos; no es el `stock_quantity` el que frena);
    # sin receta → STOCK
    op.execute(
        """
        UPDATE product
        SET fulfillment_type = CASE
            WHEN EXISTS (
                SELECT 1 FROM productconsumption
                WHERE productconsumption.product_id = product.product_id
            ) THEN 'INGREDIENTS'
            ELSE 'STOCK'
        END
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("product")}
    if "fulfillment_type" in columns:
        op.drop_column("product", "fulfillment_type")
