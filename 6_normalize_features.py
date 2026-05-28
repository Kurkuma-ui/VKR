import pandas as pd
import sqlite3
import numpy as np
import json
import os

class FeatureNormalizer:
    def __init__(self, db_path='train_zone.db', params_file='scaling_params.json'):
        self.db_path = db_path
        self.params_file = params_file
        self.scaling_params = {} # Здесь будем копить mean и std

    def normalize_features(self, timeframes=['h1', 'm5']):
        try:
            with sqlite3.connect(self.db_path) as conn:
                for tf in timeframes:
                    # Обрабатываем обе таблицы: и лонги, и шорты
                    for side in ['long', 'short']:
                        table_name = f"{side}_train_{tf}"
                        print(f"\n{'-'*20} [Обработка: {table_name.upper()}] {'-'*20}")
                        
                        # 1. Загружаем данные
                        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                        
                        if df.empty:
                            print(f"[-] Таблица {table_name} пуста. Пропускаю.")
                            continue

                        # 2. УДАЛЯЕМ ЛИШНИЕ СТОЛБЦЫ
                        # Убираем то, что ты просил + то, что не является индикатором
                        cols_to_drop = ['symbol', 'ema_200', 'ema_50', 'timeframe', 'close']
                        # Удаляем только если они есть в таблице
                        existing_drops = [c for c in cols_to_drop if c in df.columns]
                        df = df.drop(columns=existing_drops)
                        print(f"[*] Удалены столбцы: {existing_drops}")

                        # 3. Определяем колонки для нормализации (все кроме времени и таргета)
                        exclude = ['timestamp', 'target_std']
                        feature_cols = [c for c in df.columns if c not in exclude]

                        print(f"[*] Нормализация {len(feature_cols)} индикаторов...")

                        # Сохраняем параметры для этого таймфрейма и стороны
                        self.scaling_params[table_name] = {}

                        # 4. Применяем Z-score и сохраняем параметры
                        for col in feature_cols:
                            mean_val = float(df[col].mean())
                            std_val = float(df[col].std())
                            
                            # Записываем в "паспорт"
                            self.scaling_params[table_name][col] = {
                                'mean': mean_val,
                                'std': std_val
                            }

                            if std_val > 0:
                                df[col] = (df[col] - mean_val) / std_val
                                df[col] = df[col].clip(lower=-7.0, upper=7.0)
                            else:
                                df[col] = 0.0

                        # 5. Вывод статистики для контроля
                        stats = df[feature_cols].agg(['min', 'max']).transpose()
                        print(f"[+] Диапазон после клиппинга: Min {stats['min'].min():.2f} | Max {stats['max'].max():.2f}")

                        # 6. ПЕРЕЗАПИСЫВАЕМ ТАБЛИЦУ
                        df.to_sql(table_name, conn, if_exists='replace', index=False)
                        print(f"[+ SUCCESS] Таблица {table_name} теперь содержит только чистые признаки.")

                # 7. СОХРАНЯЕМ ПАРАМЕТРЫ В JSON
                with open(self.params_file, 'w') as f:
                    json.dump(self.scaling_params, f, indent=4)
                print(f"\n[!!!] Параметры нормализации сохранены в {self.params_file}")
                print("Обязательно сохрани этот файл для работы торгового бота!")

        except Exception as e:
            print(f"[-] Критическая ошибка: {e}")

if __name__ == "__main__":
    normalizer = FeatureNormalizer()
    normalizer.normalize_features()