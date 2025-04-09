import asyncio
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Annotated, Literal

from sqlalchemy import Integer, func, ForeignKey, DateTime, BigInteger, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship

import config
from database import Base

created_at = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]
text = Annotated[str, mapped_column(Text)]


class User(Base):
    __tablename__ = 'user_table'

    id = mapped_column(Integer, primary_key=True)
    first_name: Mapped[text]
    password: Mapped[text | None]
    two_fa: Mapped[bool] = mapped_column(default=False)
    tg_user_id = mapped_column(BigInteger, unique=True)
    tg_username: Mapped[text | None] = mapped_column(unique=True)
    role: Mapped[text] = mapped_column(default='user')
    email: Mapped[text | None] = mapped_column(unique=True)
    registered_at: Mapped[created_at]
    photo_url: Mapped[text | None]
    usdt_balance: Mapped[float] = mapped_column(default=0.0)

    tgauthtoken: Mapped[List['TgAuthToken']] = relationship()
    withdraw: Mapped[List['Withdraw']] = relationship()
    top_up: Mapped[List['TopUp']] = relationship()
    active_application: Mapped[List['ActiveApplication']] = relationship()
    pattern: Mapped[List['Pattern']] = relationship()

    def __str__(self):
        return f'User: {self.id=}, {self.tg_username=}, {self.role=}'


def token_end_at():
    return datetime.now() + timedelta(minutes=config.TOKEN_LIFETIME)


class TgAuthToken(Base):
    @staticmethod
    def generate_token():
        a, b = ''.join([secrets.choice(string.digits) for _ in range(6)]), ''.join(
            [secrets.choice(string.digits + string.ascii_letters) for _ in range(24)])
        return f'{a}:{b}'

    id = mapped_column(Integer, primary_key=True)
    user_pk: Mapped[int] = mapped_column(ForeignKey('user_table.id'))
    created_at: Mapped[created_at]
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=token_end_at)
    token: Mapped[text] = mapped_column(default=generate_token, unique=True)

    def __str__(self):
        return f'TgAuthToken: {self.id=}, {self.created_at=}, {self.end_at=}, {self.token=}'


class Withdraw(Base):
    id = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user_table.id'))
    phone: Mapped[text]
    card: Mapped[text]
    receiver: Mapped[text]
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id"))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currency.id"))
    comment: Mapped[text]
    amount: Mapped[float]
    usdt_amount: Mapped[float]
    tag: Mapped[text]
    status: Mapped[text]
    datetime: Mapped[created_at]
    pre_balance: Mapped[float]
    document: Mapped[str | None] = None


class TopUp(Base):
    id = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('user_table.id'))
    datetime: Mapped[created_at]
    transaction_hash: Mapped[text]
    usdt_amount: Mapped[float]
    pre_balance: Mapped[float]


class ActiveApplication(Base):
    id = mapped_column(Integer, primary_key=True)
    user_pk: Mapped[int] = mapped_column(ForeignKey('user_table.id'))
    datetime: Mapped[created_at]
    type: Mapped[Literal['topup', 'payout']]
    usdt_amount: Mapped[float]
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Pattern(Base):
    id = mapped_column(Integer, primary_key=True)
    user_pk: Mapped[int] = mapped_column(ForeignKey('user_table.id'))

    name: Mapped[text]
    field: Mapped[List['PatternField']] = relationship()


class PatternField(Base):
    id = mapped_column(Integer, primary_key=True)
    pattern_pk: Mapped[int] = mapped_column(ForeignKey('pattern.id'))
    name: Mapped[text]
    card: Mapped[text]
    phone: Mapped[text]
    receiver: Mapped[text | None]
    bank: Mapped[text]
    amount: Mapped[text]
    currency: Mapped[text]
    comment: Mapped[text | None]


class Currency(Base):
    id = mapped_column(Integer, primary_key=True)
    name: Mapped[text] = mapped_column(unique=True)
    code: Mapped[text] = mapped_column(unique=True)
    symbol: Mapped[text | None]
    rate: Mapped[float]
    rate_source: Mapped[text | None] = None
    min_amount: Mapped[float] = mapped_column(default=0.0)

    withdraw: Mapped[List['Withdraw']] = relationship()


class IndividualCurrency(Base):
    id = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = ForeignKey("user.id")
    currency_id: Mapped[int] = ForeignKey("currency.id")
    rate: Mapped[float]
    rate_source: Mapped[text | None] = None
    min_amount: Mapped[float] = 0


class CommissionStep(Base):
    id = mapped_column(Integer, primary_key=True)
    currency_type: Mapped[Literal["currency", "individual_currency"]]
    currency_id: Mapped[int]
    min: Mapped[float]
    max: Mapped[float]
    commission: Mapped[float]


class File(Base):
    id = mapped_column(Integer, primary_key=True)
    path: Mapped[text]


class Bank(Base):
    id = mapped_column(Integer, primary_key=True)
    name: Mapped[text] = mapped_column(unique=True)
    code: Mapped[text] = mapped_column(unique=True)

    withdraw: Mapped[List['Withdraw']] = relationship()
