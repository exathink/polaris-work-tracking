"""add_columns_is_epic_and_epic_key_to_work_items_table

Revision ID: ae22bf73e1ac
Revises: 74abc1071af0
Create Date: 2020-08-21 12:00:56.946585

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ae22bf73e1ac'
down_revision = '74abc1071af0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('work_items', sa.Column('epic_key', postgresql.UUID(as_uuid=True), nullable=True), schema='work_tracking')
    op.add_column('work_items', sa.Column('is_epic', sa.Boolean(), server_default='FALSE', nullable=False), schema='work_tracking')
    op.create_foreign_key('epic_issue_relationship', 'work_items', 'work_items', ['epic_key'], ['key'], source_schema='work_tracking', referent_schema='work_tracking')


def downgrade():
    op.drop_constraint('epic_issue_relationship', 'work_items', schema='work_tracking', type_='foreignkey')
    op.drop_column('work_items', 'is_epic', schema='work_tracking')
    op.drop_column('work_items', 'epic_key', schema='work_tracking')
