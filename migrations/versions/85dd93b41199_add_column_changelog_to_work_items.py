"""add_column_changelog_to_work_items

Revision ID: 85dd93b41199
Revises: c995ddf29ad6
Create Date: 2023-11-09 01:53:10.044422

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '85dd93b41199'
down_revision = 'c995ddf29ad6'
branch_labels = None
depends_on = None


def upgrade():

    op.add_column('work_items', sa.Column('changelog', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True), schema='work_tracking')



def downgrade():

    op.drop_column('work_items', 'changelog', schema='work_tracking')

