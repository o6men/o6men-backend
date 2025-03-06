import asyncio
import string
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from locale import currency
from random import randint, choice

import uvicorn
from asyncpg.pgproto.pgproto import timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from websockets.sync.server import serve

from src import middlewares
from src.auth.router import router as auth_router
from src.core import UserCore, CurrencyCore, BankCore, WithdrawCore, TopUpCore
from src.models import User
from src.routers.user import router as user_router
from src.routers.applications import router as application_router
from src.admin.router import router as admin_router
from src.telegram.bot import start_polling

async def create_test_data():
    user_rows = await UserCore.find_all()
    if len(user_rows) < 8:
        for i in range(8):
            await UserCore.add(
                first_name="Тестовое имя" + str(i),
                tg_user_id=892097043 + i,
            )
        user_rows = await UserCore.find_all()

    currency_rows = await CurrencyCore.find_all()
    if not currency_rows:
        await CurrencyCore.add(
            name="Рубль",
            code="ruble",
            symbol="₽",
            rate=94.6,
            percent=2.46,
            min_amount=4000,
            commission_step=15000
        )
        currency_rows = await CurrencyCore.find_all()

    bank_rows = await BankCore.find_all()
    if not bank_rows:
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
        bank_rows = await BankCore.find_all()

    withdraws = await WithdrawCore.find_all()
    if len(withdraws) < 60:
        last_dt = datetime.now(UTC)
        for i in range(60):
            amount = randint(1, 10000) / randint(1, 9)
            last_dt = last_dt - timedelta(days=randint(1, 2), hours=randint(0, 8), minutes=randint(0, 88), seconds=randint(0, 654))
            await WithdrawCore.add(
                user_id=choice(user_rows).id,
                phone=f'+7 ({randint(100, 999)}) {randint(100, 999)}-{randint(10, 99)}-{randint(10, 99)}',
                card=f'{randint(1000, 9999)} {randint(1000, 9999)} {randint(1000, 9999)} {randint(1000, 9999)}',
                receiver=choice(("Тестовый получатель" + str(i), "")),
                bank_id=choice(bank_rows).id,
                currency_id=choice(currency_rows).id,
                comment=choice(("Тестовый комментарий" + str(i), "")),
                amount=amount,
                usdt_amount=amount/99.104,
                tag=choice(("Тестовый тег" + str(i), "")),
                status=choice(['completed', 'waiting', 'reject', 'correction']),
                datetime=last_dt,
                pre_balance=randint(500, 12423)
            )
        withdraws = await WithdrawCore.find_all()

    topups = await TopUpCore.find_all()
    if len(topups) < 68:
        last_dt = datetime.now(UTC)
        for i in range(68):
            amount = randint(1, 10000) / randint(1, 9)
            last_dt = last_dt - timedelta(days=randint(1, 2), hours=randint(0, 8), minutes=randint(0, 88),
                                          seconds=randint(0, 654))
            await TopUpCore.add(
                user_id=choice(user_rows).id,
                transaction_hash="".join([choice(string.ascii_letters) for _ in range(64)]),
                amount=amount,
                usdt_amount=amount/99.104,
                pre_balance=randint(500, 12423),
                datetime=last_dt,
            )

# noinspection PyAsyncCall
@asynccontextmanager
async def lifespan(app: FastAPI):
    # await TgAuthTokenCore.delete()
    asyncio.create_task(start_polling())
    asyncio.create_task(create_test_data())
    yield

app = FastAPI(lifespan=lifespan, servers=[{"url": "https://o6men.site/api/"}], root_path="/api")

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