"""support_imported_work_items_sources

Revision ID: 8caff16606a3
Revises: 35f4aebc67ce
Create Date: 2019-06-17 16:42:38.825113

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8caff16606a3'
down_revision = '35f4aebc67ce'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('account_key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('organization_key', postgresql.UUID(as_uuid=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key'),
    schema='work_tracking'
    )
    op.add_column('work_items_sources', sa.Column('connector_key', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False), schema='work_tracking')
    op.add_column('work_items_sources', sa.Column('project_id', sa.Integer(), nullable=True), schema='work_tracking')
    op.add_column('work_items_sources', sa.Column('source_created_at', sa.DateTime(), nullable=True), schema='work_tracking')
    op.add_column('work_items_sources', sa.Column('source_id', sa.String(), nullable=True), schema='work_tracking')
    op.add_column('work_items_sources', sa.Column('url', sa.String(), nullable=True), schema='work_tracking')
    op.add_column('work_items_sources', sa.Column('source_record', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=True), schema='work_tracking')
    op.add_column('work_items_sources', sa.Column('source_updated_at', sa.DateTime(), nullable=True), schema='work_tracking')
    op.alter_column('work_items_sources', 'organization_key',
               existing_type=postgresql.UUID(),
               nullable=True,
               schema='work_tracking')
    op.create_foreign_key('work_items_sources_projects_fk', 'work_items_sources', 'projects', ['project_id'], ['id'], source_schema='work_tracking', referent_schema='work_tracking')

    op.create_index(op.f('ix_work_tracking_work_items_sources_source_id'), 'work_items_sources', ['source_id'],
                    unique=False, schema='work_tracking')
    # ### end Alembic commands ###


def downgrade():

    op.drop_constraint('work_items_sources_projects_fk', 'work_items_sources', schema='work_tracking', type_='foreignkey')
    op.drop_index(op.f('ix_work_tracking_work_items_sources_source_id'), table_name='work_items_sources',
                  schema='work_tracking')
    op.alter_column('work_items_sources', 'organization_key',
               existing_type=postgresql.UUID(),
               nullable=False,
               schema='work_tracking')
    op.drop_column('work_items_sources', 'source_updated_at', schema='work_tracking')
    op.drop_column('work_items_sources', 'source_record', schema='work_tracking')
    op.drop_column('work_items_sources', 'source_id', schema='work_tracking')
    op.drop_column('work_items_sources', 'source_created_at', schema='work_tracking')
    op.drop_column('work_items_sources', 'project_id', schema='work_tracking')
    op.drop_column('work_items_sources', 'connector_key', schema='work_tracking')
    op.drop_table('projects', schema='work_tracking')
    # ### end Alembic commands ###
