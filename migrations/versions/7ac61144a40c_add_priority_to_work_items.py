"""add_priority_to_work_items

Revision ID: 7ac61144a40c
Revises: e57ecf33d53c
Create Date: 2023-07-18 16:41:08.929575

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ac61144a40c'
down_revision = 'e57ecf33d53c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items', sa.Column('priority', sa.String(), nullable=True), schema='work_tracking')



def downgrade():
    op.drop_column('work_items', 'priority', schema='work_tracking')
