import logging
import torch
import sqlite3
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from db_manager import DBManager

# Настройка логирования для отслеживания прогресса в консоли
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SentimentProcessor:
    def __init__(self):
        self.db = DBManager()
        # Используем классический ProsusAI/finbert — стандарт для фин-анализа
        self.model_name = "ProsusAI/finbert"
        
        logging.info("Загрузка модели FinBERT (это может занять время при первом запуске)...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.eval() # Режим оценки (выключает dropout)
        except Exception as e:
            logging.error(f"Не удалось загрузить модель: {e}")
            raise

    def process_pending_news(self):
        """Обрабатывает только те новости, где sentiment_done = 0"""
        
        # 1. Получаем список задач из БД
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, content 
                FROM tbl_news 
                WHERE sentiment_done = 0
            """)
            rows = cursor.fetchall()

        if not rows:
            logging.info("Новых новостей для анализа не найдено.")
            return

        logging.info(f"Найдено {len(rows)} новостей для обработки.")

        for news_id, title, content in rows:
            # Объединяем заголовок и краткое описание для полноты картины
            full_text = f"{title}. {content}"
            
            try:
                # 2. Токенизация текста
                inputs = self.tokenizer(full_text, return_tensors="pt", truncation=True, padding=True, max_length=512)
                
                # 3. Предсказание модели
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    # Превращаем логиты в вероятности (0: pos, 1: neg, 2: neut)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1).numpy()[0]
                
                # Рассчитываем итоговый вес: Позитив минус Негатив
                # Если 0.8 pos и 0.1 neg -> итого 0.7 (сильный лонг)
                # Если 0.1 pos и 0.9 neg -> итого -0.8 (сильный шорт)
                sentiment_score = float(probs[0] - probs[1])

                # 4. Сохранение результата и смена флага sentiment_done
                with self.db.get_connection() as conn:
                    conn.execute("""
                        UPDATE tbl_news 
                        SET source_sentiment = ?, sentiment_done = 1 
                        WHERE id = ?
                    """, (sentiment_score, news_id))
                    conn.commit()
                
                logging.info(f"ID {news_id}: Скор {sentiment_score:.2f} записан.")

            except Exception as e:
                logging.error(f"Ошибка при обработке новости {news_id}: {e}")

        logging.info("Обработка всей очереди завершена.")

if __name__ == "__main__":
    processor = SentimentProcessor()
    processor.process_pending_news()