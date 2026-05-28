import MetaTrader5 as mt5
import os

# --- Настройки подключения к MetaTrader 5 ---
MT5_LOGIN = 104583194
MT5_PASSWORD = "Z@1qZhHh"
MT5_SERVER = "MetaQuotes-Demo"

# --- Параметры базы данных ---
DB_NAME = "trading_data.db"

# --- Параметры торговой стратегии ---
SYMBOL = "EURUSD"

# --- Параметры моделей ---
BERT_MODEL_NAME = "ProsusAI/finbert"

# Настройки парсинга новостей (Режимы: 'REFILL' or 'LIVE')
NEWS_MODE = 'LIVE' 
NEWS_HISTORY_DAYS = 30

# База данных будет создана в той же папке, где запускается скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sentiment_dss.db")

# Настройки API
FINNHUB_API_KEY = "d38i8c9r01qlbdj5laggd38i8c9r01qlbdj5lah0"
NEWS_MODE = "LIVE"

# Настройки Telegram
TELEGRAM_BOT_TOKEN = "7528959517:AAFm1lXkJEPFEWPz28oXBjxJo11FNnPV1VA"
TELEGRAM_CHAT_ID = "1175766019"