import os
import shutil
import traceback

import sqlalchemy.exc
from PIL import Image
from fastapi import APIRouter, Body, Response, Query, HTTPException, UploadFile
from sqlalchemy import or_, cast, String, func
from fastapi.responses import FileResponse

from src import jwt
from src.admin.schemas import *
from src.core import *
from src.models import *

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
    page, limit, statuses, bank_ids, sort_by, order, search, start_date, end_date, min_amount, max_amount, min_usdt_amount, max_usdt_amount = (
        params.page, params.limit, params.statuses, params.bank_ids, params.sort_by, params.order, params.search,
        params.start_date, params.end_date, params.min_amount, params.max_amount, params.min_usdt_amount,
        params.max_usdt_amount
    )

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

    if statuses:
        query = query.filter(Withdraw.status.in_(statuses))

    if bank_ids:
        query = query.filter(Withdraw.bank_id.in_(bank_ids))

    if search:
        search = search.lower()
        query = query.filter(
            or_(
                cast(Withdraw.id, String).ilike(f'%{search}%'),
                cast(func.round(Withdraw.usdt_amount, 2), String).ilike(f'%{search}%'),
                cast(func.round(Withdraw.amount, 2), String).ilike(f'%{search}%'),
                func.to_char(Withdraw.datetime, 'YYYY-MM-DD HH24:MI:SS').ilike(f'%{search}%'),
                cast(Withdraw.phone, String).ilike(f'%{search}%'),
                cast(Withdraw.card, String).ilike(f'%{search}%'),
                cast(Withdraw.comment, String).ilike(f'%{search}%'),
                cast(Withdraw.tag, String).ilike(f'%{search}%'),
                cast(Withdraw.receiver, String).ilike(f'%{search}%'),
                User.tg_username.ilike(f'%{search}%'),
                Bank.name.ilike(f'%{search}%'),
                Currency.name.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
            )
        )

    if start_date:
        query = query.filter(cast(Withdraw.datetime, DateTime(timezone=True)) >= start_date)

    if end_date:
        query = query.filter(cast(Withdraw.datetime, DateTime(timezone=True)) <= end_date)

    if min_amount:
        query = query.filter(Withdraw.amount >= min_amount)

    if max_amount:
        query = query.filter(Withdraw.amount <= max_amount)

    if min_usdt_amount:
        query = query.filter(Withdraw.usdt_amount >= min_usdt_amount)

    if max_usdt_amount:
        query = query.filter(Withdraw.usdt_amount <= max_usdt_amount)

    meta_dict = {
        "page": page,
        "pages_count": 0,
        "limit": limit,
        "completed": {},
        "waiting": {},
        "reject": {},
        "correction": {},
        "all": {}
    }

    for status in ("completed", "waiting", "reject", "correction", "all"):
        meta_dict[status] = {
            "total_count": 0,
            "total_filtered_count": 0,
            "page_count": 0,
            "total_amount": 0,
            "total_filtered_amount": 0,
            "page_amount": 0,
            "total_usdt_amount": 0,
            "total_filtered_usdt_amount": 0,
            "page_usdt_amount": 0,
        }
    async with async_session_maker() as session:
        filtered_subquery = query.subquery()
        meta_filtered_result = await session.execute(select(
            func.count().filter(filtered_subquery.c.status == "completed").label("completed_count"),
            func.count().filter(filtered_subquery.c.status == "waiting").label("waiting_count"),
            func.count().filter(filtered_subquery.c.status == "reject").label("reject_count"),
            func.count().filter(filtered_subquery.c.status == "correction").label("correction_count"),

            func.sum(filtered_subquery.c.usdt_amount).filter(filtered_subquery.c.status == "completed").label(
                "completed_usdt_amount"),
            func.sum(filtered_subquery.c.usdt_amount).filter(filtered_subquery.c.status == "waiting").label(
                "waiting_usdt_amount"),
            func.sum(filtered_subquery.c.usdt_amount).filter(filtered_subquery.c.status == "reject").label(
                "reject_usdt_amount"),
            func.sum(filtered_subquery.c.usdt_amount).filter(filtered_subquery.c.status == "correction").label(
                "correction_usdt_amount"),

            func.sum(filtered_subquery.c.amount).filter(filtered_subquery.c.status == "completed").label(
                "completed_amount"),
            func.sum(filtered_subquery.c.amount).filter(filtered_subquery.c.status == "waiting").label(
                "waiting_amount"),
            func.sum(filtered_subquery.c.amount).filter(filtered_subquery.c.status == "reject").label("reject_amount"),
            func.sum(filtered_subquery.c.amount).filter(filtered_subquery.c.status == "correction").label(
                "correction_amount"),

            func.count().label("all_count"),
            func.sum(filtered_subquery.c.amount).label("all_filtered_amount"),
            func.sum(filtered_subquery.c.usdt_amount).label("all_filtered_usdt_amount"),
        ))

        total_meta_keys = meta_filtered_result.keys()
        total_meta_values = meta_filtered_result.one()
        for i, key in enumerate(total_meta_keys):
            split = key.split("_")
            type_ = split[0]
            field = "total_filtered_" + (split[1] if len(split) == 2 else (split[1] + "_" + split[2]))
            meta_dict[type_][field] = total_meta_values[i] if total_meta_values[i] else 0

    meta_dict["pages_count"] = (meta_dict["all"]["total_filtered_count"] + limit - 1) // limit

    if sort_by in ["datetime", "usdt_amount", "status", "amount", "id"]:
        if order == "desc":
            query = query.order_by(getattr(Withdraw, sort_by).desc())
        else:
            query = query.order_by(getattr(Withdraw, sort_by))

    query = query.offset((page - 1) * limit).limit(limit)

    async with async_session_maker() as session:
        meta_result = await session.execute(
            select(
                func.count().filter(Withdraw.status == "completed").label("completed_count"),
                func.count().filter(Withdraw.status == "waiting").label("waiting_count"),
                func.count().filter(Withdraw.status == "reject").label("reject_count"),
                func.count().filter(Withdraw.status == "correction").label("correction_count"),

                func.sum(Withdraw.usdt_amount).filter(Withdraw.status == "completed").label("completed_usdt_amount"),
                func.sum(Withdraw.usdt_amount).filter(Withdraw.status == "waiting").label("waiting_usdt_amount"),
                func.sum(Withdraw.usdt_amount).filter(Withdraw.status == "reject").label("reject_usdt_amount"),
                func.sum(Withdraw.usdt_amount).filter(Withdraw.status == "correction").label("correction_usdt_amount"),

                func.sum(Withdraw.amount).filter(Withdraw.status == "completed").label("completed_amount"),
                func.sum(Withdraw.amount).filter(Withdraw.status == "waiting").label("waiting_amount"),
                func.sum(Withdraw.amount).filter(Withdraw.status == "reject").label("reject_amount"),
                func.sum(Withdraw.amount).filter(Withdraw.status == "correction").label("correction_amount"),

                func.count().label("all_count"),
                func.sum(Withdraw.amount).label("all_amount"),
                func.sum(Withdraw.usdt_amount).label("all_usdt_amount"),
            )
        )
        total_meta_keys = meta_result.keys()
        total_meta_values = meta_result.one()
        for i, key in enumerate(total_meta_keys):
            split = key.split("_")
            type_ = split[0]
            field = "total_" + (split[1] if len(split) == 2 else (split[1] + "_" + split[2]))
            meta_dict[type_][field] = total_meta_values[i] if total_meta_values[i] else 0

        result = await session.execute(query)
        withdraw_list = result.all()

    response_withdraws = []

    for withdraw_row, user_row, bank_row, currency_row in withdraw_list:
        meta_dict[withdraw_row.status]["page_count"] += 1
        meta_dict[withdraw_row.status]["page_amount"] += withdraw_row.amount
        meta_dict[withdraw_row.status]["page_usdt_amount"] += withdraw_row.usdt_amount
        meta_dict["all"]["page_count"] += 1
        meta_dict["all"]["page_amount"] += withdraw_row.amount
        meta_dict["all"]["page_usdt_amount"] += withdraw_row.usdt_amount

        response_withdraws.append(WithdrawModel(
            user=UserModel(**user_row.__dict__),
            bank=BankModel(**bank_row.__dict__),
            currency=CurrencyModel(**currency_row.__dict__),
            **withdraw_row.__dict__
        ))

    response = WithdrawsResponse(
        result=WithdrawsResponse.Result(
            withdraws=response_withdraws,
            meta=WithdrawsResponse.Meta(**meta_dict)
        )
    )

    return response


