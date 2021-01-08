"""update_work_items_source_add_column_source_data_for_webhooks

Revision ID: d8bc13b17b73
Revises: ea4711c8497a
Create Date: 2021-01-08 09:28:59.725460

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd8bc13b17b73'
down_revision = 'ea4711c8497a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items_sources', sa.Column('source_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False), schema='work_tracking')


def downgrade():
    op.drop_column('work_items_sources', 'source_data', schema='work_tracking')
