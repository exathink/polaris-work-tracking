"""added_flag_is_moved_to_work_items_table

Revision ID: 6b8c3db33ed8
Revises: 923f781c8511
Create Date: 2021-06-22 10:51:55.253934

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6b8c3db33ed8'
down_revision = '923f781c8511'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items',
                  sa.Column('is_moved_from_current_source', sa.Boolean(), server_default='FALSE', nullable=True),
                  schema='work_tracking')


def downgrade():
    op.drop_column('work_items', 'is_moved_from_current_source', schema='work_tracking')