@router.get("/withdraw/{withdraw_id}/")
async def withdraw(withdraw_id: int) -> WithdrawResponse:
    row = await WithdrawCore.find_one(id=withdraw_id)
    if row:
        withdraw_row, user_row, bank_row, currency_row = row
        return WithdrawResponse(
            result=WithdrawModel(user=user_row.__dict__, bank=bank_row.__dict__, currency=currency_row.__dict__,
                                 **withdraw_row.__dict__)
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


@router.patch('/withdraw/{withdraw_id}/')
async def withdraw_update(withdraw_id: int, data: WithdrawPatch) -> WithdrawResponse:
    data_to_update = {}
    for k, v in data.model_dump(exclude_none=True).items():
        data_to_update[k] = v
    if not data_to_update:
        raise HTTPException(400, {"ok": False, "error": "No parameters are passed"})
    updated_row = await WithdrawCore.patch(withdraw_id, **data_to_update)
    if updated_row:
        withdraw_row, user_row, bank_row, currency_row = updated_row
        return WithdrawResponse(
            result=WithdrawModel(user=user_row.__dict__, bank=bank_row.__dict__, currency=currency_row.__dict__,
                                 **withdraw_row.__dict__)
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Id not found"})


@router.delete('/withdraw/{withdraw_id}/')
async def withdraw_delete(withdraw_id: int) -> DeleteResponse:
    deleted_row = await WithdrawCore.delete(id=withdraw_id)
    if deleted_row:
        return DeleteResponse(ok=True, result=f"Withdraw {withdraw_id} deleted successfully")
    else:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})


