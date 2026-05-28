import pandas as pd
import sqlite3
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

def find_optimal_clusters_multi(db_path='train_zone.db', max_k=8):
    tables = [
        'long_train_h1', 'long_train_m5', 
        'short_train_h1', 'short_train_m5'
    ]
    
    # Создаем сетку графиков 2x2
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.flatten()
    
    try:
        with sqlite3.connect(db_path) as conn:
            for i, table_name in enumerate(tables):
                print(f"[*] Анализ {table_name}...")
                
                try:
                    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                except:
                    print(f"[!] Таблица {table_name} не найдена.")
                    continue
                
                if df.empty:
                    continue

                # 1. Подготовка признаков
                exclude = ['timestamp', 'target_std', 'cluster', 'roc', 'z_score']
                features = df.drop(columns=[c for c in exclude if c in df.columns], errors='ignore')
                
                # 2. Расчет инерции
                inertia = []
                k_range = range(1, max_k + 1)
                for k in k_range:
                    km = KMeans(n_clusters=k, random_state=42, n_init=10)
                    km.fit(features)
                    inertia.append(km.inertia_)
                
                # 3. Отрисовка на соответствующем подграфике
                ax = axes[i]
                ax.plot(k_range, inertia, 'bo-', markersize=7)
                ax.set_title(f"Метод локтя: {table_name.upper()}")
                ax.set_xlabel('Количество кластеров (k)')
                ax.set_ylabel('Инерция')
                ax.grid(True, alpha=0.3)
                
                # Пометка текущего выбора (k=4)
                ax.axvline(x=4, color='r', linestyle='--', label='Текущий k=4')
                ax.legend()

        plt.tight_layout()
        plt.show()

    except Exception as e:
        print(f"[-] Ошибка: {e}")

if __name__ == "__main__":
    find_optimal_clusters_multi()