import pandas as pd
from rm_config import RISK_CONFIG

class RiskManager:
    def __init__(self, config=None):
        # Если конфиг не передан, берем из файла по умолчанию
        self.config = config if config else RISK_CONFIG

    def calculate_levels(self, price, atr, direction, tf):
        tf_key = tf.upper()
        dir_key = direction.upper()

        # Проверка наличия настроек для конкретного ТФ и направления
        if tf_key not in self.config or dir_key not in self.config[tf_key]:
            return None

        conf = self.config[tf_key][dir_key]
        
        # Расчет дистанций на основе множителей из конфига
        sl_dist = atr * conf['sl_mult']
        tp_dist = atr * conf['tp_mult']

        if dir_key == 'BUY':
            sl = price - sl_dist
            tp = price + tp_dist
        else:
            sl = price + sl_dist
            tp = price - tp_dist

        # Добавим полезные данные для вывода
        return {
            'entry': price,
            'sl': round(sl, 5),
            'tp': round(tp, 5),
            'risk_reward': round(tp_dist / sl_dist, 2) if sl_dist != 0 else 0
        }

    def get_lot_size(self, balance, stop_loss_dist):
        """
        Рассчитывает объем лота. 
        stop_loss_dist — это расстояние в абсолютных единицах цены (например, 0.0020)
        """
        # Риск в валюте депозита
        risk_amount = balance * self.config.get('RISK_PER_TRADE', 0.02)
        
        # Переводим дистанцию в пункты (pips). Для 5-знака 0.00010 = 10 пунктов
        # Для простоты считаем, что 0.0001 = 1 пункт (стандарт для EURUSD)
        pips_dist = stop_loss_dist * 10000 
        
        if pips_dist <= 0: return 0.01
        
        # Лот = Риск / (Пункты * Стоимость пункта). 1 лот при 10 пипсах стопа = 100$ риска.
        lot = risk_amount / (pips_dist * 10) 
        
        return round(max(0.01, min(lot, 10.0)), 2)

# Пример использования для теста:
if __name__ == "__main__":
    # Передаем конфиг при создании
    rm = RiskManager(RISK_CONFIG)
    
    # Тест для H1 BUY
    # Представим: цена 1.0850, ATR 0.0015
    levels = rm.calculate_levels(1.0850, 0.0015, 'BUY', 'H1')
    
    if levels:
        print(f"--- ТЕСТ RISK MANAGER (H1 BUY) ---")
        print(f"Вход: {levels['entry']} | TP: {levels['tp']} | SL: {levels['sl']}")
        print(f"Соотношение Риск/Прибыль (RR): {levels['risk_reward']}")
        
        # Тест лота
        sl_dist = abs(levels['entry'] - levels['sl'])
        lot = rm.get_lot_size(10000, sl_dist)
        print(f"Рекомендуемый лот для риска 2%: {lot}")
    else:
        print("[!] Ошибка: Неверные параметры TF или Direction")