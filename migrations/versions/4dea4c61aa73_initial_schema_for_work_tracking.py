"""Initial schema for work_tracking

Revision ID: 4dea4c61aa73
Revises: 
Create Date: 2018-11-15 22:25:03.544719

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4dea4c61aa73'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('work_items_sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('integration_type', sa.String(), nullable=False),
    sa.Column('work_items_source_type', sa.String(length=128), nullable=False),
    sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('account_key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('project_key', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('repository_key', postgresql.UUID(as_uuid=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key'),
    schema='work_tracking'
    )
    op.create_table('work_items',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_bug', sa.Boolean(), server_default='FALSE', nullable=False),
    sa.Column('tags', postgresql.ARRAY(sa.String), server_default='{}', nullable=False),
    sa.Column('source_id', sa.String(), nullable=True),
    sa.Column('url', sa.String(), nullable=True),
    sa.Column('source_created_at', sa.DateTime(), nullable=False),
    sa.Column('source_last_updated', sa.DateTime(), nullable=True),
    sa.Column('source_display_id', sa.String(), nullable=False),
    sa.Column('source_state', sa.String(), nullable=False),
    sa.Column('work_items_source_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['work_items_source_id'], ['work_tracking.work_items_sources.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key'),
    schema='work_tracking'
    )
    op.create_index('ix_work_items_work_item_source_id_source_display_id', 'work_items', ['work_items_source_id', 'source_display_id'], unique=False, schema='work_tracking')
    op.create_index(op.f('ix_work_tracking_work_items_source_id'), 'work_items', ['source_id'], unique=False, schema='work_tracking')



def downgrade():
    op.drop_index(op.f('ix_work_tracking_work_items_source_id'), table_name='work_items', schema='work_tracking')
    op.drop_index('ix_work_items_work_item_source_id_source_display_id', table_name='work_items', schema='work_tracking')
    op.drop_table('work_items', schema='work_tracking')
    op.drop_table('work_items_sources', schema='work_tracking')

