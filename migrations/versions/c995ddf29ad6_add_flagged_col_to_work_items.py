"""add_flagged_col_to_work_items

Revision ID: c995ddf29ad6
Revises: 45713333a0fe
Create Date: 2023-10-27 14:39:32.071687

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c995ddf29ad6'
down_revision = '45713333a0fe'
branch_labels = None
depends_on = None


def upgrade():

    op.add_column('work_items', sa.Column('flagged', sa.Boolean(), server_default='FALSE', nullable=True), schema='work_tracking')



def downgrade():

    op.drop_column('work_items', 'flagged', schema='work_tracking')

