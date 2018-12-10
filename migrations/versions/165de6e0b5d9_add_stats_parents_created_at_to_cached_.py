""" add stats, parents, created_at to cached_commits

Revision ID: 165de6e0b5d9
Revises: a9326c356c7f
Create Date: 2018-12-10 18:33:28.630351

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '165de6e0b5d9'
down_revision = 'a9326c356c7f'
branch_labels = None
depends_on = None


def upgrade():

    op.add_column('cached_commits', sa.Column('created_at', sa.DateTime(), nullable=False), schema='work_tracking')
    op.add_column('cached_commits', sa.Column('parents', postgresql.ARRAY(sa.String()), nullable=False), schema='work_tracking')
    op.add_column('cached_commits', sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False), schema='work_tracking')



def downgrade():

    op.drop_column('cached_commits', 'stats', schema='work_tracking')
    op.drop_column('cached_commits', 'parents', schema='work_tracking')
    op.drop_column('cached_commits', 'created_at', schema='work_tracking')

