from typing import Any

from pydantic import BaseModel, Field, model_validator

class ResponseModel(BaseModel):
    ok: bool
    result: Any|None = Field(default=None, description="Result if success")
    error: Any|None = Field(default=None, description="Error if failed")

    @model_validator(mode='after')
    @classmethod
    def mutator(cls, obj: Any) -> Any:
        result = getattr(obj, "result", None)
        error = getattr(obj, "error", None)
        if result is None and error is None:
            raise ValueError("Cannot have both result and error")
        elif not result is None and not error is None:
            raise ValueError("Must have either result or error")

        return obj