@router.post('/withdraw/{withdraw_id}/document/')
async def withdraw_post_document(withdraw_id: int, file: UploadFile) -> WithdrawResponse:
    rows = await WithdrawCore.find_one(id=withdraw_id)
    if not rows:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})
    if rows[0].document:
        os.remove("files/" + rows[0].document)
    file_extension = file.filename.split(".")[-1]
    if file_extension not in ("png", "jpg", "jpeg", "pdf"):
        raise HTTPException(404, {"ok": False, "error": "Unsupported file type"})
    file_name = f"withdraw_{withdraw_id}.{file_extension}"

    # Сохраняем файл на диск
    with open("files/" + file_name, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = await WithdrawCore.patch(withdraw_id, document=file_name)

    withdraw_row, user_row, bank_row, currency_row = result

    return WithdrawResponse(
        result=WithdrawModel(user=user_row.__dict__, bank=bank_row.__dict__, currency=currency_row.__dict__,
                             **withdraw_row.__dict__)
    )


@router.get('/withdraw/{withdraw_id}/document/')
async def withdraw_get_document(withdraw_id: int) -> FileResponse:
    withdraw_row = await WithdrawCore.find_one(id=withdraw_id)
    if not withdraw_row:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})
    elif not withdraw_row[0].document:
        raise HTTPException(404, {"ok": False, "error": "Withdraw does not have a document"})
    elif not os.path.exists("files/" + withdraw_row[0].document):
        await WithdrawCore.patch(id=withdraw_id, document=None)
        raise HTTPException(404, {"ok": False, "error": "Withdraw does not have a document"})

    return FileResponse("files/" + withdraw_row[0].document, filename=withdraw_row[0].document)


