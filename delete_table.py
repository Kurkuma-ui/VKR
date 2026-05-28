import sqlite3

# === НАСТРОЙКИ ===
DB_NAME = 'train_zone.db'
TABLE_TO_DELETE = 'filtered_train_h1'  # <--- ВПИШИ НАЗВАНИЕ ТАБЛИЦЫ
# =================

def delete_table():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Команда SQL для удаления таблицы
        query = f"DROP TABLE IF EXISTS {TABLE_TO_DELETE}"
        
        cursor.execute(query)
        conn.commit()
        
        print(f"[+] Таблица '{TABLE_TO_DELETE}' успешно удалена (или её не было).")

    except Exception as e:
        print(f"[-] Ошибка при удалении: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Подтверждение в консоли, чтобы не удалить лишнее случайно
    confirm = input(f"Вы точно хотите удалить таблицу '{TABLE_TO_DELETE}'? (y/n): ")
    if confirm.lower() == 'y':
        delete_table()
    else:
        print("[*] Удаление отменено.")