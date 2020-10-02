"""update_work_items_add_column_api_payload

Revision ID: ea4711c8497a
Revises: 28908a4c2f2f
Create Date: 2020-09-30 10:40:26.616384

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ea4711c8497a'
down_revision = '86da8e15b2e1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items',
                  sa.Column('api_payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
                  schema='work_tracking')


def downgrade():
    op.drop_column('work_items', 'api_payload', schema='work_tracking')
