import sqlite3
import config

class DBManager:
    def __init__(self):
        self.db_path = config.DB_PATH

    def get_connection(self):
        # Файл БД создастся автоматически при первом подключении
        return sqlite3.connect(self.db_path)