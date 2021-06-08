"""update_work_item_table_add_column_source_parent_id

Revision ID: 923f781c8511
Revises: 59e6ca76ad64
Create Date: 2021-06-04 08:47:27.245073

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '923f781c8511'
down_revision = '59e6ca76ad64'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items', sa.Column('parent_source_display_id', sa.String(), nullable=True), schema='work_tracking')


def downgrade():
    op.drop_column('work_items', 'parent_source_display_id', schema='work_tracking')
