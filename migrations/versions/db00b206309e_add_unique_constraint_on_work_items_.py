"""add unique constraint on work_items(work_items_source_id, source_id)

Revision ID: db00b206309e
Revises: 4dea4c61aa73
Create Date: 2018-11-16 22:19:24.260731

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'db00b206309e'
down_revision = '4dea4c61aa73'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('ix_work_tracking_work_items_source_id', table_name='work_items', schema='work_tracking')
    op.create_unique_constraint('work_tracking_work_items_work_items_source_id_source_id', 'work_items', ['work_items_source_id', 'source_id'], schema='work_tracking')
    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint('work_tracking_work_items_work_items_source_id_source_id', 'work_items', schema='work_tracking', type_='unique')
    op.create_index('ix_work_tracking_work_items_source_id', 'work_items', ['source_id'], unique=False, schema='work_tracking')

