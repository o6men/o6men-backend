import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src import middlewares
from src.auth.router import router as auth_router
from src.routers.user import router as user_router
from src.routers.applications import router as application_router
from src.admin.router import router as admin_router
from src.telegram.bot import start_polling

# noinspection PyAsyncCall
@asynccontextmanager
async def lifespan(app: FastAPI):
    # await TgAuthTokenCore.delete()
    asyncio.create_task(start_polling())
    yield

app = FastAPI(lifespan=lifespan, root_path_in_servers=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["GET", 'POST', 'OPTIONS', 'DELETE', 'PATCH'],
    allow_headers=['*'],
)

app.middleware("http")(middlewares.allow_credentials)
app.middleware("http")(middlewares.check_auth)


class Item(BaseModel):
    hello: str = 'hello'

@app.get('/', tags=['Базовый адрес'])
async def main_page() -> Item:
    return Item()


app.include_router(auth_router, prefix='/auth')
app.include_router(user_router, prefix='/user')
app.include_router(application_router, prefix='/application')
app.include_router(admin_router, prefix='/admin')

if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)