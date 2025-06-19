"""Add trade result and daily pnl tables

Revision ID: e0a67c18c6d4
Revises: df9491b6f34f
Create Date: 2025-06-19 02:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e0a67c18c6d4'
down_revision = 'df9491b6f34f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'trade_result',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('strategy_id', sa.Integer(), sa.ForeignKey('strategy.id')),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(length=50), nullable=True),
    )
    op.create_table(
        'daily_pnl',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('day', sa.Date(), nullable=False, unique=True),
        sa.Column('pnl', sa.Float(), nullable=False),
    )


def downgrade():
    op.drop_table('daily_pnl')
    op.drop_table('trade_result')