@router.delete('/withdraw/{withdraw_id}/document/')
async def withdraw_delete_document(withdraw_id: int) -> ResponseModel:
    withdraw_row = await WithdrawCore.find_one(id=withdraw_id)
    if not withdraw_row:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})
    elif not withdraw_row[0].document:
        raise HTTPException(404, {"ok": False, "error": "Withdraw does not have a document"})

    await WithdrawCore.patch(id=withdraw_id, document=None)
    if os.path.exists("files/" + withdraw_row[0].document):
        os.remove("files/" + withdraw_row[0].document)

    return ResponseModel(result="Success")


@router.get('/topups/')
async def topups(params: Annotated[TopUps, Query()]):
    page, limit, sort_by, order, search, start_date, end_date, min_usdt_amount, max_usdt_amount = (
        params.page, params.limit, params.sort_by, params.order, params.search,
        params.start_date, params.end_date, params.min_usdt_amount, params.max_usdt_amount
    )

    query = select(
        TopUp,
        User
    ).join(
        User, User.id == TopUp.user_id
    )

    if search:
        search = search.lower()
        query = query.filter(
            or_(
                cast(TopUp.id, String).ilike(f'%{search}%'),
                cast(func.round(TopUp.usdt_amount, 2), String).ilike(f'%{search}%'),
                func.to_char(TopUp.datetime, 'YYYY-MM-DD HH24:MI:SS').ilike(f'%{search}%'),
                User.tg_username.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
            )
        )

    if start_date:
        query = query.filter(cast(TopUp.datetime, DateTime(timezone=True)) >= start_date)

    if end_date:
        query = query.filter(cast(TopUp.datetime, DateTime(timezone=True)) <= end_date)

    if min_usdt_amount:
        query = query.filter(TopUp.usdt_amount >= min_usdt_amount)

    if max_usdt_amount:
        query = query.filter(TopUp.usdt_amount <= max_usdt_amount)

    meta_dict = {
        "page": page,
        "pages_count": 0,
        "limit": limit,
        "total_count": 0,
        "total_filtered__count": 0,
        "page_count": 0,
        "total_usdt_amount": 0,
        "total_filtered_usdt_amount": 0,
        "page_usdt_amount": 0
    }

    async with async_session_maker() as session:
        filtered_subquery = query.subquery()

        meta_dict["total_filtered_count"] = await session.scalar(
            select(func.count()).select_from(filtered_subquery)
        ) or 0

        meta_dict["total_filtered_usdt_amount"] = await session.scalar(
            select(func.sum(filtered_subquery.c.usdt_amount))
        ) or 0

    if sort_by in ["datetime", "usdt_amount", "id"]:
        if order == "desc":
            query = query.order_by(getattr(TopUp, sort_by).desc())
        else:
            query = query.order_by(getattr(TopUp, sort_by))

    query = query.offset((page - 1) * limit).limit(limit)

    async with async_session_maker() as session:
        meta_dict["total_count"] = await session.scalar(select(func.count()).select_from(TopUp)) or 0
        meta_dict["total_usdt_amount"] = await session.scalar(
            select(func.sum(TopUp.usdt_amount)).select_from(TopUp)) or 0

        result = await session.execute(query)
        topup_list = result.all()

    response_topups = []

    meta_dict["pages_count"] = (meta_dict["total_filtered_count"] + limit - 1) // limit

    for topup_row, user_row in topup_list:
        meta_dict["page_count"] += 1
        meta_dict["page_usdt_amount"] += topup_row.usdt_amount
        response_topups.append(TopUpModel(
            user=UserModel(**user_row.__dict__),
            **topup_row.__dict__
        ))

    response = TopUpsResponse(
        result=TopUpsResponse.Result(
            topups=response_topups,
            meta=meta_dict
        )
    )

    return response


