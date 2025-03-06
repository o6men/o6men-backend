from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

from src.schemas import ResponseModel


# withdraws
class WithdrawModel(BaseModel):
    id: int
    user_id: int
    phone: str
    card: str
    receiver: str = Field(description="Can be empty string")
    bank_id: int
    currency_id: int
    comment: str = Field(description="Can be empty string")
    amount: float
    usdt_amount: float
    tag: str = Field(description="Can be empty string")
    status: Literal['completed', 'waiting', 'reject', 'correction']
    datetime: datetime
    document: int | None = None


class Withdraws(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1)
    statuses: List[Literal["completed", "waiting", "reject", "correction"]] | None = Field(None)
    bank_ids: List[int] | None = Field(None)
    currencies: List[int] | None = Field(None)
    sort_by: Literal["datetime", "amount"] = "datetime"
    order: Literal["asc", "desc"] = "desc"
    search: str | None = Field(None)
    start_date: datetime | None = Field(None,
                                        description="Start date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\")")
    end_date: datetime | None = Field(None,
                                      description="End date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\"")


class WithdrawsResponse(ResponseModel):
    class Meta(BaseModel):
        page: int
        page_count: int
        limit: int
        total_withdraw_count: int
        page_withdraw_count: int
        usdt_total_amount: float
        usdt_page_amount: float

    class Result(BaseModel):
        withdraws: List[WithdrawModel]
        meta: "WithdrawsResponse.Meta"

    result: Result


class WithdrawPatch(BaseModel):
    user_id: int | None = None
    phone: str | None = None
    card: str | None = None
    receiver: str | None = None
    bank_id: int | None = None
    currency_id: int | None = None
    comment: str | None = None
    tag: str | None = None
    status: Literal["completed", "waiting", "reject", "correction"] | None = None


class WithdrawResponse(ResponseModel):
    result: WithdrawModel = None


# topups
class TopUpModel(BaseModel):
    id: int
    user_id: int
    datetime: datetime
    transaction_hash: str
    usdt_amount: float


class TopUps(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1)
    sort_by: Literal["datetime", "amount"] = "datetime"
    order: Literal["asc", "desc"] = "desc"
    search: str | None = Field(None)
    start_date: datetime | None = Field(None,
                                        description="Start date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\")")
    end_date: datetime | None = Field(None,
                                      description="End date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\"")


class TopUpsResponse(ResponseModel):
    class Meta(BaseModel):
        page: int
        page_count: int
        limit: int
        total_topup_count: int
        page_topup_count: int
        usdt_total_amount: float
        usdt_page_amount: float

    class Result(BaseModel):
        topups: List[TopUpModel]
        meta: "TopUpsResponse.Meta"

    result: Result


class TopUpResponse(ResponseModel):
    result: TopUpModel = None


# get_currencies|create_currency
class CurrencyModel(BaseModel):
    id: int
    name: str
    code: str
    symbol: str
    rate: float | None
    percent: float
    min_amount: float
    commission_step: float


class CurrenciesResponse(ResponseModel):
    result: List[CurrencyModel] = None


class CurrencyPost(BaseModel):
    name: str
    code: str
    symbol: str
    percent: float
    min_amount: float
    commission_step: float


class CurrencyPatch(BaseModel):
    name: str | None = None
    code: str | None = None
    symbol: str | None = None
    rate: float | None = None
    percent: float | None = None
    min_amount: float | None = None
    commission_step: float | None = None


class CurrencyResponse(ResponseModel):
    result: CurrencyModel = None


# get_users
class UserModel(BaseModel):
    id: int
    first_name: str
    two_fa: bool
    tg_user_id: int
    tg_username: str | None
    role: str
    email: str | None
    registered_at: datetime
    photo_url: str | None
    usdt_balance: float

class UserPatch(BaseModel):
    role: str|None = None
    usdt_balance: float | None = None


class UsersResponse(ResponseModel):
    result: List[UserModel] = None


class UserResponse(ResponseModel):
    result: UserModel = None


# get_banks
class BankModel(BaseModel):
    id: int
    name: str
    code: str


class BanksResponse(ResponseModel):
    result: List[BankModel] = None


class BankPost(BaseModel):
    name: str
    code: str


class BankPatch(BaseModel):
    name: str | None = None
    code: str | None = None


class BankResponse(BaseModel):
    result: BankModel = None
