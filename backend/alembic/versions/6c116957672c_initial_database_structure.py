"""Initial database structure

Revision ID: 6c116957672c
Revises:
Create Date: 2026-02-04 16:51:56.144152

"""
from alembic import op

from app.database import Base
from app.models import *  # noqa: F401,F403


revision = '6c116957672c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
