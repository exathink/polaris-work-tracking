"""drop_work_items_source_source_record_column

Revision ID: 78d3b6744769
Revises: 8caff16606a3
Create Date: 2019-06-20 19:36:09.003582

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '78d3b6744769'
down_revision = '8caff16606a3'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('work_items_sources', 'source_record', schema='work_tracking')
    # ### end Alembic commands ###


def downgrade():
    op.add_column('work_items_sources', sa.Column('source_record', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=True), schema='work_tracking')
    # ### end Alembic commands ###
