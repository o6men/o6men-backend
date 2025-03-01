from typing import Annotated

import sqlalchemy.exc
from fastapi import APIRouter, Body, Response, Query, HTTPException
from sqlalchemy import select, or_, cast, DateTime, func, String

import config
from src import jwt
from src.admin.schemas import *
from src.core import async_session_maker, CurrencyCore, WithdrawCore, BankCore, TopUpCore, UserCore
from src.models import Currency, Withdraw, TopUp, Bank, User

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


@router.get('/withdraws/')
async def withdraws(params: Annotated[Withdraws, Query()]) -> WithdrawsResponse:
    page, limit, statuses, bank_ids, sort_by, order, search, start_date, end_date = (
        params.page, params.limit, params.statuses, params.bank_ids, params.sort_by, params.order, params.search,
        params.start_date, params.end_date
    )

    query = select(Withdraw)

    if statuses:
        query = query.filter(Withdraw.status.in_(statuses))

    if bank_ids:
        query = query.filter(Withdraw.bank_id.in_(bank_ids))

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

    if sort_by in ["datetime", "amount_in_usd", "status", "amount"]:
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

    response = WithdrawsResponse(
        result=WithdrawsResponse.Result(
            withdraws=response_withdraws,
            meta=WithdrawsResponse.Meta(
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


@router.get("/withdraw/{withdraw_id}/")
async def withdraw(withdraw_id: int) -> WithdrawResponse:
    row = await WithdrawCore.find_one(id=withdraw_id)
    if row:
        return WithdrawResponse(
            result=row.__dict__
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


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

@router.patch('/withdraw/{withdraw_id}/')
async def update_tag(withdraw_id: int, data: WithdrawPatch) -> WithdrawResponse:
    try:
        data_to_update = {}
        for k, v in data.model_dump(exclude_none=True).items():
            data_to_update[k] = v
        if not data_to_update:
            raise HTTPException(400, {"ok": False, "error": "No parameters are passed"})
        updated_row = await WithdrawCore.patch(withdraw_id, **data_to_update)
        if updated_row:
            return WithdrawResponse(
                result=updated_row.__dict__
            )
        else:
            raise HTTPException(400, {"ok": False, "error": "Id not found"})
    except:
        raise HTTPException(500, {"ok": False, "error": "Some error"})


@router.get('/topups/')
async def topups(params: Annotated[TopUps, Query()]):
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

    response = TopUpsResponse(
        result=TopUpsResponse.Result(
            topups=response_topups,
            meta=TopUpsResponse.Meta(
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


@router.get("/topup/{topup_id}/")
async def topup(topup_id: int) -> TopUpResponse:
    row = await TopUpCore.find_one(id=topup_id)
    if row:
        return TopUpResponse(
            result=row.__dict__
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


@router.get('/users/')
async def users(ids: Annotated[List[int], Query(example=[12, 20])] = None):
    async with async_session_maker() as session:
        if not ids:
            query = select(User).order_by(User.id.asc())
        else:
            query = select(User).filter(User.id.in_(ids)).order_by(User.id.asc())
        result = await session.execute(query)
        user_rows = result.scalars().all()

    response = UsersResponse(
        result=[UserModel(**row.__dict__) for row in user_rows]
    )

    return response


@router.get("/user/{user_id}/")
async def user(user_id: int) -> UserResponse:
    row = await UserCore.find_one(id=user_id)
    if row:
        return UserResponse(
            result=row.__dict__
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


@router.get('/currencies/')
async def currencies(ids: Annotated[List[int], Query(example=[12, 20])] = None) -> CurrenciesResponse:
    async with async_session_maker() as session:
        if not ids:
            query = select(Currency).order_by(Currency.id.asc())
        else:
            query = select(Currency).filter(Currency.id.in_(ids)).order_by(Currency.id.asc())
        result = await session.execute(query)
        currency_rows = result.scalars().all()

    response = CurrenciesResponse(
        result=[CurrencyModel(**row.__dict__) for row in currency_rows]
    )

    return response


@router.get("/currency/{currency_id}/")
async def currency(currency_id: int) -> CurrencyResponse:
    row = await CurrencyCore.find_one(id=currency_id)
    if row:
        return CurrencyResponse(
            result=row.__dict__
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


@router.post('/currency/')
async def post_currency(input_currency: CurrencyPost) -> CurrencyResponse:
    try:
        new_row_id = await CurrencyCore.add(
            name=input_currency.name,
            code=input_currency.code,
            symbol=input_currency.symbol,
            percent=input_currency.percent,
            min_amount=input_currency.min_amount,
            commission_step=input_currency.commission_step
        )
    except sqlalchemy.exc.IntegrityError:
        raise HTTPException(400, {"ok": False, "error": "This name or code already exists"})

    currency_row = await CurrencyCore.find_one(id=new_row_id)

    if currency_row:
        return CurrencyResponse(
            result=CurrencyModel(**currency_row.__dict__)
        )
    else:
        raise HTTPException(500, {"ok": False, "error": "Some error"})


@router.patch("/currency/{currency_id}/")
async def patch_currency(currency_id: int, data: CurrencyPatch) -> CurrencyResponse:
    try:
        data_to_update = {}
        for k, v in data.model_dump(exclude_none=True).items():
            data_to_update[k] = v
        if not data_to_update:
            raise HTTPException(400, {"ok": False, "error": "No parameters are passed"})
        updated_row = await CurrencyCore.patch(currency_id, **data_to_update)
        if updated_row:
            return CurrencyResponse(
                result=updated_row.__dict__
            )
        else:
            raise HTTPException(400, {"ok": False, "error": "Id not found"})
    except:
        raise HTTPException(400, {"ok": False, "error": "Some error"})


@router.get("/banks/")
async def banks(ids: Annotated[List[int], Query(example=[12, 20])] = None):
    async with async_session_maker() as session:
        if not ids:
            query = select(Bank).order_by(Bank.id.asc())
        else:
            query = select(Bank).filter(Bank.id.in_(ids)).order_by(Bank.id.asc())
        result = await session.execute(query)
        banks_rows = result.scalars().all()

    response = BanksResponse(
        result=[BankModel(**row.__dict__) for row in banks_rows]
    )

    return response


@router.get("/bank/{bank_id}/")
async def bank(bank_id: int) -> BankResponse:
    row = await BankCore.find_one(id=bank_id)
    if row:
        return BankResponse(
            result=row.__dict__
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


@router.post("/bank/")
async def post_bank(data: BankPost) -> BankResponse:
    try:
        new_row_id = await BankCore.add(
            name=data.name,
            code=data.code,
        )
    except sqlalchemy.exc.IntegrityError:
        raise HTTPException(400, {"ok": False, "error": "This name or code already exists"})

    new_row = await BankCore.find_one(id=new_row_id)

    if new_row:
        return BankResponse(
            result=BankModel(**new_row.__dict__)
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Some error"})


@router.patch("/bank/{bank_id}/")
async def patch_bank(bank_id: int, data: BankPatch) -> BankResponse:
    try:
        data_to_update = {}
        for k, v in data.model_dump(exclude_none=True).items():
            data_to_update[k] = v
        if not data_to_update:
            raise HTTPException(400, {"ok": False, "error": "No parameters are passed"})
        updated_row = await BankCore.patch(bank_id, **data_to_update)
        if updated_row:
            return BankResponse(
                result=updated_row.__dict__
            )
        else:
            raise HTTPException(400, {"ok": False, "error": "Id not found"})
    except:
        raise HTTPException(400, {"ok": False, "error": "Some error"})
