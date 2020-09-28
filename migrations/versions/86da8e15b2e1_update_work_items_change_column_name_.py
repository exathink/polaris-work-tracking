"""update_work_items_change_column_name_epic_id_to_parent_id

Revision ID: 86da8e15b2e1
Revises: 28908a4c2f2f
Create Date: 2020-09-24 13:43:36.025597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86da8e15b2e1'
down_revision = '28908a4c2f2f'
branch_labels = None
depends_on = None


def copy_from_epic_id_to_parent_id():
    op.execute(f"""
                update work_tracking.work_items set parent_id=epic_id where epic_id is not NULL 
            """)


def copy_from_parent_id_to_epic_id():
    op.execute("""
                update work_tracking.work_items set epic_id=parent_id where parent_id is not NULL
            """)


def upgrade():
    op.add_column('work_items', sa.Column('parent_id', sa.Integer(), nullable=True), schema='work_tracking')
    copy_from_epic_id_to_parent_id()
    op.drop_constraint('work_items_epic_id_fk', 'work_items', schema='work_tracking', type_='foreignkey')
    op.create_foreign_key('work_items_parent_id_fk', 'work_items', 'work_items', ['parent_id'], ['id'], source_schema='work_tracking', referent_schema='work_tracking')
    op.drop_column('work_items', 'epic_id', schema='work_tracking')


def downgrade():
    op.add_column('work_items', sa.Column('epic_id', sa.INTEGER(), autoincrement=False, nullable=True), schema='work_tracking')
    copy_from_parent_id_to_epic_id()
    op.drop_constraint('work_items_parent_id_fk', 'work_items', schema='work_tracking', type_='foreignkey')
    op.create_foreign_key('work_items_epic_id_fk', 'work_items', 'work_items', ['epic_id'], ['id'], source_schema='work_tracking', referent_schema='work_tracking')
    op.drop_column('work_items', 'parent_id', schema='work_tracking')
