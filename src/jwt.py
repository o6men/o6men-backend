from datetime import datetime, UTC, timedelta
from typing import Union, Literal

import config

from jose import jwt, JWTError

from src.core import BaseCore
from src.models import User


def create_jwt_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=30)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, config.SECRET, 'HS256')
    return encode_jwt


async def decode_jwt_token(token: str) -> Union[int, str, Literal['incorrect_token', 'lifetime_expired', 'user_not_found']]:
    try:
        payload = jwt.decode(token, config.SECRET, 'HS256')
    except JWTError:
        return 'incorrect_token'

    expire = payload.get('exp')
    if expire:
        expire_time = datetime.fromtimestamp(int(expire), tz=UTC)
        if expire_time < datetime.now(UTC):
            return 'lifetime_expired'
    else:
        return 'lifetime_expired'

    user_id = payload.get('sub')
    if not user_id:
        return 'user_not_found'
    elif user_id == 'admin':
        return 'admin'

    core = BaseCore
    core.model = User
    user_db = await core.find_one(id=int(user_id))
    if not user_db:
        return 'user_not_found'

    return user_db.id