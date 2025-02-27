from datetime import datetime
from typing import Any, List, Literal, Dict

from pydantic import BaseModel, Field, model_validator
from pydantic.json_schema import DEFAULT_REF_TEMPLATE, GenerateJsonSchema, JsonSchemaMode
from typing_extensions import Self

from config import BANKS
from src.models import User
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
    amount_in_usd: float
    tag: str = Field(description="Can be empty string")
    status: Literal['completed', 'waiting', 'reject', 'correction']
    datetime: datetime
    document: int|None = None

class GetWithdrawsInput(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1)
    statuses: List[Literal["completed", "waiting", "reject", "correction"]] | None = Field(None)
    banks: List[str] | None = Field(None)
    sort_by: Literal["datetime", "amount"] = "datetime"
    order: Literal["asc", "desc"] = "desc"
    search: str | None = Field(None)
    start_date: datetime|None = Field(None, description="Start date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\")")
    end_date: datetime|None = Field(None, description="End date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\"")

class GetWithdrawsResponse(ResponseModel):
    class Meta(BaseModel):
        page: int
        page_count: int
        limit: int
        total_withdraw_count: int
        page_withdraw_count: int
        total_amount_in_usd: float
        page_amount_in_usd: float

    class Result(BaseModel):
        withdraws: List[WithdrawModel]
        meta: "GetWithdrawsResponse.Meta"

    result: Result


class WithdrawUpdateTagInput(BaseModel):
    id: int
    tag: str

class WithdrawUpdateTagResponse(ResponseModel):
    result: Literal["Success"] = None

# topups

class TopUpModel(BaseModel):
    id: int
    user_id: int
    datetime: datetime
    transaction_hash: str
    amount: float
    amount_in_usd: float

class GetTopUpsInput(BaseModel):
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1)
    sort_by: Literal["datetime", "amount"] = "datetime"
    order: Literal["asc", "desc"] = "desc"
    search: str | None = Field(None)
    start_date: datetime|None = Field(None, description="Start date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\")")
    end_date: datetime|None = Field(None, description="End date in ISO 8601 format with timezone YYYY-MM-DDThh:mm:ss(\"±hh:mm\" or \"Z\"")

class GetTopUpsResponse(ResponseModel):
    class Meta(BaseModel):
        page: int
        page_count: int
        limit: int
        total_topup_count: int
        page_topup_count: int
        total_amount_in_usd: float
        page_amount_in_usd: float

    class Result(BaseModel):
        topups: List[TopUpModel]
        meta: "GetTopUpsResponse.Meta"

    result: Result


# get_currencies|create_currency
class CurrencyModel(BaseModel):
    id: int
    name: str
    code: str
    symbol: str
    rate: float|None
    percent: float
    min_amount: float
    commission_step: float

class GetCurrenciesResponse(ResponseModel):
    result: List[CurrencyModel] = None

class CreateCurrencyInput(BaseModel):
    name: str
    code: str
    symbol: str
    percent: float
    min_amount: float
    commission_step: float

class CreateCurrencyResponse(ResponseModel):
    result: CurrencyModel = None

# get_users

class UserModel(BaseModel):
    id: int
    first_name: str
    two_fa: bool
    tg_user_id: int
    tg_username: str|None
    role: str
    email: str|None
    registered_at: datetime
    photo_url: str|None
    tether_balance: float


class GetUsersResponse(ResponseModel):
    result: List[UserModel] = None

# get_banks

class BankModel(BaseModel):
    id: int
    name: str
    code: str

class GetBanksResponse(ResponseModel):
    result: List[BankModel] = None