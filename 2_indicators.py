import pandas as pd
from db_manager import DBManager
import numpy as np

class FeatureProcessor:
    def __init__(self):
        self.db = DBManager()

    def fetch_all_quotes(self, table_name):
        query = f"SELECT * FROM {table_name} ORDER BY timestamp ASC"
        with self.db.get_connection() as conn:
            return pd.read_sql(query, conn)

    def calculate_indicators(self, df):
        d = df.copy()
        
        # EMA200 и 50
        d['ema_200'] = d['close'].ewm(span=200, adjust=False).mean()
        d['ema_50'] = d['close'].ewm(span=50, adjust=False).mean()
        d['dist_ema_200'] = (d['close'] - d['ema_200']) / d['ema_200']
        
        # MACD
        ema12 = d['close'].ewm(span=12, adjust=False).mean()
        ema26 = d['close'].ewm(span=26, adjust=False).mean()
        d['macd_line'] = ema12 - ema26
        d['macd_signal'] = d['macd_line'].ewm(span=9, adjust=False).mean()
        d['macd_hist'] = d['macd_line'] - d['macd_signal']

        # ATR
        high_low = d['high'] - d['low']
        high_close = (d['high'] - d['close'].shift()).abs()
        low_close = (d['low'] - d['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        d['atr'] = true_range.rolling(14).mean()
        
        # BB_Widt
        std = d['close'].rolling(20).std()
        ma = d['close'].rolling(20).mean()
        d['bb_width'] = (4 * std) / ma
        
        # RSI
        delta = d['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        d['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        # ADX
        plus_dm = d['high'].diff().where(lambda x: (x > 0) & (x > d['low'].diff().abs()), 0)
        minus_dm = d['low'].diff().abs().where(lambda x: (x > 0) & (x > d['high'].diff()), 0)
        tr_smooth = true_range.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / tr_smooth)
        minus_di = 100 * (minus_dm.rolling(14).mean() / tr_smooth)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        d['adx'] = dx.rolling(14).mean()
        
        # ROC
        d['roc'] = d['close'].pct_change(periods=12) * 100
        
        # SLOPE
        def get_slope(y):
            if len(y) < 30: return 0
            x = np.arange(len(y))
            return np.polyfit(x, y, 1)[0]
        
        d['slope'] = d['close'].rolling(30).apply(get_slope, raw=True)
        
        # Channel_pos
        d['h50'] = d['high'].rolling(50).max()
        d['l50'] = d['low'].rolling(50).min()
        d['channel_pos'] = (d['close'] - d['l50']) / (d['h50'] - d['l50'])
        
        # Отклонение
        d['z_score'] = (d['close'] - ma) / std
        
        return d.dropna()

    def run(self):
        for tf in ['h1', 'm5']:
            quotes = self.fetch_all_quotes(f"tbl_quotes_{tf}")
            
            if len(quotes) < 200:
                print(f"[-] Мало данных для {tf}")
                continue
                
            print(f"[{tf.upper()}] Расчет признаков")
            features = self.calculate_indicators(quotes)
            
            cols_to_keep = [
                'timestamp', 'symbol', 'ema_200', 'ema_50', 'dist_ema_200', 
                'atr', 'bb_width', 'rsi', 'adx', 'roc', 'slope', 
                'channel_pos', 'z_score', 'macd_hist'
            ]
            final_df = features[cols_to_keep].copy()
            final_df['timeframe'] = tf

            table_name = f"tbl_indic_{tf}"
            
            print(f"[{tf.upper()}] Сохранение данных в tbl_indic_{tf}")
            
            with self.db.get_connection() as conn:
                conn.execute(f"DELETE FROM {table_name}")
                final_df.to_sql(table_name, conn, if_exists='append', index=False)
            
            print(f"[+] {tf.upper()} расчёты записаны в базу")

if __name__ == "__main__":
    FeatureProcessor().run()