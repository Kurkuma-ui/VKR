import pandas as pd
import sqlite3

class SignalFiler:
    def __init__(self, db_path='train_zone.db'):
        self.db_path = db_path

    def filter_and_save_best_signals(self, min_threshold=0.5, max_threshold=3.0):
        timeframes = ['h1', 'm5']
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for tf in timeframes:
                    print(f"\n{'='*10} Таймфрейм {tf.upper()} {'='*10}")

                    for side in ['long', 'short']:
                        # Источник: новые таблицы с правильными таргетами
                        source_table = f"data_train_std{side}_{tf}"
                        # Цель: чистые выборки для обучения
                        target_table = f"{side}_train_{tf}"
                        
                        try:
                            # 1. Загрузка данных
                            df = pd.read_sql(f"SELECT * FROM {source_table}", conn)
                        except Exception:
                            print(f"[-] Таблица {source_table} не найдена. Пропуск.")
                            continue

                        if df.empty or 'target_std' not in df.columns:
                            print(f"[-] Пропуск {source_table}: таблица пуста или нет колонки target_std.")
                            continue

                        # 2. Фильтрация в диапазоне (0.5 < target_std < 3.0)
                        # Теперь и для Long, и для Short значения должны быть выше 0.5, 
                        # так как Short таргет мы пересчитали как потенциальную прибыль.
                        initial_count = len(df)
                        df_final = df[
                            (df['target_std'] > min_threshold) & 
                            (df['target_std'] < max_threshold)
                        ].copy()

                        if df_final.empty:
                            print(f"[-] Для {tf} ({side}) не найдено сигналов в диапазоне [{min_threshold}, {max_threshold}].")
                            continue

                        # 3. Сохранение
                        # if_exists='replace' перезапишет таблицы long_train_h1 и т.д.
                        df_final.to_sql(target_table, conn, if_exists='replace', index=False)
                        
                        print(f"[+] {side.upper()}: Из {initial_count} строк отобрано {len(df_final)} качественных сигналов.")
                        print(f"    Записано в: {target_table}")

        except Exception as e:
            print(f"[-] Критическая ошибка: {e}")

if __name__ == "__main__":
    filterer = SignalFiler()
    # Запускаем фильтрацию с твоими границами
    filterer.filter_and_save_best_signals(min_threshold=0.5, max_threshold=3.0)