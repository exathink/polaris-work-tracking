"""add cached_commits and work_items_commits tables

Revision ID: ab068ed4540f
Revises: ef7cfbdea63e
Create Date: 2018-11-28 19:50:05.899315

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ab068ed4540f'
down_revision = 'ef7cfbdea63e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cached_commits',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('commit_key', sa.String(), nullable=False),
    sa.Column('repository_name', sa.String(), nullable=False),
    sa.Column('commit_date', sa.DateTime(), nullable=False),
    sa.Column('commit_date_tz_offset', sa.Integer(), nullable=False),
    sa.Column('committer_contributor_name', sa.String(), nullable=False),
    sa.Column('committer_contributor_key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('author_date', sa.DateTime(), nullable=False),
    sa.Column('author_date_tz_offset', sa.Integer(), nullable=False),
    sa.Column('author_contributor_key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('author_contributor_name', sa.String(), nullable=False),
    sa.Column('commit_message', sa.Text(), nullable=False),
    sa.Column('created_on_branch', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('repository_name', 'commit_key'),
    schema='work_tracking'
    )
    op.create_table('work_items_commits',
    sa.Column('work_item_id', sa.BigInteger(), nullable=False),
    sa.Column('commit_id', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['commit_id'], ['work_tracking.cached_commits.id'], ),
    sa.ForeignKeyConstraint(['work_item_id'], ['work_tracking.work_items.id'], ),
    sa.PrimaryKeyConstraint('work_item_id', 'commit_id'),
    schema='work_tracking'
    )
    op.create_index(op.f('ix_work_tracking_work_items_commits_commit_id'), 'work_items_commits', ['commit_id'], unique=False, schema='work_tracking')
    op.create_index(op.f('ix_work_tracking_work_items_commits_work_item_id'), 'work_items_commits', ['work_item_id'], unique=False, schema='work_tracking')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_work_tracking_work_items_commits_work_item_id'), table_name='work_items_commits', schema='work_tracking')
    op.drop_index(op.f('ix_work_tracking_work_items_commits_commit_id'), table_name='work_items_commits', schema='work_tracking')
    op.drop_table('work_items_commits', schema='work_tracking')
    op.drop_table('cached_commits', schema='work_tracking')
    # ### end Alembic commands ###
