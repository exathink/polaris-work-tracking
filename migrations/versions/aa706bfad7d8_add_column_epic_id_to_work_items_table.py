"""add_column_epic_id_to_work_items_table

Revision ID: aa706bfad7d8
Revises: 74abc1071af0
Create Date: 2020-08-19 13:34:35.746472

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa706bfad7d8'
down_revision = '74abc1071af0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items', sa.Column('epic_id', sa.String(), nullable=True), schema='work_tracking')


def downgrade():
    op.drop_column('work_items', 'epic_id', schema='work_tracking')