@router.get("/topup/{topup_id}/")
async def topup(topup_id: int) -> TopUpResponse:
    query = select(TopUp, User).join(User, User.id == TopUp.user_id).filter(TopUp.id == topup_id)
    async with async_session_maker() as session:
        result = await session.execute(query)
        topup_row, user_row = result.first()
    if topup_row:
        return TopUpResponse(
            result=TopUpModel(
                user=UserModel(**user_row.__dict__),
                **topup_row.__dict__
            )
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


@router.get('/users/')
async def users(ids: Annotated[List[int], Query(example=[1, 2])] = None):
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


@router.patch("/user/{user_id}/")
async def user_patch(user_id: int, data: UserPatch) -> UserResponse:
    data_to_update = {}
    for k, v in data.model_dump(exclude_none=True).items():
        data_to_update[k] = v
    if not data_to_update:
        raise HTTPException(400, {"ok": False, "error": "No parameters are passed"})
    updated_row = await UserCore.patch(user_id, **data_to_update)
    if updated_row:
        return UserResponse(
            result=updated_row.__dict__
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Id not found"})


@router.get('/currencies/')
async def currencies(ids: Annotated[List[int], Query(example=[1, 2])] = None) -> CurrenciesResponse:
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
async def currency_get(currency_id: int) -> CurrencyResponse:
    row = await CurrencyCore.find_one(id=currency_id)
    if row:
        return CurrencyResponse(
            result=row.__dict__
        )
    else:
        raise HTTPException(400, {"ok": False, "error": "Not found"})


@router.post('/currency/')
async def currency_post(input_currency: CurrencyPost) -> CurrencyResponse:
    try:
        new_row_id = await CurrencyCore.add(
            name=input_currency.name,
            code=input_currency.code,
            symbol=input_currency.symbol,
            min_amount=input_currency.min_amount,
            rate=input_currency.rate,
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
async def currency_post(currency_id: int, data: CurrencyPatch) -> CurrencyResponse:
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


@router.delete("/currency/{currency_id}/")
async def currency_delete(currency_id: int) -> DeleteResponse:
    deleted_row = await CurrencyCore.delete(id=currency_id)
    if deleted_row:
        return DeleteResponse(ok=True, result=f"Currency {deleted_row} deleted successfully")
    else:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})


@router.get("/currency/{currency_id}/commission_steps/")
async def commissions_get(currency_id: int) -> CommissionStepsResponse:
    currency = await CurrencyCore.find_one(id=currency_id)
    if not currency:
        raise HTTPException(404, {"ok": False, "error": "Currency not found"})
    steps = await CommissionCore.find_all(currency_id=currency_id)
    return CommissionStepsResponse(result=[CommissionStepModel(**i.__dict__) for i in steps])


@router.get("/commission_step/{commission_id}/")
async def commission_get(commission_id: int) -> CommissionStepResponse:
    commission_step = await CommissionCore.find_one(id=commission_id)
    if not commission_step:
        raise HTTPException(404, {"ok": False, "error": "Commission not found"})
    step = await CommissionCore.find_one(id=commission_id)
    return CommissionStepResponse(result=CommissionStepModel(**step.__dict__))


@router.post("/currency/{currency_id}/commission_step/")
async def commission_post(currency_id: int, input_c_step: CommissionStepPost) -> CommissionStepModel:
    new_row_id = await CommissionCore.add(**input_c_step.__dict__, currency_id=currency_id, currency_type="currency")

    commission_row = await CommissionCore.find_one(id=new_row_id)

    if commission_row:
        return CommissionStepModel(**commission_row.__dict__)
    else:
        raise HTTPException(500, {"ok": False, "error": "Some error"})


@router.patch("/commission_step/{commission_id}/")
async def commissions_patch(commission_id: int, data: CommissionStepPatch) -> CommissionStepResponse:
    commission_step = await CommissionCore.find_one(id=commission_id)
    if not commission_step:
        raise HTTPException(404, {"ok": False, "error": "Commission not found"})
    data_to_update = {}
    for k, v in data.model_dump(exclude_none=True).items():
        data_to_update[k] = v
    step = await CommissionCore.patch(id=commission_id, **data_to_update)
    return CommissionStepResponse(result=CommissionStepModel(**step.__dict__))


@router.delete("commission_step/{commission_id}/")
async def commissions_delete(commission_id: int) -> DeleteResponse:
    deleted_row = await CommissionCore.delete(id=commission_id)
    if deleted_row:
        return DeleteResponse(ok=True, result=f"Commission step {deleted_row} deleted successfully")
    else:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})


