import shutil
from datetime import datetime, timedelta, UTC
from pathlib import Path
from random import randint, choice
from typing import List, Literal, Annotated

import sqlalchemy.exc
from fastapi import APIRouter, Body, Response, HTTPException, Query, UploadFile, File as File_fastapi
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, or_, cast, DateTime, func, String
from sqlalchemy.orm import selectinload

import config
from src import jwt
from src.admin.schemas import CurrencyModel, CreateCurrencyInput, GetCurrenciesResponse, CreateCurrencyResponse, \
    WithdrawModel, GetWithdrawsResponse, GetWithdrawsInput, GetUsersResponse, UserModel, WithdrawUpdateTagInput, \
    WithdrawUpdateTagResponse, GetTopUpsInput, TopUpModel, GetTopUpsResponse, GetBanksResponse, BankModel
from src.core import async_session_maker, UserCore, CurrencyCore, WithdrawCore, FileCore
from src.models import User, Currency, Withdraw, TopUp, Bank

router = APIRouter(prefix='', tags=['Админ панель'])


@router.post('/auth/')
async def auth(response: Response, token: str = Body(..., embed=True)):
    if token == config.ADMIN_TOKEN:
        admin_access_token = jwt.create_jwt_token({'sub': 'admin'})
        response.set_cookie(key='admin_access_token', value=admin_access_token, httponly=True, samesite='lax',
                            secure=False)
        return {'access': True}
    else:
        return {'access': False}


@router.get('/check_auth/')
async def check_auth():
    return {"ok": True, "result": "Authenticated"}


@router.get('/get_withdraws/')
async def get_withdraws(params: Annotated[GetWithdrawsInput, Query()]) -> GetWithdrawsResponse:
    page, limit, statuses, banks, sort_by, order, search, start_date, end_date = (
        params.page, params.limit, params.statuses, params.banks, params.sort_by, params.order, params.search, params.start_date, params.end_date
    )

    query = select(Withdraw)

    if statuses:
        query = query.filter(Withdraw.status.in_(statuses))

    if banks:
        query = query.filter(Withdraw.bank_id.in_(banks))

    if search:
        search = search.lower()
        query = query.filter(
            or_(
                cast(Withdraw.amount_in_usd, String).ilike(f'%{search}%'),
                cast(Withdraw.amount, String).ilike(f'%{search}%'),
                cast(Withdraw.datetime, String).ilike(f'%{search}%'),
                cast(Withdraw.phone, String).ilike(f'%{search}%'),
                cast(Withdraw.card, String).ilike(f'%{search}%'),
                cast(Withdraw.comment, String).ilike(f'%{search}%'),
                cast(Withdraw.tag, String).ilike(f'%{search}%'),
            )
        )

    if start_date:
        query = query.filter(cast(Withdraw.datetime, DateTime(timezone=True)) >= start_date)

    if end_date:
        query = query.filter(cast(Withdraw.datetime, DateTime(timezone=True)) <= end_date)

    if sort_by in ["datetime", "amount_in_usd", "status"]:
        if order == "desc":
            query = query.order_by(getattr(Withdraw, sort_by).desc())
        else:
            query = query.order_by(getattr(Withdraw, sort_by))

    query = query.offset((page - 1) * limit).limit(limit)

    async with async_session_maker() as session:
        total_withdraw_count = await session.scalar(select(func.count()).select_from(Withdraw)) or 0
        total_amount_in_usd = await session.scalar(select(func.sum(Withdraw.amount_in_usd)).select_from(Withdraw)) or 0

        result = await session.execute(query)
        withdraw_list = result.scalars().all()

    response_withdraws = []

    page_count = (total_withdraw_count + limit - 1) // limit
    page_withdraw_count = 0
    page_amount_in_usd = 0

    for withdraw_row in withdraw_list:
        page_withdraw_count += 1
        page_amount_in_usd += withdraw_row.amount_in_usd
        response_withdraws.append(WithdrawModel(**withdraw_row.__dict__))

    response = GetWithdrawsResponse(
        ok=True,
        result=GetWithdrawsResponse.Result(
            withdraws=response_withdraws,
            meta=GetWithdrawsResponse.Meta(
                page=page,
                page_count=page_count,
                limit=limit,
                total_withdraw_count=total_withdraw_count,
                page_withdraw_count=page_withdraw_count,
                total_amount_in_usd=total_amount_in_usd,
                page_amount_in_usd=page_amount_in_usd
            )
        )
    )

    return response

#
# @router.get("/withdraw/get_document/{withdraw_id}/")
# async def withdraw_document(withdraw_id: str):
#     file_id = withdraw_list[int(withdraw_id)].document
#     file_row = await FileCore.find_one(id=file_id)
#     document = Path(file_row.path)
#     if document.exists():
#         return FileResponse(document)
#     else:
#         raise HTTPException(401, "File not found")
#
#
# @router.post("/withdraw/upload_document/{withdraw_id}/")
# async def withdraw_upload_document(withdraw_id: str, file: UploadFile = File_fastapi(...)):
#     try:
#         path = f"files/{file.filename}"
#         with open(path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#         await FileCore.add(path=path)
#         file_row = await FileCore.find_one(path=path, order_type="desc")
#         global withdraw_list
#         withdraw_list[int(withdraw_id)].document = file_row.id
#         return JSONResponse(content={"message": "File uploaded successfully"}, status_code=200)
#     except Exception as e:
#         raise HTTPException(400)
#

