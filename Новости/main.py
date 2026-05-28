import logging
import requests
import config
from db_manager import DBManager
import os
import warnings

# Импортируем ваши классы
from get import NewsFetcher
from nlp_processor import SentimentProcessor
from SentimentManager import SentimentAggregator

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore", message=".*unexpected_keys.*")

# Настраиваем единый логгер для всего пайплайна
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Orchestrator")

def send_telegram_message(text: str):
    """Отправляет сообщение в Telegram через Bot API"""
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Уведомление в Telegram успешно отправлено.")
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")

def get_latest_metrics():
    """Извлекает последнюю запись агрегации из БД"""
    db = DBManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT calc_timestamp, current_mood, s3d_avg, s14d_avg, z_score 
            FROM tbl_sentiment_daily 
            ORDER BY id DESC LIMIT 1
        """)
        return cursor.fetchone()

def main():
    logger.info("=== Запуск пайплайна анализа сентимента ===")
    
    # Шаг 1: Сбор новостей
    logger.info("Шаг 1: Загрузка новостей...")
    fetcher = NewsFetcher()
    fetcher.fetch_and_save()
    
    # Шаг 2: Анализ тональности (FinBERT)
    logger.info("Шаг 2: ML Обработка сентимента...")
    processor = SentimentProcessor()
    processor.process_pending_news()
    
    # Шаг 3: Агрегация и расчет метрик
    logger.info("Шаг 3: Агрегация данных...")
    aggregator = SentimentAggregator(decay_lambda=0.05)
    aggregator.calculate_metrics()
    
    # Шаг 4: Уведомление в Telegram
    metrics = get_latest_metrics()
    if metrics:
        calc_timestamp, current_mood, s3d, s14d, z_score = metrics
        
        # Определяем визуальный тренд для частного трейдера
        trend_emoji = "🟢" if current_mood > 0 else "🔴" if current_mood < 0 else "⚪"
        z_warning = "⚠️ <b>АНОМАЛИЯ СЕНТИМЕНТА!</b>\n" if abs(z_score) > 2.0 else ""
        
        msg = (
            f"{z_warning}"
            f"📊 <b>Отчет по сентименту XAU/USD (Forex)</b>\n"
            f"🕒 {calc_timestamp}\n\n"
            f"{trend_emoji} <b>Текущее настроение:</b> {current_mood:.3f}\n"
            f"📅 <b>Взвешенное 3 дня:</b> {s3d:.3f}\n"
            f"📆 <b>Взвешенное 14 дней:</b> {s14d:.3f}\n"
            f"📉 <b>Z-Score (Отклонение):</b> {z_score:.2f}"
        )
        send_telegram_message(msg)
    else:
        logger.warning("Нет данных для отправки в Telegram.")
        
    logger.info("=== Пайплайн успешно завершен ===")

if __name__ == "__main__":
    main()