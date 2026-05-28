import pandas as pd
import sqlite3

def evaluate_test_performance(db_path='train_zone.db'):
    try:
        with sqlite3.connect(db_path) as conn:
            # 1. Загружаем предсказания
            df = pd.read_sql("SELECT * FROM data_test_predicted_h1", conn)
            # 2. Загружаем ИСХОДНУЮ тестовую таблицу (где есть реальный target_std)
            # Если target_std в другой таблице, подставь правильное имя
            original_test = pd.read_sql("SELECT timestamp, target_std FROM data_test_m5", conn)

        # Объединяем по времени, чтобы увидеть, какой профит принесли сигналы ИИ
        report_df = pd.merge(df, original_test, on='timestamp')
        
        # Разделяем: что нашел ИИ и что он пропустил
        signals = report_df[report_df['ai_signal'] == 1]
        no_signals = report_df[report_df['ai_signal'] == 0]

        print(f"\n{'-'*15} ОТЧЕТ ОБ ЭФФЕКТИВНОСТИ ИИ {'-'*15}")
        print(f"Сигналов найдено: {len(signals)}")
        print(f"Средний профит (Target) ИИ: {signals['target_std'].mean():.4f}")
        print(f"Средний профит пропущенных: {no_signals['target_std'].mean():.4f}")
        
        # Проверка по порогу уверенности (фильтруем элиту)
        high_conf = signals[signals['ai_confidence'] > 0.95]
        print(f"Средний профит при уверенности > 0.9: {high_conf['target_std'].mean():.4f} (Всего {len(high_conf)} сделок)")

    except Exception as e:
        print(f"[-] Ошибка при оценке: {e}")

if __name__ == "__main__":
    evaluate_test_performance()