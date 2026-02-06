"""Initial schema with Job, ExtractedData, and Source models

Revision ID: 001
Revises: 
Create Date: 2026-02-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create source table
    op.create_table(
        'source',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.Enum('DATABASE', 'VECTOR', 'WEB', 'RESEARCH', name='sourcetype'), nullable=False),
        sa.Column('trust_score', sa.Float(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_source_name'), 'source', ['name'], unique=False)

    # Create job table
    op.create_table(
        'job',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', name='jobstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.String(length=1000), nullable=True),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_source_name'), 'job', ['source_name'], unique=False)
    op.create_index(op.f('ix_job_status_created'), 'job', ['status', 'created_at'], unique=False)
    op.create_index(op.f('ix_job_created_at'), 'job', ['created_at'], unique=False)
    op.create_index(op.f('ix_job_source_created'), 'job', ['source_name', 'created_at'], unique=False)

    # Create extracted_data table
    op.create_table(
        'extracted_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('extracted_at', sa.DateTime(), nullable=False),
        sa.Column('trust_score', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['job.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extracted_data_job_id'), 'extracted_data', ['job_id'], unique=False)
    op.create_index(op.f('ix_extracted_data_source'), 'extracted_data', ['source'], unique=False)
    op.create_index(op.f('ix_extracted_data_job_created'), 'extracted_data', ['job_id', 'extracted_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_extracted_data_job_created'), table_name='extracted_data')
    op.drop_index(op.f('ix_extracted_data_source'), table_name='extracted_data')
    op.drop_index(op.f('ix_extracted_data_job_id'), table_name='extracted_data')
    op.drop_table('extracted_data')
    
    op.drop_index(op.f('ix_job_source_created'), table_name='job')
    op.drop_index(op.f('ix_job_created_at'), table_name='job')
    op.drop_index(op.f('ix_job_status_created'), table_name='job')
    op.drop_index(op.f('ix_job_source_name'), table_name='job')
    op.drop_table('job')
    
    op.drop_index(op.f('ix_source_name'), table_name='source')
    op.drop_table('source')
