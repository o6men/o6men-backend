from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

from src.schemas import ResponseModel


class DeleteResponse(ResponseModel):
    result: str

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
    role: str | None = None
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
    user: UserModel
    bank: BankModel
    currency: CurrencyModel
    document: int | None = None


class Withdraws(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1)
    statuses: List[Literal["completed", "waiting", "reject", "correction"]] | None = None
    bank_ids: List[int] | None = None
    currencies: List[int] | None = None
    sort_by: Literal["datetime", "amount"] = "datetime"
    order: Literal["asc", "desc"] = "desc"
    search: str | None = None
    start_date: datetime | None = Field(None,
                                        description="Start date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\")")
    end_date: datetime | None = Field(None,
                                      description="End date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\"")
    min_amount: float | None = None
    max_amount: float | None = None
    min_usdt_amount: float | None = None
    max_usdt_amount: float | None = None


class WithdrawsResponse(ResponseModel):
    class StatusSummary(BaseModel):
        total_count: int = Field(description="Общее количество элементов с этим статусом (без учёта фильтров)")
        total_filtered_count: int = Field(description="Количество элементов с этим статусом (с учётом фильтров)")
        page_count: int = Field(description="Количество элементов с этим статусом на текущей странице")

        total_amount: float = Field(description="Общая сумма для этого статуса (без учёта фильтров)")
        total_filtered_amount: float = Field(description="Сумма для этого статуса (с учётом фильтров)")
        page_amount: float = Field(description="Сумма для этого статуса на текущей странице")

        total_usdt_amount: float = Field(description="Общая сумма в USDT для этого статуса (без учёта фильтров)")
        total_filtered_usdt_amount: float = Field(description="Сумма в USDT для этого статуса (с учётом фильтров)")
        page_usdt_amount: float = Field(description="Сумма в USDT для этого статуса на текущей странице")

    class Meta(BaseModel):
        page: int = Field(description="Номер страницы")
        pages_count: int = Field(description="Количество страниц (с учётом фильтров)")
        limit: int = Field(description="Количество элементов на странице")
        completed: "WithdrawsResponse.StatusSummary"
        waiting: "WithdrawsResponse.StatusSummary"
        reject: "WithdrawsResponse.StatusSummary"
        correction: "WithdrawsResponse.StatusSummary"
        all: "WithdrawsResponse.StatusSummary"

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
    user: UserModel
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
    min_usdt_amount: float | None = None
    max_usdt_amount: float | None = None


class TopUpsResponse(ResponseModel):
    class Meta(BaseModel):
        page: int
        pages_count: int
        limit: int
        total_count: int
        total_filtered_count: int
        page_count: int
        total_usdt_amount: float
        total_filtered_usdt_amount: float
        page_usdt_amount: float

    class Result(BaseModel):
        topups: List[TopUpModel]
        meta: "TopUpsResponse.Meta"

    result: Result


class TopUpResponse(ResponseModel):
    result: TopUpModel = None