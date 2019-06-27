"""make_account_key_nullable_on_work_items_source

Revision ID: 74abc1071af0
Revises: 6bd4d4838e11
Create Date: 2019-06-27 21:57:37.457914

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '74abc1071af0'
down_revision = '6bd4d4838e11'
branch_labels = None
depends_on = None


def upgrade():

    op.alter_column('work_items_sources', 'account_key',
               existing_type=postgresql.UUID(),
               nullable=True,
               schema='work_tracking')
    # ### end Alembic commands ###


def downgrade():
    op.alter_column('work_items_sources', 'account_key',
               existing_type=postgresql.UUID(),
               nullable=False,
               schema='work_tracking')
    # ### end Alembic commands ###
