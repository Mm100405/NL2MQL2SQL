"""merge conversation and view migrations

Revision ID: 3fe7001f9299
Revises: a1b2c3d4e5f6, feea14b28cbe
Create Date: 2026-02-05 17:38:20.051618

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '3fe7001f9299'
down_revision = ('a1b2c3d4e5f6', 'feea14b28cbe')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass