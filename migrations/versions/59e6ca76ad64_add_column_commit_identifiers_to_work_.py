"""add_column_commit_identifiers_to_work_items

Revision ID: 59e6ca76ad64
Revises: 5dbc88ccc5fc
Create Date: 2021-04-20 11:15:48.442193

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '59e6ca76ad64'
down_revision = '5dbc88ccc5fc'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items', sa.Column('commit_identifiers', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True), schema='work_tracking')


def downgrade():
    op.drop_column('work_items', 'commit_identifiers', schema='work_tracking')
