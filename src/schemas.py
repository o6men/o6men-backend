from typing import Any

from pydantic import BaseModel

class ResponseModel(BaseModel):
    ok: bool = True
    result: Any