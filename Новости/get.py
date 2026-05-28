import requests
import logging
from datetime import datetime
import config 
from db_manager import DBManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NewsFetcher:
    def __init__(self):
        self.api_key = config.FINNHUB_API_KEY
        self.url = "https://finnhub.io/api/v1/company-news"
        self.symbol = "GLD"  # Золотой ETF как надежный источник макро-новостей по металлу
        self.db = DBManager()
        self._init_db()
        
        # Словарь ключевых слов для фильтрации рыночного шума
        self.keywords = ['gold', 'xau', 'gld', 'bullion', 'fed', 'inflation', 'precious', 'metals', 'commodity']

    def _init_db(self):
        with self.db.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tbl_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    title TEXT,
                    content TEXT,
                    url TEXT UNIQUE,
                    source_sentiment REAL DEFAULT 0.0,
                    sentiment_done INTEGER DEFAULT 0
                )
            ''')
            conn.commit()

    def fetch_and_save(self):
        # ИЗМЕНЕНО: Жестко задаем начало 2026 года в качестве стартовой точки
        today = datetime.now()
        from_date = "2026-01-01"
        to_date = today.strftime('%Y-%m-%d')
        
        logging.info(f"Запрос новостей напрямую из Finnhub с начала 2026 года ({from_date} -> {to_date})...")

        params = {
            "symbol": self.symbol,
            "from": from_date,
            "to": to_date,
            "token": self.api_key
        }

        try:
            response = requests.get(self.url, params=params, timeout=25)  # Увеличили timeout, так как данных будет больше
            
            if response.status_code == 429:
                logging.warning("Превышен лимит запросов API Finnhub (429). Повторите попытку позже.")
                return
                
            response.raise_for_status()
            feed = response.json()
        except Exception as e:
            logging.error(f"Ошибка при запросе к API Finnhub: {e}")
            return

        if not isinstance(feed, list) or not feed:
            logging.info("От API Finnhub не получено новостей за этот период.")
            return

        new_count = 0
        filtered_count = 0  # Счётчик отсеянного шума
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for item in feed:
                try:
                    # Переводим Unix timestamp от Finnhub в формат YYYY-MM-DD HH:MM:SS
                    dt = datetime.fromtimestamp(item["datetime"])
                    ts = dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    title = item.get("headline")
                    content = item.get("summary")
                    url = item.get("url")
                    
                    # Пропускаем пустые записи, если они прилетят
                    if not title or not url:
                        continue

                    # ФИЛЬТРАЦИЯ: Проверяем наличие ключевых слов в заголовке и контенте
                    text_to_check = f"{title} {content or ''}".lower()
                    if not any(word in text_to_check for word in self.keywords):
                        filtered_count += 1
                        continue  # Пропускаем новость, так как это нецелевой шум

                    # Если такой URL уже есть в БД, база его просто пропустит благодаря UNIQUE
                    cursor.execute("""
                        INSERT OR IGNORE INTO tbl_news (timestamp, title, content, url) 
                        VALUES (?, ?, ?, ?)
                    """, (ts, title, content, url))
                    
                    if cursor.rowcount > 0:
                        new_count += 1
                except Exception as ex:
                    logging.debug(f"Ошибка парсинга элемента новости: {ex}")
                    continue
            conn.commit()
        
        logging.info(f"Фильтрация завершена. Отсеяно нерелевантных новостей за 2026 год: {filtered_count}")
        logging.info(f"Успешно обработано. В базу добавлено {new_count} новых целевых новостей.")

if __name__ == "__main__":
    NewsFetcher().fetch_and_save()