import pandas as pd
import sqlite3
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

def train_and_predict(db_path='train_zone.db'):
    try:
        with sqlite3.connect(db_path) as conn:
            # 1. Загружаем размеченный ТРЕЙН
            train_df = pd.read_sql("SELECT * FROM long_train_m5_clustered", conn)
            # 2. Загружаем нормализованный ТЕСТ
            test_df = pd.read_sql("SELECT * FROM data_test_normal_m5", conn)

        if train_df.empty or test_df.empty:
            print("[-] Ошибка: Одна из таблиц пуста.")
            return

        # 3. ПОДГОТОВКА УЧИТЕЛЯ (Labeling)
        # Назначаем '1' только лучшим кластерам, которые мы выбрали (3, 5, 0)
        good_clusters = [3]
        train_df['target_label'] = train_df['cluster'].apply(lambda x: 1 if x in good_clusters else 0)

        # Список признаков (должен совпадать в обеих таблицах)
        features = ['dist_ema_200', 'atr', 'bb_width', 'rsi', 'adx', 'slope', 'channel_pos', 'macd_hist']
        
        X_train = train_df[features]
        y_train = train_df['target_label']
        X_test = test_df[features]

        # 4. ОБУЧЕНИЕ МОДЕЛИ
        print(f"[*] Обучаю модель на {len(X_train)} примерах...")
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)

        # 5. ПРЕДСКАЗАНИЕ НА ТЕСТЕ
        print("[*] Запускаю предсказание на тестовых данных...")
        test_df['ai_signal'] = model.predict(X_test)
        # Получаем вероятность (уверенность модели)
        test_df['ai_confidence'] = model.predict_proba(X_test)[:, 1]

        # 6. СОХРАНЕНИЕ РЕЗУЛЬТАТА
        with sqlite3.connect(db_path) as conn:
            test_df.to_sql("data_test_predicted_h1", conn, if_exists='replace', index=False)
        
        # 7. СТАТИСТИКА
        signals_count = test_df['ai_signal'].sum()
        avg_conf = test_df[test_df['ai_signal'] == 1]['ai_confidence'].mean()
        
        print(f"\n{'-'*20} ИТОГИ ТЕСТА {'-'*20}")
        print(f"[+] Всего свечей в тесте: {len(test_df)}")
        print(f"[+] Модель нашла сигналов: {signals_count}")
        print(f"[+] Средняя уверенность в сигналах: {avg_conf:.2f}")
        print(f"[+ SUCCESS] Результаты сохранены в data_test_predicted_h1")

    except Exception as e:
        print(f"[-] Ошибка: {e}")

if __name__ == "__main__":
    train_and_predict()