"""added work_item_type_column to work_items

Revision ID: 9c6bac6fe49a
Revises: d37d16c40f5d
Create Date: 2019-02-16 17:25:07.007966

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c6bac6fe49a'
down_revision = 'd37d16c40f5d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items', sa.Column('work_item_type', sa.String(), nullable=False), schema='work_tracking')


def downgrade():
    op.drop_column('work_items', 'work_item_type', schema='work_tracking')
