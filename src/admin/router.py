import re
import shutil
from datetime import datetime, timedelta, UTC
from pathlib import Path
from random import randint, choice
from re import compile
from typing import List, Literal, Annotated

from fastapi import APIRouter, Body, Response, HTTPException, Query, UploadFile, File as File_fastapi
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import config
from config import BANKS
from src import jwt
from src.core import UserCore, CurrencyCore, WithdrawCore, FileCore
from src.models import User

router = APIRouter(prefix='', tags=['Админ панель'])

@router.post('/auth/')
async def auth(response: Response, token: str = Body(..., embed=True)):
    if token == config.ADMIN_TOKEN:
        admin_access_token = jwt.create_jwt_token({'sub': 'admin'})
        response.set_cookie(key='admin_access_token', value=admin_access_token, httponly=True, samesite='lax', secure=False)
        return {'access': True}
    else:
        return {'access': False}

@router.get('/check_auth/')
async def check_auth():
    return {'auth': True}

class Withdraw(BaseModel):
    class Searched(BaseModel):
        field: str
        offset: int
        length: int

    id: int
    datetime: int
    amount: float
    amount_in_usd: float
    currency: str
    user: str
    phone: str
    card: str
    receiver: str|None
    bank: str
    tag: str|None
    status: Literal['completed', 'waiting', 'reject', 'correction']
    comment: str|None
    searched: List[Searched]|None = Field(default=None)
    document: int|None = Field(default=None)

class WithdrawsResponse(BaseModel):
    class Meta(BaseModel):
        page: int
        limit: int
        total_withdraws: int
        total_pages: int
        total_amount: float
        page_amount: float
        banks: dict = BANKS

    withdraws: List[Withdraw]
    meta: Meta

withdraw_list = []
count = 268
last_dt = datetime.now(UTC)
for i in reversed(range(268)):
    last_dt = last_dt - timedelta(hours=randint(0, 8), minutes=randint(0, 88),
                                                  seconds=randint(0, 654))
    count -= 1
    amount = randint(1, 10000) / randint(1, 9)
    withdraw_list.append(Withdraw(**{
        'id': count,
        'datetime': int(last_dt.timestamp()),
        'amount': amount,
        'amount_in_usd': amount / 96.23,
        'currency': choice(['rubles', 'tenge']),
        'user': 'astercael',
        'phone': f'+7 ({randint(100, 999)}) {randint(100, 999)}-{randint(10, 99)}-{randint(10, 99)}',
        'card': f'{randint(1000, 9999)} {randint(1000, 9999)} {randint(1000, 9999)} {randint(1000, 9999)}',
        'receiver': 'Пусто',
        'bank': choice(['tbank', 'sber', 'alfa']),
        'tag': choice(['Метка', '']),
        'status': choice(['completed', 'waiting', 'reject', 'correction']),
        'comment': choice(['Какой-то комментарий', ''])
    }))

class WithdrawParams(BaseModel):
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1),
    statuses: List[Literal["completed", "waiting", "reject", "correction"]] | None = Query(default=None),
    banks: List[str] | None = Query(default=None),
    sort_by: Literal["datetime", "amount"] = "datetime",
    order: Literal["asc", "desc"] = "desc"
    search: str | None = Query(None)

