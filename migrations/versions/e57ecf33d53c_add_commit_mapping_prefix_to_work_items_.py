"""add_commit_mapping_prefix_to_work_items_sources

Revision ID: e57ecf33d53c
Revises: 6b8c3db33ed8
Create Date: 2022-03-12 16:17:04.914340

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e57ecf33d53c'
down_revision = '6b8c3db33ed8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items_sources', sa.Column('commit_mapping_prefix', sa.String(), nullable=True), schema='work_tracking')



def downgrade():
    op.drop_column('work_items_sources', 'commit_mapping_prefix', schema='work_tracking')