@router.patch('/withdraw/update_tag/')
async def update_tag(data: WithdrawUpdateTagInput, response: Response) -> WithdrawUpdateTagResponse:
    try:
        await WithdrawCore.update({"id": data.id}, tag=data.tag)
        return WithdrawUpdateTagResponse(
            ok=True,
            result="Success"
        )
    except:
        response.status_code = 500
        return WithdrawUpdateTagResponse(
            ok=False,
            error="Some error"
        )


@router.get('/get_topups/')
async def get_topups(params: Annotated[GetTopUpsInput, Query()]):
    page, limit, sort_by, order, search, start_date, end_date = (
        params.page, params.limit, params.sort_by, params.order, params.search,
        params.start_date, params.end_date
    )

    query = select(TopUp)

    if search:
        search = search.lower()
        query = query.filter(
            or_(
                cast(TopUp.amount_in_usd, String).ilike(f'%{search}%'),
                cast(TopUp.amount, String).ilike(f'%{search}%'),
                cast(TopUp.datetime, String).ilike(f'%{search}%'),
            )
        )

    if start_date:
        query = query.filter(cast(TopUp.datetime, DateTime(timezone=True)) >= start_date)

    if end_date:
        query = query.filter(cast(TopUp.datetime, DateTime(timezone=True)) <= end_date)

    if sort_by in ["datetime", "amount_in_usd"]:
        if order == "desc":
            query = query.order_by(getattr(TopUp, sort_by).desc())
        else:
            query = query.order_by(getattr(TopUp, sort_by))

    query = query.offset((page - 1) * limit).limit(limit)

    async with async_session_maker() as session:
        total_topup_count = await session.scalar(select(func.count()).select_from(TopUp)) or 0
        total_amount_in_usd = await session.scalar(select(func.sum(TopUp.amount_in_usd)).select_from(TopUp)) or 0

        result = await session.execute(query)
        topup_list = result.scalars().all()

    response_topups = []

    page_count = (total_topup_count + limit - 1) // limit
    page_topup_count = 0
    page_amount_in_usd = 0

    for topup_row in topup_list:
        page_topup_count += 1
        page_amount_in_usd += topup_row.amount_in_usd
        response_topups.append(TopUpModel(**topup_row.__dict__))

    response = GetTopUpsResponse(
        ok=True,
        result=GetTopUpsResponse.Result(
            topups=response_topups,
            meta=GetTopUpsResponse.Meta(
                page=page,
                page_count=page_count,
                limit=limit,
                total_topup_count=total_topup_count,
                page_topup_count=page_topup_count,
                total_amount_in_usd=total_amount_in_usd,
                page_amount_in_usd=page_amount_in_usd
            )
        )
    )

    return response


@router.get('/get_users/')
async def get_users(ids: Annotated[List[int], Query(example=[12, 20])] = None):
    async with async_session_maker() as session:
        if not ids:
            query = select(User).order_by(User.id.asc())
        else:
            query = select(User).filter(User.id.in_(ids)).order_by(User.id.asc())
        result = await session.execute(query)
        user_rows = result.scalars().all()

    response = GetUsersResponse(
        ok=True,
        result=[UserModel(**row.__dict__) for row in user_rows]
    )

    return response


@router.get('/get_currencies/')
async def get_currencies(ids: Annotated[List[int], Query(example=[12, 20])] = None) -> GetCurrenciesResponse:
    async with async_session_maker() as session:
        if not ids:
            query = select(Currency).order_by(Currency.id.asc())
        else:
            query = select(Currency).filter(Currency.id.in_(ids)).order_by(Currency.id.asc())
        result = await session.execute(query)
        currency_rows = result.scalars().all()

    response = GetCurrenciesResponse(
        ok=True,
        result=[CurrencyModel(**row.__dict__) for row in currency_rows]
    )

    return response


@router.post('/create_currency/')
async def create_currency(input_currency: CreateCurrencyInput, response: Response) -> CreateCurrencyResponse:
    try:
        await CurrencyCore.add(
            name=input_currency.name,
            code=input_currency.code,
            symbol=input_currency.symbol,
            percent=input_currency.percent,
            min_amount=input_currency.min_amount,
            commission_step=input_currency.commission_step
        )
    except sqlalchemy.exc.IntegrityError:
        response.status_code = 400
        return CreateCurrencyResponse(
            ok=False,
            error="This name or code already exist"
        )

    async with async_session_maker() as session:
        query = select(Currency).filter(
            Currency.name == input_currency.name,
            Currency.code == input_currency.code,
            Currency.symbol == input_currency.symbol,
            Currency.percent == input_currency.percent,
            Currency.min_amount == input_currency.min_amount,
            Currency.commission_step == input_currency.commission_step
        )
        result = await session.execute(query)
        currency_row = result.scalars().one_or_none()

    if currency_row:
        return CreateCurrencyResponse(
            ok=True,
            result=CurrencyModel(**currency_row.__dict__)
        )
    else:
        response.status_code = 500
        return CreateCurrencyResponse(
            ok=False,
            error="Unknown error"
        )

@router.get("/get_banks/")
async def get_banks(ids: Annotated[List[int], Query(example=[12, 20])] = None):
    async with async_session_maker() as session:
        if not ids:
            query = select(Bank).order_by(Bank.id.asc())
        else:
            query = select(Bank).filter(Bank.id.in_(ids)).order_by(Bank.id.asc())
        result = await session.execute(query)
        banks_rows = result.scalars().all()

    response = GetBanksResponse(
        ok=True,
        result=[BankModel(**row.__dict__) for row in banks_rows]
    )

    return response