@router.get('/withdraws/')
async def withdraws(params: Annotated[WithdrawParams, Query()]) -> WithdrawsResponse:
    page, limit, statuses, banks, sort_by, order, search = params.page, params.limit, params.statuses, params.banks, params.sort_by, params.order, params.search

    filtered_withdraws = []
    total_withdraws = 0
    start_slice = -limit+limit*page
    end_slice = limit*page
    total_amount = 0

    for i in withdraw_list:
        add = True
        if not statuses is None:
            if i.status not in statuses:
                add = False
        if not banks is None:
            if i.bank not in banks:
                add = False
        if search:
            list_searched = []
            for key, value in  i.__dict__.items():
                if key == "bank":
                    value = BANKS[value]
                elif key == "datetime":
                    value = datetime.fromtimestamp(value).strftime("%d.%m.%Y %H:%M:%S")
                if search.lower() in str(value).lower():
                    re_res = re.compile(search.lower()).search(str(value).lower())
                    list_searched.append(Withdraw.Searched(
                        field=key,
                        offset=re_res.start(),
                        length=re_res.end() - re_res.start()
                    ))
            if list_searched:
                i.searched = list_searched
            else:
                add = False
        if add:
            filtered_withdraws.append(i)
            total_withdraws += 1
            total_amount += i.amount_in_usd

    sorted_withdraws = sorted(
        filtered_withdraws,
        key=lambda x: x.__dict__[sort_by],
        reverse=True if order == 'desc' else False
    )

    slice_withdraws = sorted_withdraws[start_slice:end_slice]

    total_pages = (total_withdraws + limit - 1) // limit
    page_amount = 0

    for i in slice_withdraws:
        page_amount += i.amount_in_usd

    response = WithdrawsResponse(
        withdraws=slice_withdraws,
        meta=WithdrawsResponse.Meta(
            page=page,
            limit=limit,
            total_withdraws=total_withdraws,
            total_pages=total_pages,
            total_amount=total_amount,
            page_amount=page_amount
        )
    )

    return response

@router.get("/withdraw/document/{withdraw_id}/")
async def withdraw_document(withdraw_id: str):
    file_id = withdraw_list[int(withdraw_id)].document
    file_row = await FileCore.find_one(id=file_id)
    document = Path(file_row.path)
    if document.exists():
        return FileResponse(document)
    else:
        raise HTTPException(401, "File not found")


@router.post("/withdraw/upload_document/{withdraw_id}/")
async def withdraw_upload_document(withdraw_id: str, file: UploadFile = File_fastapi(...)):
    try:
        path = f"files/{file.filename}"
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        await FileCore.add(path=path)
        file_row = await FileCore.find_one(path=path, order_type="desc")
        global withdraw_list
        withdraw_list[int(withdraw_id)].document = file_row.id
        return JSONResponse(content={"message": "File uploaded successfully"}, status_code=200)
    except Exception as e:
        raise HTTPException(400)


@router.patch('/withdraw/update_tag/')
async def update_tag(id: int = Body(..., embed=True), tag: str = Body(..., embed=True)):
    found_withdraw = True if (await WithdrawCore.find_one(id=id)) else False
    if not found_withdraw:
        print(f'NOT FOUND {id=}, {tag=}')
        return HTTPException(403)


@router.get('/topups/')
async def topups():
    topup_list = []

    count = 0
    for i in range(15):
        count += 1
        amount = randint(1, 10000) / randint(1, 9)
        topup_list.append({
            'id': count,
            'datetime': datetime.now(UTC) - timedelta(hours=randint(0, 50), minutes=randint(0, 200), seconds=randint(0, 800)),
            'amount': amount,
            'amount_in_usd': amount + 1.0003,
            'user': 'astercael',
            'tag': 'Пусто',
            'status': choice(['completed', 'waiting', 'reject']),
        })

    return topup_list


@router.get('/users/')
async def users():
    user_list = []
    user_rows = await UserCore.find_all()

    for user in user_rows:
        user: User
        user_list.append({
            'datetime': user.registered_at,
            'name': user.first_name,
            'username': user.tg_username,
            'balance': user.tether_balance
        })

    return user_list

@router.get('/currencies/')
async def currencies():
    currency_list = []
    currency_rows = await CurrencyCore.find_all()

    for currency in currency_rows:
        currency_list.append({
            'name': currency.name,
            'code': currency.code,
            'symbol': currency.symbol,
            'rate': currency.rate,
            'percent': currency.percent,
            'min_amount': currency.min_amount,
            'commission_step': currency.commission_step
        })

    return currency_list

class CurrencyModel(BaseModel):
    name: str
    code: str
    symbol: str
    percent: str = Field(pattern=compile(r'[+\d.-]+'))
    min_amount: str = Field(pattern=compile(r'[+\d.-]+'))
    commission_step: str = Field(pattern=compile(r'[+\d.-]+'))

@router.post('/create_currency/')
async def create_currency(currency: CurrencyModel):
    await CurrencyCore.add(
        name=currency.name,
        code=currency.code,
        symbol=currency.symbol,
        percent=float(currency.percent),
        min_amount=float(currency.min_amount),
        commission_step=float(currency.commission_step)
    )
    return {'success': True}