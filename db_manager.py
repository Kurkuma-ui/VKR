import sqlite3
import pandas as pd
import os

class DBManager:
    def __init__(self, db_path="trading_data.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        """Создает подключение к базе данных."""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Инициализация таблиц для разных таймфреймов."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Создаем таблицы для M5 и H1 отдельно
            # Это значительно ускорит выборку данных для обучения
            for suffix in ['m5', 'h1']:
                table_name = f"tbl_quotes_{suffix}"
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        timestamp DATETIME,
                        symbol TEXT,
                        open REAL,
                        high REAL,
                        low REAL,
                        close REAL,
                        tick_volume INTEGER,
                        PRIMARY KEY (timestamp, symbol)
                    )
                ''')
            
            # Таблица новостей (оставляем как была, она общая)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tbl_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME,
                    headline TEXT,
                    sentiment_score REAL DEFAULT 0,
                    asset_tag TEXT,
                    UNIQUE(timestamp, headline)
                )
            ''')
            
            # Таблица признаков (Features)
            # Добавим колонку для хранения типа ТФ, на основе которого считались признаки
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tbl_features (
                    timestamp DATETIME,
                    timeframe TEXT,
                    ema_200 REAL,
                    fvg_signal INTEGER,
                    sentiment_score REAL,
                    target REAL,
                    PRIMARY KEY (timestamp, timeframe)
                )
            ''')
            conn.commit()
        print(f"База данных оптимизирована под MTF: {os.path.abspath(self.db_path)}")

    def save_quotes(self, df, table_name):
        """
        Сохранение котировок в указанную таблицу.
        table_name: 'tbl_quotes_m5' или 'tbl_quotes_h1'
        """
        if df.empty:
            print(f"Ошибка: Попытка сохранить пустой DataFrame в {table_name}!")
            return

        # Убираем колонку 'timeframe', если она есть в DF, так как имя таблицы уже говорит о ТФ
        if 'timeframe' in df.columns:
            df = df.drop(columns=['timeframe'])

        with self.get_connection() as conn:
            try:
                # Используем метод 'INSERT OR REPLACE' через SQL, чтобы не плодить дубликаты
                # Но для скорости в Pandas используем to_sql с chunksize
                df.to_sql(table_name, conn, if_exists='append', index=False, method='multi', chunksize=500)
                conn.commit()
                print(f"[DB] {len(df)} строк записано в {table_name}")
            except sqlite3.IntegrityError:
                # Если попались дубликаты по Primary Key, игнорируем их
                pass
            except Exception as e:
                print(f"Критическая ошибка при записи в {table_name}: {e}")

    def save_news(self, timestamp, headline, sentiment, asset):
        """Сохранение новости."""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO tbl_news (timestamp, headline, sentiment_score, asset_tag)
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, headline, sentiment, asset))
        except Exception as e:
            print(f"Ошибка при сохранении новости: {e}")

    def get_last_quote_time(self, symbol, table_name):
        """Узнать время последней записи в конкретной таблице."""
        try:
            with self.get_connection() as conn:
                res = conn.execute(
                    f"SELECT MAX(timestamp) FROM {table_name} WHERE symbol=?", 
                    (symbol,)
                ).fetchone()
                return res[0] if res[0] else None
        except Exception:
            return None
        
    def save_features(self, df, timeframe):
        """Сохранение рассчитанных признаков в общую таблицу."""
        if df.empty: return
        
        df['timeframe'] = timeframe
        with self.get_connection() as conn:
            # Используем replace, чтобы при пересчете истории данные обновлялись
            df.to_sql('tbl_features', conn, if_exists='append', index=False, method='multi', chunksize=500)

    def recreate_features_table(self):
        """Пересоздает таблицу признаков с правильной структурой."""
        with self.get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS tbl_features")
            conn.execute('''
                CREATE TABLE tbl_features (
                    timestamp DATETIME,
                    symbol TEXT,
                    timeframe TEXT,
                    ema_200 REAL,
                    ema_50 REAL,
                    dist_ema_200 REAL,
                    atr REAL,
                    bb_width REAL,
                    rsi REAL,
                    adx REAL,
                    roc REAL,
                    slope REAL,
                    channel_pos REAL,
                    z_score REAL,
                    skew REAL,
                    kurt REAL,
                    PRIMARY KEY (timestamp, symbol, timeframe)
                )
            ''')
            conn.commit()
        print("[DB] Таблица tbl_features пересоздана.")

    def get_first_quote_time(self, symbol, table_name):
        """Возвращает время самой первой (старой) свечи в таблице"""
        query = f"SELECT MIN(timestamp) FROM {table_name} WHERE symbol = ?"
        try:
            with self.get_connection() as conn:
                res = conn.execute(query, (symbol,)).fetchone()
                return res[0] if res and res[0] else None
        except Exception as e:
            print(f"[-] Ошибка при получении первой даты: {e}")
            return None

if __name__ == "__main__":
    db = DBManager()
    db.recreate_features_table()