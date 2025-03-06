from datetime import datetime, UTC, timedelta
from random import randint, choice
from re import compile
from typing import List, Literal

from fastapi.exceptions import HTTPException
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from src.core import UserCore, WithdrawCore, TopUpCore, PatternCore, PatternFieldCore
from src.models import Withdraw, PatternField

router = APIRouter(prefix='', tags=['Пользователь'])

class ResponseUser(BaseModel):
    id: int
    first_name: str | None
    two_fa: bool
    tg_user_id: int
    tg_username: str | None
    email: str | None
    usdt_balance: float


@router.get('/get_user/')
async def get_user(request: Request):
    user_id = request.state.user_id
    user = await UserCore.find_one(id=user_id)
    resp = ResponseUser(**user.__dict__)
    return resp

@router.get('/stats/')
async def stats(request: Request):
    user_id = request.state.user_id
    stats_topup = await TopUpCore.find_all(user_pk=user_id)
    stats_payout = await WithdrawCore.find_all(user_pk=user_id)

    all_stats = []

    count = 0

    for i in stats_payout + stats_topup:
        count += 1
        all_stats.append({
            'id': count,
            'datetime': i.datetime,
            'amount': i.amount,
            'usdt_amount': i.usdt_amount,
            'type': 'payout' if type(i) == Withdraw else 'topup',
            'currency': i.to_currency if type(i) == Withdraw else 'tether',
        })

    for i in range(15):
        count += 1
        amount = randint(1, 10000) / randint(1, 9)
        all_stats.append({
            'id': count,
            'datetime': datetime.now(UTC) - timedelta(hours=randint(0, 50), minutes=randint(0, 200), seconds=randint(0, 800)),
            'amount': amount,
            'usdt_amount': amount * 1.003,
            'type': choice(['topup', 'payout']),
            'currency': 'tether',
        })

    return all_stats


class Pattern(BaseModel):
    class PatternField(BaseModel):
        id: int|None = Field(default=None)
        name: str
        card: str = Field(pattern=compile(r'\d{4} \d{4} \d{4} \d{4}'))
        phone: str = Field(pattern=compile(r'\+7 \d{3} \d{3}-\d{2}-\d{2}'))
        receiver: str|None
        bank: Literal['sber', 'tbank', 'alfa']
        amount: str
        currency: Literal['rubles', 'tenge']
        comment: str|None

        def __eq__(self, other):
            if not isinstance(other, Pattern.PatternField):
                return False
            other: Pattern.PatternField

            if other.name != self.name:
                return False
            if other.card != self.card:
                return False
            if other.phone != self.phone:
                return False
            if other.receiver != self.receiver:
                return False
            if other.bank != self.bank:
                return False
            if other.amount != self.amount:
                return False
            if other.currency != self.currency:
                return False
            if other.comment != self.comment:
                return False

            return True

    name: str
    id: int|None = Field(default=None)
    fields: List[PatternField]

    def __eq__(self, other):
        if not isinstance(other, Pattern):
            return False
        other: Pattern

        if other.name != self.name:
            return False

        if len(self.fields) != len(other.fields):
            return False

        for i in range(len(self.fields)):
            if other.fields[i] != self.fields[i]:
                return False

        return True


@router.post('/save_pattern/')
async def save_pattern(request: Request, pattern: Pattern):
    user_id = request.state.user_id

    all_patterns = await PatternCore.find_all(user_pk=user_id)

    for pattern_row in all_patterns:
        all_forms: List[PatternField] = await PatternFieldCore.find_all(pattern_pk=pattern_row.id)
        class_pattern = Pattern(
            name=pattern.name,
            fields=[
                Pattern.PatternField(
                    name=i.name,
                    card=i.card,
                    phone=i.phone,
                    receiver=i.receiver,
                    bank=i.bank,
                    amount=i.amount,
                    currency=i.currency,
                    comment=i.comment,
                ) for i in all_forms
            ]
        )
        if class_pattern == pattern:
            raise HTTPException(400, {'successful': False, 'already_exists': True})

    last_pattern_id = await PatternCore.find_one(
        order_type='desc'
    )

    if not last_pattern_id:
        new_pattern_id = 1
    else:
        new_pattern_id = last_pattern_id.id + 1

    await PatternCore.add(
        id=new_pattern_id,
        user_pk=user_id,
        name=pattern.name,
    )

    for field in pattern.fields:
        without_id_field = field.model_dump()
        without_id_field.pop('id')
        await PatternFieldCore.add(
            pattern_pk=new_pattern_id,
            **without_id_field
        )

    return {'successful': True}

@router.get('/get_patterns/')
async def get_patterns(request: Request, limit: int = 20) -> List[Pattern]:
    user_id = request.state.user_id
    patterns = []
    pattern_rows = await PatternCore.find_all(user_pk=user_id, limit=limit)
    for i in pattern_rows:
        pattern_fields = await PatternFieldCore.find_all(pattern_pk=i.id)
        patterns.append(Pattern(
            name=i.name,
            id=i.id,
            fields=[Pattern.PatternField(**i.__dict__) for i in pattern_fields]
        ))
    return patterns

@router.delete('/pattern/')
async def delete_pattern(request: Request, id: int):
    user_id = request.state.user_id

    pattern_exists = True if (await PatternCore.find_one(user_pk=user_id, id=id)) else False

    if not pattern_exists:
        raise HTTPException(403, {'error': True})

    await PatternFieldCore.delete(pattern_pk=id)
    await PatternCore.delete(id=id)