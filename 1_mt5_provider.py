import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import config
from db_manager import DBManager

HISTORY_DEPTH = {
    mt5.TIMEFRAME_H1: 5000,
    mt5.TIMEFRAME_M5: 15000
}

class MT5Provider:
    def __init__(self):
        self.db = DBManager(config.DB_NAME)

    def connect(self):
        if not mt5.initialize():
            print(f"[-] Ошибка подключения к MT5: {mt5.last_error()}")
            return False
        print("[+] Успешное подключение к MetaTrader 5")
        return True

    def fetch_and_save_data(self, symbol, timeframe, direction):
        if not mt5.symbol_select(symbol, True):
            print(f"[-] Ошибка: Символ {symbol} не найден.")
            return

        tf_map = {mt5.TIMEFRAME_M5: "m5", mt5.TIMEFRAME_H1: "h1"}
        suffix = tf_map.get(timeframe, "unknown")
        table_name = f"tbl_quotes_{suffix}"
        
        count = HISTORY_DEPTH.get(timeframe, 5000)

        # Границы данных в БД
        last_time_str = self.db.get_last_quote_time(symbol, table_name)
        first_time_str = self.db.get_first_quote_time(symbol, table_name)

        rates = None

        # Докачка
        if direction == "future":
            if last_time_str:
                last_dt = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
                print(f"[{suffix.upper()}] Обновление: Запрос свечей после {last_dt}...")
                rates = mt5.copy_rates_range(symbol, timeframe, last_dt, datetime.now() + timedelta(days=1))
            else:
                print(f"[{suffix.upper()}] База пуста. Загружаю начальные {count} свечей...")
                rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

        # Подгрузка
        elif direction == "past":
            if first_time_str:
                first_dt = datetime.strptime(first_time_str, '%Y-%m-%d %H:%M:%S')
                print(f"[{suffix.upper()}] Подгрузка истории: Найдено {count} свечей ДО {first_dt}...")
                
                rates = mt5.copy_rates_from(symbol, timeframe, first_dt, count)
            else:
                print(f"[{suffix.upper()}] Невозможно качать 'past': база пуста.")
                return

        if rates is None or len(rates) == 0:
            print(f"[-] [{suffix.upper()}] MT5 не вернул данных для направления {direction}.")
            return

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Фильтрация дублей на стыках
        if direction == "future" and last_time_str:
            df = df[df['time'] > last_dt]
        elif direction == "past" and first_time_str:
            df = df[df['time'] < first_dt]

        if df.empty:
            print(f"[{suffix.upper()}] Новых уникальных данных не обнаружено.")
            return

        # Форматирование для сохранения
        print(f"[SUCCESS] {suffix.upper()}: Подготовлено {len(df)} строк.")
        df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'tick_volume']
        df['symbol'] = symbol
        
        try:
            self.db.save_quotes(df, table_name=table_name)
        except Exception as e:
            print(f"[-] Ошибка при сохранении в БД: {e}")

    def close(self):
        mt5.shutdown()
        print("[!] Сессия MetaTrader 5 завершена.")

if __name__ == "__main__":
    provider = MT5Provider()
    if provider.connect():
         
        if config.LOAD_HISTORY_MODE:
            print("\n>>> РЕЖИМ: ГЛУБОКАЯ ПОДГРУЗКА ИСТОРИИ (PAST) <<<")
            for tf in HISTORY_DEPTH.keys():
                provider.fetch_and_save_data(config.SYMBOL, tf, direction="past")
        else:
            print("\n>>> РЕЖИМ: ОБНОВЛЕНИЕ ТЕКУЩИХ ДАННЫХ (FUTURE) <<<")
            for tf in HISTORY_DEPTH.keys():
                provider.fetch_and_save_data(config.SYMBOL, tf, direction="future")
            
        provider.close()