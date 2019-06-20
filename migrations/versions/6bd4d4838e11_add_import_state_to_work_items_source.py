"""add_import_state_to_work_items_source

Revision ID: 6bd4d4838e11
Revises: 78d3b6744769
Create Date: 2019-06-20 21:35:36.433711

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6bd4d4838e11'
down_revision = '78d3b6744769'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items_sources', sa.Column('import_state', sa.String(), server_default='disabled', nullable=False), schema='work_tracking')
    # ### end Alembic commands ###


def downgrade():
    op.drop_column('work_items_sources', 'import_state', schema='work_tracking')
    # ### end Alembic commands ###
