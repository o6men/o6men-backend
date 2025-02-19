from datetime import datetime, UTC, timedelta
from re import compile
from typing import List, Literal

from fastapi import APIRouter, Request, Body
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, Field

from src.core import ActiveApplicationCore

router = APIRouter(prefix='', tags=['Заявки'])

class Withdraw(BaseModel):
    id: int | None = Field(default=None)
    name: str
    card: str = Field(pattern=compile(r'\d{4} \d{4} \d{4} \d{4}'))
    phone: str = Field(pattern=compile(r'\+7 \d{3} \d{3}-\d{2}-\d{2}'))
    receiver: str | None
    bank: Literal['sber', 'tbank', 'alfa']
    amount: str
    currency: Literal['rubles', 'tenge']
    comment: str | None


eng_to_rus_bank = {
    'sber': 'Сбер',
    'tbank': 'Тбанк (Тинькофф)',
    'alfa': 'Альфа',
    'vtb': 'ВТБ',
    'open': 'Открытие'
}

@router.post('/withdraw/')
async def main_page(request: Request, withdraw: List[Withdraw]):
    print(withdraw)

class Amount(BaseModel):
    amount: int|float

@router.post('/create_topup/')
async def top_up(request: Request, amount: float = Body(embed=True)):
    user_id = request.state.user_id
    print(user_id, amount)
    user_applications = await ActiveApplicationCore.find_one(user_pk=user_id, type='topup')
    if user_applications:
        raise HTTPException(400, 'There is already an application')
    await ActiveApplicationCore.add(
        user_pk=user_id,
        type='topup',
        expired_at=datetime.now(UTC) + timedelta(minutes=30),
        amount=amount
    )