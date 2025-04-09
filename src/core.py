from typing import Union, Type, Literal, List, Optional, Tuple

from database import async_session_maker, Base
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result
from sqlalchemy import select, update, delete, asc, desc
from sqlalchemy.exc import SQLAlchemyError
from src.models import User, TgAuthToken, Withdraw, TopUp, ActiveApplication, Pattern, PatternField, Currency, File, \
    Bank, CommissionStep


class BaseCore:
    model: Type[Base] = None

    @staticmethod
    async def execute(query) -> Result:
        async with async_session_maker() as session:
            session: AsyncSession
            result: Result = await session.execute(query)
            return result

    @classmethod
    async def find_all(cls, order_by: str = 'id', order_type: Literal['asc', 'desc'] = 'asc', limit: int = None, **filter_by) -> List[model]:
        order_type: Union[asc, desc] = asc if order_type == 'asc' else desc

        async with async_session_maker() as session:
            query = select(cls.model)

            for field, value in filter_by.items():
                query = query.filter(getattr(cls.model, field) == value)

            query = query.order_by(order_type(getattr(cls.model, order_by)))

            query = query.limit(limit)

            res = await session.execute(query)
            return res.scalars().all()

    @classmethod
    async def find_one(cls, order_by: str = 'id', order_type: Literal['asc', 'desc'] = 'asc', **filter_by) -> Optional[model]:
        order_type: Union[asc, desc] = asc if order_type == 'asc' else desc

        async with async_session_maker() as session:
            query = select(cls.model)

            for field, value in filter_by.items():
                query = query.filter(getattr(cls.model, field) == value)

            query = query.order_by(order_type(getattr(cls.model, order_by)))

            query = query.limit(1)

            res = await session.execute(query)
            return res.scalars().one_or_none()

    @classmethod
    async def add(cls, **values) -> int:
        async with async_session_maker() as session:
            async with session.begin():
                new = cls.model(**values)
                session.add(new)
                try:
                    await session.commit()
                    return new.id
                except SQLAlchemyError as err:
                    await session.rollback()
                    raise err

    @classmethod
    async def update(cls, filter_by, **values) -> int:
        async with async_session_maker() as session:
            async with session.begin():
                query = (
                    update(cls.model)
                    .where(*[getattr(cls.model, k) == v for k, v in filter_by.items()])
                    .values(**values)
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(query)
                try:
                    await session.commit()
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e
                return result.rowcount

    @classmethod
    async def patch(cls, id: int, **values) -> Optional[model]:
        async with async_session_maker() as session:
            async with session.begin():
                query = (
                    update(cls.model)
                    .where(cls.model.id == id)
                    .values(**values)
                    .execution_options(synchronize_session="fetch")
                    .returning(cls.model)
                )
                try:
                    result = await session.execute(query)
                    updated_row = result.scalar_one_or_none()
                    return updated_row
                except SQLAlchemyError as e:
                    await session.rollback()
                    raise e

    @classmethod
    async def delete(cls, **filter_by) -> int:
        async with async_session_maker() as session:
            async with session.begin():
                query = delete(cls.model).where(*[getattr(cls.model, k) == v for k, v in filter_by.items()])
                result = await session.execute(query)
                await session.commit()
                return result.rowcount


class UserCore(BaseCore):
    model = User

class TgAuthTokenCore(BaseCore):
    model = TgAuthToken

class WithdrawCore(BaseCore):
    model = Withdraw

    @classmethod
    async def find_one(cls, order_by: str = 'id', order_type: Literal['asc', 'desc'] = 'asc', **filter_by) -> Optional[Tuple[Withdraw, User, Bank, Currency]]:
        order_type: Union[asc, desc] = asc if order_type == 'asc' else desc
        async with async_session_maker() as session:
            print(filter_by)
            query = (
                select(
                    Withdraw,
                    User,
                    Bank,
                    Currency
                )
                .join(User, User.id == Withdraw.user_id)
                .join(Bank, Bank.id == Withdraw.bank_id)
                .join(Currency, Currency.id == Withdraw.currency_id)
            )
            for field, value in filter_by.items():
                query = query.filter(getattr(Withdraw, field) == value)

            query = query.order_by(order_type(getattr(Withdraw, order_by)))

            query = query.limit(1)

            res = await session.execute(query)
            return res.first()

    @classmethod
    async def patch(cls, id: int, **values) -> Optional[Tuple[Withdraw, User, Bank, Currency]]:
        res = await super().patch(id, **values)
        if res:
            return await cls.find_one(id=id)
        else:
            return None

class TopUpCore(BaseCore):
    model = TopUp

class ActiveApplicationCore(BaseCore):
    model = ActiveApplication

class PatternCore(BaseCore):
    model = Pattern

class PatternFieldCore(BaseCore):
    model = PatternField

class CurrencyCore(BaseCore):
    model = Currency

class CommissionCore(BaseCore):
    model = CommissionStep

class FileCore(BaseCore):
    model = File

class BankCore(BaseCore):
    model = Bank