"""Add WorkItem

Revision ID: 5a9093690ffb
Revises: 
Create Date: 2018-11-12 19:03:54.841592

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5a9093690ffb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table('work_items',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_bug', sa.Boolean(), server_default='FALSE', nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key'),
    schema='work_tracking'
    )



def downgrade():
    op.drop_table('work_items', schema='work_tracking')

