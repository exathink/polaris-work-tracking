"""add_columns_is_epic_and_epic_id_to_work_items_table

Revision ID: 290588ad8e66
Revises: 74abc1071af0
Create Date: 2020-08-24 12:24:10.572259

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '290588ad8e66'
down_revision = '74abc1071af0'
branch_labels = None
depends_on = None


def update_is_epic():
    op.execute(f"""
                update work_tracking.work_items set is_epic=TRUE where work_item_type='epic'   
    """)


def upgrade():
    op.add_column('work_items', sa.Column('epic_id', sa.Integer(), nullable=True), schema='work_tracking')
    op.add_column('work_items', sa.Column('is_epic', sa.Boolean(), server_default='FALSE', nullable=False),
                  schema='work_tracking')
    op.create_foreign_key('work_items_epic_id_fk', 'work_items', 'work_items', ['epic_id'], ['id'],
                          source_schema='work_tracking', referent_schema='work_tracking')
    update_is_epic()


def downgrade():
    op.drop_constraint('work_items_epic_id_fk', 'work_items', schema='work_tracking', type_='foreignkey')
    op.drop_column('work_items', 'is_epic', schema='work_tracking')
    op.drop_column('work_items', 'epic_id', schema='work_tracking')
