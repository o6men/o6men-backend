import os

from dotenv import load_dotenv

load_dotenv()

DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('DB_PASS')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')

DB_URL = f'postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

BOT_TOKEN = os.environ.get('BOT_TOKEN')
SECRET = os.environ.get('SECRET')

TOKEN_LIFETIME = 12 # minutes

frontend_url = 'https://o6men.site/'

CRYPTOADDRESS = 'TEDepUJidzXfCkHtDmWhAPQiTibhiRE2C5'

ADMIN_TOKEN = '197685:DF3KijgREdqjzRFuylb0MTIh'

BANKS = {
    'tbank': 'ТБанк (Тинькофф)',
    'sber': 'Сбер',
    'alfa': 'Альфа'
}
