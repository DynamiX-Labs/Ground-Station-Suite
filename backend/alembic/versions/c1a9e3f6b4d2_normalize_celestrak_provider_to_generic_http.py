# Copyright (c) 2026 Efstratios Goudelis
# Modifications and extensions Copyright (C) 2026 DynamiX-Labs

"""normalize celestrak provider to generic_http

Revision ID: c1a9e3f6b4d2
Revises: 4f8c2b1d7e6a
Create Date: 2026-05-02 16:40:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c1a9e3f6b4d2"
down_revision = "4f8c2b1d7e6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE tle_sources
            SET provider = 'generic_http'
            WHERE lower(coalesce(provider, '')) = 'celestrak'
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE tle_sources
            SET provider = 'celestrak'
            WHERE lower(coalesce(provider, '')) = 'generic_http'
              AND lower(coalesce(url, '')) LIKE '%celestrak%'
            """
        )
    )
