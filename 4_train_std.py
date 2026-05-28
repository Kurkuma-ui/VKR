import pandas as pd
import numpy as np
import sqlite3

class TargetBuilder:
    def __init__(self, db_path, source_db_path):
        self.db_path = db_path
        self.source_db_path = source_db_path

    def add_normalized_targets(self, timeframe_params):
        # Проходим по каждому таймфрейму (h1, m5)
        for tf, params in timeframe_params.items():
            lookahead = params['lookahead']
            window = params['window']
            
            # Базовая таблица с признаками
            source_table = f"data_train_{tf}"
            quotes_table = f"tbl_quotes_{tf}"
            
            # Для каждого ТФ делаем два прохода: для Long и для Short
            for direction in ['long', 'short']:
                target_table = f"data_train_std{direction}_{tf}"
                print(f"--- Обработка {target_table.upper()} (lookahead: {lookahead}) ---")

                try:
                    with sqlite3.connect(self.db_path) as Dconn:
                        Dconn.execute(f"ATTACH DATABASE '{self.source_db_path}' AS source_db")
                        
                        # Загружаем всё из тренировочной таблицы + котировки для расчёта таргета
                        query = f"""
                            SELECT t.*, q.close, q.tick_volume 
                            FROM {source_table} t
                            JOIN source_db.{quotes_table} q ON t.timestamp = q.timestamp
                            ORDER BY t.timestamp ASC
                        """
                        df = pd.read_sql(query, Dconn)

                    if df.empty:
                        print(f"[-] Данные не найдены для {target_table}.")
                        continue

                    # --- ЛОГИКА РАСЧЁТА ТАРГЕТА ---
                    if direction == 'long':
                        # Ищем максимум впереди (профит от покупки)
                        df['future_val'] = df['close'].shift(-lookahead).rolling(window=lookahead).max()
                        df['raw_return'] = (df['future_val'] - df['close']) / df['close'] * 100
                    else:
                        # Ищем минимум впереди (профит от продажи: точка входа - будущий минимум)
                        df['future_val'] = df['close'].shift(-lookahead).rolling(window=lookahead).min()
                        df['raw_return'] = (df['close'] - df['future_val']) / df['close'] * 100

                    # Z-score доходности (нормализация)
                    rolling_avg = df['raw_return'].rolling(window=window).mean()
                    rolling_std = df['raw_return'].rolling(window=window).std()
                    df['target_std'] = (df['raw_return'] - rolling_avg) / rolling_std

                    # Нормализация объема (vol_norm)
                    vol_avg = df['tick_volume'].rolling(window=window).mean()
                    vol_std = df['tick_volume'].rolling(window=window).std()
                    df['vol_norm'] = (df['tick_volume'] - vol_avg) / vol_std

                    # --- СОХРАНЕНИЕ ---
                    # Удаляем вспомогательные колонки перед сохранением, чтобы не дублировать close/volume
                    cols_to_drop = ['future_val', 'raw_return', 'tick_volume', 'close']
                    df_final = df.drop(columns=[c for c in cols_to_drop if c in df.columns])

                    with sqlite3.connect(self.db_path) as Dconn:
                        # Сохраняем в новую таблицу (например, data_train_stdlong_h1)
                        df_final.to_sql(target_table, Dconn, if_exists='replace', index=False)
                    
                    print(f"[+] Успешно создана таблица: {target_table} ({len(df_final)} строк)")

                except Exception as e:
                    print(f"[-] Ошибка при обработке {target_table}: {e}")

if __name__ == "__main__":
    builder = TargetBuilder(
        db_path='train_zone.db', 
        source_db_path='trading_data.db'
    )

    # Настройки горизонтов прогнозирования
    settings = {
        'h1': {
            'lookahead': 6, 
            'window': 100
        },
        'm5': {
            'lookahead': 12, # Для М5 можно взять чуть больше свечей вперед
            'window': 300
        }
    }

    builder.add_normalized_targets(timeframe_params=settings)