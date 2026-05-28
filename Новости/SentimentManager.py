import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from db_manager import DBManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SentimentAggregator:
    def __init__(self, decay_lambda=0.05):
        self.db = DBManager()
        self.decay_lambda = decay_lambda
        self._init_agg_db()

    def _init_agg_db(self):
        with self.db.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tbl_sentiment_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    calc_timestamp DATETIME,
                    current_mood REAL,
                    s3d_avg REAL,
                    s14d_avg REAL,
                    z_score REAL
                )
            ''')
            conn.commit()

    def calculate_metrics(self):
        # 1. Загружаем все обработанные новости в DataFrame
        with self.db.get_connection() as conn:
            query = "SELECT timestamp, source_sentiment FROM tbl_news WHERE sentiment_done = 1"
            df = pd.read_sql_query(query, conn)

        if df.empty:
            logging.warning("Нет данных для агрегации.")
            return

        df['timestamp'] = pd.to_datetime(df['timestamp'])
        now = datetime.now()

        # 2. Расчет Time Decay (t в часах)
        df['hours_ago'] = (now - df['timestamp']).dt.total_seconds() / 3600
        df['weight'] = np.exp(-self.decay_lambda * df['hours_ago'])
        
        # Взвешенный сентимент каждой новости
        df['weighted_sentiment'] = df['source_sentiment'] * df['weight']

        # 3. Текущий сентимент (среднее взвешенное)
        current_mood = df['weighted_sentiment'].sum() / df['weight'].sum()

        # 4. Расчет S3D и S14D (простые средние за периоды)
        three_days_ago = now - timedelta(days=3)
        fourteen_days_ago = now - timedelta(days=14)

        s3d = df[df['timestamp'] > three_days_ago]['source_sentiment'].mean()
        s14d = df[df['timestamp'] > fourteen_days_ago]['source_sentiment'].mean()

        # 5. Расчет Z-Score (относительно 14-дневного окна)
        # Показывает, является ли текущий всплеск аномальным
        std_14d = df[df['timestamp'] > fourteen_days_ago]['source_sentiment'].std()
        mean_14d = s14d
        
        # Защита от деления на ноль
        z_score = (current_mood - mean_14d) / std_14d if std_14d > 0 else 0

        # 6. Сохранение в базу
        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO tbl_sentiment_daily (calc_timestamp, current_mood, s3d_avg, s14d_avg, z_score)
                VALUES (?, ?, ?, ?, ?)
            """, (now.strftime('%Y-%m-%d %H:%M:%S'), 
                  float(current_mood), float(s3d), float(s14d), float(z_score)))
            conn.commit()

        logging.info(f"Агрегация завершена: Mood={current_mood:.3f}, Z={z_score:.2f}")

if __name__ == "__main__":
    aggregator = SentimentAggregator(decay_lambda=0.05)
    aggregator.calculate_metrics()