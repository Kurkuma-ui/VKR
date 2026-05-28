import pandas as pd
from db_manager import DBManager

def export_table_to_csv():
    # Подключаемся к твоей базе данных через существующий менеджер
    db = DBManager()
    
    with db.get_connection() as conn:
        # Читаем всю таблицу в DataFrame
        query = "SELECT * FROM tbl_news ORDER BY timestamp DESC"
        df = pd.read_sql_query(query, conn)
    
    # 1. Сохраняем в CSV (encoding='utf-8-sig' нужен, чтобы Excel корректно читал русский/английский текст)
    csv_filename = "news_export.csv"
    df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
    print(f"Таблица успешно сохранена в CSV: {csv_filename}")

    # 2. АЛЬТЕРНАТИВА: Если нужен чистый Excel (требуется библиотека openpyxl: pip install openpyxl)
    # excel_filename = "news_export.xlsx"
    # df.to_excel(excel_filename, index=False)
    # print(f"Таблица успешно сохранена в Excel: {excel_filename}")

if __name__ == "__main__":
    export_table_to_csv()