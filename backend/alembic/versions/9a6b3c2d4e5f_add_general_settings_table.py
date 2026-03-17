"""add_general_settings_table

Revision ID: 9a6b3c2d4e5f
Revises: 7f6c1e8a4b2d
Create Date: 2026-03-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "9a6b3c2d4e5f"
down_revision: Union[str, Sequence[str], None] = "7f6c1e8a4b2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "generalsetting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sqlmodel.AutoString(length=255), nullable=False),
        sa.Column("env_value", sa.Text(), nullable=True),
        sa.Column("db_value", sa.Text(), nullable=True),
        sa.Column("use_db_value", sa.Boolean(), nullable=False),
        sa.Column("is_runtime_editable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("generalsetting", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_generalsetting_key"), ["key"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("generalsetting", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_generalsetting_key"))

    op.drop_table("generalsetting")
