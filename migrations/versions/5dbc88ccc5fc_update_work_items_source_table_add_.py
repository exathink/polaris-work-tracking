"""update_work_items_source_table_add_column_source_states

Revision ID: 5dbc88ccc5fc
Revises: d8bc13b17b73
Create Date: 2021-01-19 14:28:47.221916

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5dbc88ccc5fc'
down_revision = 'd8bc13b17b73'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items_sources', sa.Column('source_states', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True), schema='work_tracking')


def downgrade():
    op.drop_column('work_items_sources', 'source_states', schema='work_tracking')
