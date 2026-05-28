import pandas as pd
import sqlite3
from sklearn.cluster import KMeans

def perform_final_clustering(db_path='train_zone.db', table_name='long_train_m5', n_clusters=4):
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        
        if df.empty:
            print(f"[-] Таблица {table_name} пуста.")
            return

        # 1. Подготовка признаков
        exclude = ['timestamp', 'target_std', 'roc', 'z_score']
        features = df.drop(columns=[c for c in exclude if c in df.columns], errors='ignore')
        
        # 2. Кластеризация
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(features)
        
        # 3. ВЫВОД СТАТИСТИКИ ЭФФЕКТИВНОСТИ
        stats = df.groupby('cluster')['target_std'].agg(['count', 'mean', 'std']).reset_index()
        stats.columns = ['Кластер', 'Кол-во', 'Средний Target', 'Риск (STD)']
        
        print(f"\n{'-'*15} СТАТИСТИКА КЛАСТЕРОВ (k={n_clusters}) {'-'*15}")
        print(stats.sort_values(by='Средний Target', ascending=False).to_string(index=False))

        # 4. ПРОФИЛИ РЫНОЧНЫХ СИТУАЦИЙ (Центры кластеров)
        # Считаем среднее по каждому индикатору внутри кластера
        profiles = df.groupby('cluster')[features.columns].mean()
        
        print(f"\n{'-'*15} ПРОФИЛИ РЫНОЧНЫХ СИТУАЦИЙ (Средние значения) {'-'*15}")
        # Выводим в том же порядке, что и статистику прибыли для удобства сравнения
        sorted_clusters = stats.sort_values(by='Средний Target', ascending=False)['Кластер']
        print(profiles.loc[sorted_clusters].round(3).to_string())

        # 5. Перезапись в БД
        with sqlite3.connect(db_path) as conn:
            new_table_name = f"{table_name}_clustered"
            df.to_sql(new_table_name, conn, if_exists='replace', index=False)
            
        print(f"\n[+ SUCCESS] Таблица {new_table_name} обновлена.")

    except Exception as e:
        print(f"[-] Ошибка: {e}")

if __name__ == "__main__":
    tables_to_process = [
        'long_train_h1', 
        'long_train_m5', 
        'short_train_h1', 
        'short_train_m5'
    ]
    
    db_path = 'train_zone.db'
    
    print(f"[*] Начало глобальной кластеризации для базы: {db_path}")
    print("="*60)

    for table in tables_to_process:
        print(f"\n>>> Обработка таблицы: {table.upper()}")
        perform_final_clustering(db_path=db_path, table_name=table, n_clusters=4)
        print(f"{'='*60}")
    
    print("\n[ЗАВЕРШЕНО] Все таблицы обработаны и обновлены.")