@router.get("/banks/")
async def banks(ids: Annotated[List[int], Query(example=[1, 2])] = None):
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
async def bank_post(data: BankPost) -> BankResponse:
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
async def bank_patch(bank_id: int, data: BankPatch) -> BankResponse:
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


@router.post('/bank/{bank_id}/icon/')
async def bank_post_icon(bank_id: int, file: UploadFile) -> BankResponse:
    rows = await BankCore.find_one(id=bank_id)
    if not rows:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})
    if rows.icon:
        os.remove("files/" + rows.icon)
    file_extension = file.filename.split(".")[-1]
    if file_extension not in ("png", "jpg", "jpeg"):
        raise HTTPException(404, {"ok": False, "error": "Unsupported file type"})
    file_name = f"bank_{bank_id}.{file_extension}"
    original_path = "files/" + file_name
    with open(original_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    resized_paths = {}
    for size in [32, 64, 128, 256]:
        img = Image.open(original_path)
        img = img.convert("RGBA")  # Для прозрачности, если нужно
        img = img.resize((size, size), Image.Resampling.LANCZOS)

        resized_name = f"bank_{bank_id}_{size}x{size}.png"
        resized_path = f"files/{resized_name}"
        img.save(resized_path, format="PNG")
        resized_paths[f"{size}x{size}"] = resized_name

    bank_row = await BankCore.patch(bank_id, icon=resized_paths["64x64"])

    return BankResponse(
        result=BankModel(**bank_row.__dict__)
    )


@router.delete("/bank/{bank_id}/")
async def bank_delete(bank_id: int) -> DeleteResponse:
    deleted_row = await BankCore.delete(id=bank_id)
    if deleted_row:
        return DeleteResponse(ok=True, result=f"Bank {deleted_row} deleted successfully")
    else:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})


@router.get('/bank/{bank_id}/icon/')
async def bank_get_icon(bank_id: int) -> FileResponse:
    bank_row: Bank = await BankCore.find_one(id=bank_id)
    if not bank_row:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})
    elif not bank_row.icon:
        raise HTTPException(404, {"ok": False, "error": "Bank does not have a icon"})
    elif not os.path.exists("files/" + bank_row.icon):
        await BankCore.patch(id=bank_id, icon=None)
        raise HTTPException(404, {"ok": False, "error": "Bank does not have a icon"})

    if not bank_row.icon:
        raise HTTPException(404, {"ok": False, "error": "Bank does not have a icon"})

    return FileResponse("files/" + bank_row.icon, filename=bank_row.icon)


@router.delete('/bank/{bank_id}/icon/')
async def bank_delete_icon(bank_id: int) -> ResponseModel:
    bank_row: Bank = await BankCore.find_one(id=bank_id)
    if not bank_row:
        raise HTTPException(404, {"ok": False, "error": "Id not found"})
    elif not bank_row.icon:
        raise HTTPException(404, {"ok": False, "error": "Bank does not have a icon"})

    await BankCore.patch(id=bank_id, icon=None)
    if os.path.exists("files/" + bank_row.icon):
        os.remove("files/" + bank_row.icon)

    return ResponseModel(result="Success")
