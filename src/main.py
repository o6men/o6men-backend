import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from locale import currency

import uvicorn
from asyncpg.pgproto.pgproto import timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import middlewares
from src.auth.router import router as auth_router
from src.core import UserCore, CurrencyCore, BankCore, WithdrawCore, TopUpCore
from src.models import User
from src.routers.user import router as user_router
from src.routers.applications import router as application_router
from src.admin.router import router as admin_router
from src.telegram.bot import start_polling

async def create_test_data():
    user_row = await UserCore.find_one()
    if not user_row:
        await UserCore.add(
            first_name="Тестовое имя",
            tg_user_id=892097042,
        )
        user_row = await UserCore.find_one()

    currency_row = await CurrencyCore.find_one()
    if not currency_row:
        await CurrencyCore.add(
            name="Рубль",
            code="ruble",
            symbol="₽",
            rate=94.6,
            percent=2.46,
            min_amount=4000,
            commission_step=15000
        )
        currency_row = await CurrencyCore.find_one()

    bank_row = await BankCore.find_one()
    if not bank_row:
        await BankCore.add(
            name="Сбер",
            code="sber"
        )
        await BankCore.add(
            name="ТБанк",
            code="tbank"
        )
        await BankCore.add(
            name="Альфа",
            code="alfa"
        )
        bank_row = await BankCore.find_one()

    withdraw = await WithdrawCore.find_one()
    if not withdraw:
        await WithdrawCore.add(
            user_id=user_row.id,
            phone="+79981502010",
            card="8843964328371662",
            receiver="Тестовый получатель 1",
            bank_id=bank_row.id,
            currency_id=currency_row.id,
            comment="Тестовый комментарий 1",
            amount=8400,
            amount_in_usd=88.7949260042,
            tag="Тестовый тег 1",
            status="completed",
            datetime=datetime.now(UTC)-timedelta(days=4, minutes=44, seconds=444),
            pre_balance=426
        )

        await WithdrawCore.add(
            user_id=user_row.id,
            phone="+79981502020",
            card="2354578144571663",
            receiver="Тестовый получатель 2",
            bank_id=bank_row.id,
            currency_id=currency_row.id,
            comment="",
            amount=8800,
            amount_in_usd=93.02325581395,
            tag="Тестовый тег 2",
            status="waiting",
            datetime=datetime.now(UTC) - timedelta(days=3, minutes=33, seconds=333),
            pre_balance=337.2050739958
        )

        await WithdrawCore.add(
            user_id=user_row.id,
            phone="+79981502030",
            card="8834964512405435",
            receiver="",
            bank_id=bank_row.id,
            currency_id=currency_row.id,
            comment="Тестовый комментарий 3",
            amount=9760,
            amount_in_usd=103.1712473573,
            tag="",
            status="correction",
            datetime=datetime.now(UTC) - timedelta(days=2, minutes=22, seconds=222),
            pre_balance=337.2050739958
        )

        await WithdrawCore.add(
            user_id=user_row.id,
            phone="+79981502040",
            card="3464591702396546",
            receiver="Тестовый получатель 4",
            bank_id=bank_row.id,
            currency_id=currency_row.id,
            comment="Тестовый комментарий 4",
            amount=6660,
            amount_in_usd=70.4016913319,
            tag="",
            status="reject",
            datetime=datetime.now(UTC) - timedelta(days=1, minutes=11, seconds=111),
            pre_balance=337.2050739958
        )
        withdraw = await WithdrawCore.find_one()

    topup = await TopUpCore.find_one()
    if not topup:
        await TopUpCore.add(
            user_id=user_row.id,
            transaction_hash="qjgni4u5wjgf098ofj23m405pgofj3k423",
            amount=426,
            amount_in_usd=425.617878,
            pre_balance=0,
            datetime=datetime.now(UTC) - timedelta(days=5, minutes=55, seconds=555),
        )

# noinspection PyAsyncCall
@asynccontextmanager
async def lifespan(app: FastAPI):
    # await TgAuthTokenCore.delete()
    asyncio.create_task(start_polling())
    asyncio.create_task(create_test_data())
    yield

app = FastAPI(lifespan=lifespan, root_path_in_servers=False, root_path="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["GET", 'POST', 'OPTIONS', 'DELETE', 'PATCH'],
    allow_headers=['*'],
)

app.middleware("http")(middlewares.allow_credentials)
app.middleware("http")(middlewares.check_auth)


class Item(BaseModel):
    hello: str = 'hello'

@app.get('/', tags=['Базовый адрес'])
async def main_page() -> Item:
    return Item()


app.include_router(auth_router, prefix='/auth')
app.include_router(user_router, prefix='/user')
app.include_router(application_router, prefix='/application')
app.include_router(admin_router, prefix='/admin')

if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)