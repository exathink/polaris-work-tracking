"""Add deleted_at field to work_items

Revision ID: 35f4aebc67ce
Revises: 9c6bac6fe49a
Create Date: 2019-05-03 21:22:30.111385

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35f4aebc67ce'
down_revision = '9c6bac6fe49a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items', sa.Column('deleted_at', sa.DateTime(), nullable=True), schema='work_tracking')



def downgrade():
    op.drop_column('work_items', 'deleted_at', schema='work_tracking')

