"""new_revision

Revision ID: 082b29525a76
Revises: c97c1d23ab69
Create Date: 2025-04-27 21:00:16.191081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '082b29525a76'
down_revision: Union[str, None] = 'c97c1d23ab69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('withdraw_currency_id_fkey', 'withdraw', type_='foreignkey')
    op.drop_constraint('withdraw_bank_id_fkey', 'withdraw', type_='foreignkey')
    op.create_foreign_key(None, 'withdraw', 'currency', ['currency_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'withdraw', 'bank', ['bank_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'withdraw', type_='foreignkey')
    op.drop_constraint(None, 'withdraw', type_='foreignkey')
    op.create_foreign_key('withdraw_bank_id_fkey', 'withdraw', 'bank', ['bank_id'], ['id'])
    op.create_foreign_key('withdraw_currency_id_fkey', 'withdraw', 'currency', ['currency_id'], ['id'])
    # ### end Alembic commands ###
