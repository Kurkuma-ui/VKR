import pandas as pd
from db_manager import DBManager

def run_historical_test():
    db = DBManager()
    
    # 1. Загружаем все обработанные новости из базы данных
    with db.get_connection() as conn:
        query = """
            SELECT timestamp, title, content, source_sentiment 
            FROM tbl_news 
            WHERE sentiment_done = 1 
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, conn)
        
    if df.empty:
        print("❌ Ошибка: В базе данных нет новостей со скорингом сентимента (sentiment_done = 1).")
        print("Сначала запусти скрипт разметки FinBERT.")
        return
        
    # 2. Предобработка временных рядов
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    
    # Переносим временную метку в индекс, чтобы pandas корректно считал временные окна ('3d', '14d')
    df.set_index('timestamp', inplace=True)
    
    # 3. Расчет скользящих показателей (Включает текущую новость и смотрит назад во времени)
    df['mood_3d'] = df['source_sentiment'].rolling('3d').mean()
    df['mood_14d'] = df['source_sentiment'].rolling('14d').mean()
    
    # Расчет стандартного отклонения и Z-Score для 14 дней (метрика импульса сентимента)
    df['std_14d'] = df['source_sentiment'].rolling('14d').std()
    df['z_score_14d'] = (df['source_sentiment'] - df['mood_14d']) / df['std_14d']
    df['z_score_14d'] = df['z_score_14d'].fillna(0)  # Защита от NaN, если новостей слишком мало
    
    # 4. Фильтруем данные для вывода: берем только последние 30 дней
    max_date = df.index.max()
    start_date = max_date - pd.Timedelta(days=30)
    df_test_period = df[df.index >= start_date]
    
    # 5. Вывод результатов в консоль
    print("=" * 90)
    print(f"🚀 СИМУЛЯЦИЯ ТЕСТОВОГО ПРОГОНА СИСТЕМЫ ЗА ПОСЛЕДНИЕ 30 ДНЕЙ")
    print(f"Период: {start_date.strftime('%Y-%m-%d')} ---> {max_date.strftime('%Y-%m-%d')}")
    print(f"Всего целевых новостей в этом окне: {len(df_test_period)}")
    print("=" * 90 + "\n")
    
    for i, (timestamp, row) in enumerate(df_test_period.iterrows(), 1):
        print(f"📍 [Новость #{i}] Время фиксации: {timestamp}")
        print(f"   [Название]: {row['title']}")
        print(f"   [Контент] : {row['content'] if row['content'] else 'Нет описания.'}")
        print(f"   [Сентимент]: {row['source_sentiment']:.4f}")
        print("-" * 50)
        print(f"   📊 Метрики скользящих окон на момент выхода новости:")
        print(f"      🔹 Средний сентимент за 3 дня (Mood 3D)  : {row['mood_3d']:.4f}")
        print(f"      🔸 Средний сентимент за 14 дней (Mood 14D): {row['mood_14d']:.4f}")
        print(f"      ⚡ Текущий Импульс рынка (Z-Score 14D)    : {row['z_score_14d']:.4f}")
        print("=" * 90 + "\n")

if __name__ == "__main__":
    run_historical_test()