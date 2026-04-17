"""Add unique field/date_time constraint for meteo_data

Revision ID: d9a2e7b5f101
Revises: 08511d7a3065
Create Date: 2026-03-26 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d9a2e7b5f101"
down_revision: Union[str, None] = "08511d7a3065"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM meteo_data a
        USING meteo_data b
        WHERE a.ctid < b.ctid
          AND a.field_id = b.field_id
          AND a.date_time = b.date_time
        """
    )
    op.create_unique_constraint(
        "uq_meteo_data_field_id_date_time",
        "meteo_data",
        ["field_id", "date_time"],
    )
    op.create_index("ix_meteo_data_date_time", "meteo_data", ["date_time"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_meteo_data_date_time", table_name="meteo_data")
    op.drop_constraint("uq_meteo_data_field_id_date_time", "meteo_data", type_="unique")
