import pandas as pd
import sqlite3
import json
import os

class TestNormalizer:
    def __init__(self, db_path='train_zone.db', params_file='scaling_params.json'):
        self.db_path = db_path
        self.params_file = params_file
        self.scaling_params = self._load_params()

    def _load_params(self):
        """Загрузка параметров из JSON, созданного при обучении"""
        if not os.path.exists(self.params_file):
            raise FileNotFoundError(f"[-] Файл параметров {self.params_file} не найден! Сначала запусти нормализацию трейна.")
        with open(self.params_file, 'r') as f:
            return json.load(f)

    def normalize_test_data(self, timeframes=['h1', 'm5']):
        try:
            with sqlite3.connect(self.db_path) as conn:
                for tf in timeframes:
                    # Имя исходной таблицы теста
                    source_table = f"data_test_{tf}"
                    # Имя новой таблицы для нормализованных данных
                    target_table = f"data_test_normal_{tf}"
                    
                    print(f"\n{'-'*20} [Обработка теста: {source_table.upper()}] {'-'*20}")
                    
                    # 1. Загружаем тестовые данные
                    df = pd.read_sql(f"SELECT * FROM {source_table}", conn)
                    
                    if df.empty:
                        print(f"[-] Таблица {source_table} пуста. Пропускаю.")
                        continue

                    # 2. Удаляем лишние столбцы (те же, что и в трейне)
                    cols_to_drop = ['symbol', 'ema_200', 'ema_50', 'timeframe', 'close', 'roc', 'z_score']
                    existing_drops = [c for c in cols_to_drop if c in df.columns]
                    df = df.drop(columns=existing_drops)

                    # 3. Подбираем параметры нормализации
                    # Т.к. в тесте нет разделения на long/short, берем параметры от long_train_{tf}
                    # Индикаторы (RSI, ATR и т.д.) считаются одинаково для обеих сторон.
                    ref_key = f"long_train_{tf}"
                    if ref_key not in self.scaling_params:
                        print(f"[-] Нет параметров для {ref_key} в JSON. Пропускаю {tf}.")
                        continue
                    
                    current_params = self.scaling_params[ref_key]
                    
                    # 4. Применяем Z-score ИЗ ТРЕЙНА
                    print(f"[*] Применяю параметры нормализации от {ref_key}...")
                    
                    applied_count = 0
                    for col, p in current_params.items():
                        if col in df.columns:
                            mean_val = p['mean']
                            std_val = p['std']
                            
                            if std_val > 0:
                                df[col] = (df[col] - mean_val) / std_val
                                # Тот же клиппинг, что и в трейне
                                df[col] = df[col].clip(lower=-7.0, upper=7.0)
                            else:
                                df[col] = 0.0
                            applied_count += 1

                    print(f"[+] Нормализовано признаков: {applied_count}")

                    # 5. Сохраняем в НОВУЮ таблицу
                    # Мы не перезаписываем исходный тест, а создаем data_test_normal_{tf}
                    df.to_sql(target_table, conn, if_exists='replace', index=False)
                    print(f"[+ SUCCESS] Результат сохранен в таблицу: {target_table}")

        except Exception as e:
            print(f"[-] Ошибка при нормализации теста: {e}")

if __name__ == "__main__":
    # Запускаем нормализацию для тестов
    test_norm = TestNormalizer()
    test_norm.normalize_test_data(timeframes=['h1', 'm5'])