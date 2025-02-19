from datetime import datetime, UTC
import re
from typing import Union

import aiogram
from aiogram import types as tgtypes, F, exceptions
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Filter
from aiogram.types import InlineKeyboardMarkup as IMarkup, InlineKeyboardButton as IButton, Message, CallbackQuery
from sqlalchemy.exc import SQLAlchemyError

import config
from src.core import UserCore, TgAuthTokenCore

bot = aiogram.Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode='html'))
dispatcher = aiogram.Dispatcher()

class PrivateF(Filter):
    async def __call__(self, update: Union[CallbackQuery, Message], *args, **kwargs):
        chat = update.chat if type(update) == Message else update.message.chat
        return chat.type == 'private'

class FullmatchF(Filter):
    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    async def __call__(self, update: Union[CallbackQuery, Message], *args, **kwargs):
        if type(update) == Message:
            text = update.text or update.caption or ''
        elif type(update) == CallbackQuery:
            text = update.data
        else:
            return False

        res = self.pattern.fullmatch(text)
        if res:
            return True
        else:
            return False

@dispatcher.message(PrivateF(), F.text and F.text[:6] == '/start')
async def start_message(message: Message):
    user = message.from_user

    db_user = await UserCore.find_one(tg_user_id=user.id)

    if not db_user:
        await UserCore.add(**{
            'tg_user_id': user.id,
            'first_name': user.first_name or 'noname',
            'tg_username': user.username,
        })


    await bot.send_message(
        chat_id=user.id,
        text=f"""
Привет, <b>{user.first_name}</b>, ты попал к o6men боту.
Ты можешь получить токен для входа или войти в веб-приложение: 
        """,
        reply_markup=IMarkup(inline_keyboard=[
            [IButton(text='Открыть приложение 👾', web_app=tgtypes.WebAppInfo(url=config.frontend_url))],
            [IButton(text='Получить токен 📜', callback_data='get_token')]]
        )
    )

@dispatcher.callback_query(PrivateF(), FullmatchF('get_token(_del_msg|)'))
async def callback_update(callback: CallbackQuery):
    user = callback.from_user
    db_user = await UserCore.find_one(tg_user_id=user.id)

    created_token = await TgAuthTokenCore.find_one(user_pk=db_user.id, order_type='desc')
    if not created_token or (created_token and created_token.end_at < datetime.now(UTC)):
        try:
            await TgAuthTokenCore.add(user_pk=db_user.id)
        # If there's a 1,52784834*10^47 chance of a match happening)
        except SQLAlchemyError:
            await TgAuthTokenCore.add(user_pk=db_user.id)

        created_token = await TgAuthTokenCore.find_one(user_pk=db_user.id, order_type='desc')

    await bot.send_message(
        chat_id=user.id,
        text=f'Ваш токен - <code>{created_token.token}</code>',
        reply_markup=IMarkup(inline_keyboard=[
            [IButton(text='Открыть приложение 👾', web_app=tgtypes.WebAppInfo(url=config.frontend_url))],
            [IButton(text='Получить токен 📜', callback_data='get_token_del_msg')]]
        )
    )
    if callback.data == 'get_token_del_msg':
        try:
            await bot.delete_message(
                chat_id=user.id,
                message_id=callback.message.message_id
            )
        except exceptions.TelegramBadRequest:
            pass

allowed_updates = ['message', 'callback_query']

async def start_polling():
    print(f'\033[32mINFO:\033[0m     BOT RUNNING')
    await dispatcher.start_polling(bot, polling_timeout=300, allowed_updates=allowed_updates, handle_signals=False)
