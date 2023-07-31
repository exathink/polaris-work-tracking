"""add_releases_and_story_points_columns_to_work_items

Revision ID: dc7185193c09
Revises: 7ac61144a40c
Create Date: 2023-07-26 23:57:05.608409

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dc7185193c09'
down_revision = '7ac61144a40c'
branch_labels = None
depends_on = None


def upgrade():

    op.add_column('work_items', sa.Column('releases', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True), schema='work_tracking')
    op.add_column('work_items', sa.Column('story_points', sa.Integer(), nullable=True), schema='work_tracking')



def downgrade():

    op.drop_column('work_items', 'story_points', schema='work_tracking')
    op.drop_column('work_items', 'releases', schema='work_tracking')

