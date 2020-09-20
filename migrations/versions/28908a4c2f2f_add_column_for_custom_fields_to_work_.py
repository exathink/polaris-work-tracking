"""add_column_for_custom_fields_to_work_items_sources_table

Revision ID: 28908a4c2f2f
Revises: 290588ad8e66
Create Date: 2020-09-10 11:27:58.067472

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '28908a4c2f2f'
down_revision = '290588ad8e66'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items_sources',
                  sa.Column('custom_fields', postgresql.JSONB(astext_type=sa.Text()), server_default='[]',
                            nullable=True), schema='work_tracking')


def downgrade():
    op.drop_column('work_items_sources', 'custom_fields', schema='work_tracking')
