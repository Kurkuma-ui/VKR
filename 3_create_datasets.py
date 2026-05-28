import sqlite3
import pandas as pd
import config

def split_train_test_data(timeframe_settings):
    try:
        with sqlite3.connect('trading_data.db') as conn, \
             sqlite3.connect('train_zone.db') as Dconn:
            
            for tf, dates in timeframe_settings.items():
                source_table = f"tbl_indic_{tf}"
                train_table = f"data_train_{tf}"
                test_table = f"data_test_{tf}"
                
                print(f"[*] Обработка {tf.upper()} из {source_table}...")

                t_start = dates['train_start']
                t_end = dates['train_end']
                test_start = dates['test_start']
                test_end = dates['test_end']

                train_query = f"SELECT * FROM {source_table} WHERE timestamp >= ? AND timestamp <= ?"
                df_train = pd.read_sql_query(train_query, conn, params=(t_start, t_end))
            
                test_query = f"SELECT * FROM {source_table} WHERE timestamp >= ? AND timestamp <= ?"
                df_test = pd.read_sql_query(test_query, conn, params=(test_start, test_end))

                total_rows = len(df_train) + len(df_test)
                
                if total_rows == 0:
                    print(f"[-] Нет данных в {source_table} для указанных дат. Пропускаю.")
                    continue

                df_train.to_sql(train_table, Dconn, if_exists='replace', index=False)
                df_test.to_sql(test_table, Dconn, if_exists='replace', index=False)
            
                train_pct = (len(df_train) / total_rows) * 100
                test_pct = (len(df_test) / total_rows) * 100
            
                print(f"[+] Разделение для {tf.upper()} завершено!")
                print("-" * 40)
                print(f"  Период Train: {t_start} - {t_end}")
                print(f"  Обучающая выборка: {len(df_train)} строк | {train_pct:.1f}%")
                print(f"  Тестовая выборка : {len(df_test)} строк | {test_pct:.1f}%")
                print("-" * 40)
                print(f"Данные сохранены в '{train_table}' и '{test_table}' в train_zone.db\n")

    except Exception as e:
        print(f"[-] Произошла ошибка: {e}")

if __name__ == "__main__":
    timeframe_config = {
        'h1': {
            'train_start': '2025-01-01 00:00:00',
            'train_end':   '2025-12-31 23:59:59',
            'test_start':  '2026-01-01 00:00:00',
            'test_end':    '2026-04-03 23:00:00'
        },
        'm5': {
            'train_start': '2025-11-19 23:00:00',
            'train_end':   '2026-02-28 23:59:59',
            'test_start':  '2026-03-01 00:00:00',
            'test_end':    '2026-03-31 23:59:59'
        }
    }
    
    split_train_test_data(timeframe_config)