import pandas as pd
import sqlite3

def find_correlations_report(db_path='train_zone.db', threshold=0.8):
    tables = [
        'long_train_h1', 
        'long_train_m5', 
        'short_train_h1', 
        'short_train_m5'
    ]

    try:
        with sqlite3.connect(db_path) as conn:
            for table_name in tables:
                print(f"\n{'='*30} АНАЛИЗ ТАБЛИЦЫ: {table_name.upper()} {'='*30}")
                
                try:
                    df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                except Exception as e:
                    print(f"[!] Таблица {table_name} не найдена или недоступна: {e}")
                    continue

                if df.empty:
                    print(f"[-] Таблица {table_name} пуста.")
                    continue

                # 1. Подготовка признаков (включая vol_norm)
                exclude = ['timestamp', 'target_std', 'roc', 'z_score']
                features = df.drop(columns=[c for c in exclude if c in df.columns], errors='ignore')
                
                # 2. Матрица корреляций
                corr_matrix = features.corr().abs()
                
                # 3. Сбор уникальных пар
                pairs = []
                cols = corr_matrix.columns
                for i in range(len(cols)):
                    for j in range(i + 1, len(cols)):
                        pairs.append({
                            'Feature 1': cols[i],
                            'Feature 2': cols[j],
                            'Correlation': round(corr_matrix.iloc[i, j], 4)
                        })
                
                if not pairs:
                    print(f"[-] Недостаточно признаков для расчета корреляции в {table_name}")
                    continue
                    
                all_pairs_df = pd.DataFrame(pairs).sort_values(by='Correlation', ascending=False)

                # 4. Вывод критических связей
                bad_corrs = all_pairs_df[all_pairs_df['Correlation'] >= threshold]
                
                print(f"\n>>> КРИТИЧЕСКИЕ СВЯЗИ (> {threshold}):")
                if bad_corrs.empty:
                    print("    [+] Чисто! Сильных зависимостей не обнаружено.")
                else:
                    print(bad_corrs.to_string(index=False))

                # 5. Топ-5 для общего понимания структуры
                print(f"\n>>> ТОП-5 СИЛЬНЕЙШИХ СВЯЗЕЙ:")
                print(all_pairs_df.head(5).to_string(index=False))
                print(f"\n{'-'*80}")

    except Exception as e:
        print(f"[-] Критическая ошибка при работе с БД: {e}")

if __name__ == "__main__":
    find_correlations_report()