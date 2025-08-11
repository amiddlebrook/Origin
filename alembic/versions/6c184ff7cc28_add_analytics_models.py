"""Add analytics models

Revision ID: 6c184ff7cc28
Revises: 87ba1bcec004
Create Date: 2025-08-11 15:41:08.373772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c184ff7cc28'
down_revision: Union[str, None] = '87ba1bcec004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_activities table
    op.create_table(
        'user_activities',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('activity_type', sa.String(100), nullable=False),
        sa.Column('activity_data', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False)
    )
    
    # Create search_queries table
    op.create_table(
        'search_queries',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('query', sa.String(500), nullable=False),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('filters', sa.JSON(), nullable=True),
        sa.Column('search_type', sa.String(50), nullable=False, server_default='all'),
        sa.Column('is_advanced', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True)
    )
    
    # Create content_interactions table
    op.create_table(
        'content_interactions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, index=True),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('interaction_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True)
    )
    
    # Create indexes for content_interactions
    op.create_index('idx_content_interactions_content', 'content_interactions', ['content_type', 'content_id'])
    op.create_index('idx_content_interactions_created', 'content_interactions', ['created_at'])


def downgrade() -> None:
    op.drop_table('content_interactions')
    op.drop_table('search_queries')
    op.drop_table('user_activities')
