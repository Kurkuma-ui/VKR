import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor

class FeatureAnalyzer:
    def __init__(self, db_path='train_zone.db'):
        self.db_path = db_path

    def analyze_all_tables(self):
        tables = [
            'long_train_h1_clustered',
            'long_train_m5_clustered',
            'short_train_h1_clustered',
            'short_train_m5_clustered'
        ]
        
        # Сводная таблица для сравнения важности между TF и направлениями
        summary_importance = pd.DataFrame()

        for table in tables:
            print(f"\n{'='*20} Анализ: {table} {'='*20}")
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    df = pd.read_sql(f"SELECT * FROM {table}", conn)
                
                if df.empty:
                    print(f"[-] Данные в {table} не найдены.")
                    continue

                # 1. Подготовка данных
                y = df['target_std']
                # Исключаем технические колонки. 
                # Добавляем vol_avg/vol_std если они остались, оставляем vol_norm
                drop_cols = ['timestamp', 'target_std', 'cluster', 'roc', 'z_score', 'date_only']
                X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
                
                # 2. Обучение модели
                model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
                model.fit(X, y)

                # 3. Сбор важности
                importance = pd.DataFrame({
                    'Feature': X.columns,
                    'Importance': model.feature_importances_,
                    'Source': table
                }).sort_values(by='Importance', ascending=False)

                summary_importance = pd.concat([summary_importance, importance])

                # 4. Визуализация каждого случая
                plt.figure(figsize=(10, 5))
                sns.barplot(x='Importance', y='Feature', data=importance, palette='magma')
                plt.title(f'Важность признаков: {table}')
                plt.tight_layout()
                plt.show()

                print(f"[+] Топ-5 для {table}:")
                print(importance[['Feature', 'Importance']].head(5).to_string(index=False))

            except Exception as e:
                print(f"[-] Ошибка при анализе {table}: {e}")

        return summary_importance

if __name__ == "__main__":
    analyzer = FeatureAnalyzer()
    all_importances = analyzer.analyze_all_tables()