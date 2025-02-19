from fastapi import Request
from fastapi.responses import JSONResponse

from src.jwt import decode_jwt_token

async def allow_credentials(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

async def check_auth(request: Request, call_next):
    if request.method == 'OPTIONS':
        return await call_next(request)
    if request['path'] == '/auth/check_token/':
        if (await request.json()).get('token'):
            return await call_next(request)
    elif request['path'] == '/auth/check_auth/':
        return await call_next(request)
    elif request['path'] == '/admin/auth/':
        if (await request.json()).get('token'):
            print(1)
            return await call_next(request)

    if request['path'][:6] == '/admin':
        token = request.cookies.get('admin_access_token')
    else:
        token = request.cookies.get('user_access_token')
    if not token:
        return JSONResponse({'detail': 'unauthorized'}, status_code=401)
    result = await decode_jwt_token(token)
    if type(result) == str:
        if result != 'admin':
            return JSONResponse({'detail': 'unauthorized'}, status_code=401)

    request.state.user_id = result

    return await call_next(request)
