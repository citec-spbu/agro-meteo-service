"""renamed longitude

Revision ID: 16670270ff97
Revises: 1fbabf2a972c
Create Date: 2024-05-07 02:11:34.427487

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16670270ff97'
down_revision: Union[str, None] = '1fbabf2a972c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('fields', sa.Column('longitude', sa.Float(), nullable=False))
    op.drop_column('fields', 'longtitude')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('fields', sa.Column('longtitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    op.drop_column('fields', 'longitude')
    # ### end Alembic commands ###
