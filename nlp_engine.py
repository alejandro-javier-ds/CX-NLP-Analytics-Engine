import logging
import datetime
import pandas as pd
from typing import List, Dict, Any, Tuple
from google_play_scraper import Sort, reviews
from deep_translator import GoogleTranslator
from textblob import TextBlob
from sqlalchemy import create_engine
from config import get_connection_string

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s'
)

APP_PACKAGE = 'com.bcp.innovacion.yape'
REVIEW_COUNT = 50

def get_sentiment_category(score: float) -> str:
    if score > 0.15:
        return 'Positive'
    elif score < -0.15:
        return 'Negative'
    return 'Neutral'

def detect_anomaly(star_rating: int, category: str) -> int:
    if star_rating <= 2 and category == 'Positive':
        return 1
    if star_rating >= 4 and category == 'Negative':
        return 1
    return 0

def get_fallback_data() -> Tuple[List[Dict[str, Any]], str]:
    base_time = datetime.datetime.now()
    return [
        {'content': 'Excelente rendimiento y arquitectura muy segura.', 'score': 5, 'at': base_time},
        {'content': 'La última actualización rompió la interfaz, se congela.', 'score': 1, 'at': base_time},
        {'content': 'Cumple su función, pero podría mejorar.', 'score': 3, 'at': base_time},
        {'content': 'Excelente aplicación, la mejor de todas pero la odio.', 'score': 1, 'at': base_time},
        {'content': 'Funciona perfecto todos los días.', 'score': 5, 'at': base_time},
        {'content': 'Terrible servicio, app inútil, me encanta.', 'score': 5, 'at': base_time},
        {'content': 'Interesante pero el registro es lento.', 'score': 3, 'at': base_time},
        {'content': 'La mejor billetera móvil del país.', 'score': 5, 'at': base_time},
        {'content': 'Soporte al cliente decepcionante.', 'score': 1, 'at': base_time},
        {'content': 'Funcionalidad estándar, opera bajo los parámetros.', 'score': 3, 'at': base_time}
    ], 'SYNTHETIC_FALLBACK'

def extract_app_reviews(package: str, count: int) -> Tuple[List[Dict[str, Any]], str]:
    logging.info(f"EXTRACTION: Initiating connection to Google Play Store endpoint ({package})")
    try:
        result, _ = reviews(
            package,
            lang='es',
            country='pe',
            sort=Sort.MOST_RELEVANT,
            count=count
        )
        if result:
            logging.info(f"EXTRACTION: Successfully retrieved {len(result)} raw records.")
            return result, 'REAL_API'

        logging.warning("EXTRACTION: Zero records returned from API. Triggering automated fallback.")
        return get_fallback_data()
    except Exception as e:
        logging.warning(f"EXTRACTION: API Connection timeout or ban. Triggering fallback protocol.")
        return get_fallback_data()

def process_sentiment_pipeline() -> None:
    try:
        raw_data, data_source = extract_app_reviews(APP_PACKAGE, REVIEW_COUNT)

        df = pd.DataFrame(raw_data)
        df = df[['at', 'score', 'content']].rename(columns={
            'at': 'ReviewDate',
            'score': 'StarRating',
            'content': 'RawText'
        })

        translator = GoogleTranslator(source='auto', target='en')
        logging.info(f"PROCESS: Executing vectorized NLP translation and sentiment analysis for {len(df)} records.")

        translated_texts = []
        sentiment_scores = []
        categories = []
        anomalies = []

        for _, row in df.iterrows():
            raw_text = str(row['RawText'])
            try:
                translated = translator.translate(raw_text)
            except Exception:
                translated = raw_text

            analysis = TextBlob(translated)
            score = analysis.sentiment.polarity
            category = get_sentiment_category(score)
            anomaly = detect_anomaly(row['StarRating'], category)

            translated_texts.append(translated)
            sentiment_scores.append(score)
            categories.append(category)
            anomalies.append(anomaly)

        df['TranslatedText'] = translated_texts
        df['SentimentScore'] = sentiment_scores
        df['Category'] = categories
        df['IsAnomaly'] = anomalies
        df['DataSource'] = data_source
        df['ExtractionTimestamp'] = datetime.datetime.now()

        logging.info("DATABASE: Initiating Bulk Insert into SentimentLogs...")
        engine = create_engine(get_connection_string(), fast_executemany=True)

        with engine.begin() as conn:
            existing = pd.read_sql("SELECT RawText FROM SentimentLogs", conn)
            existing_texts = set(existing['RawText'])
            df_new = df[~df['RawText'].isin(existing_texts)]

            if df_new.empty:
                logging.info("SQL_SYNC: No new records to insert. All duplicates skipped.")
                return

            df_new.to_sql('SentimentLogs', con=conn, if_exists='append', index=False, chunksize=500)

        logging.info("SQL_SYNC: Pipeline execution and bulk insert completed successfully.")

    except Exception as e:
        logging.error(f"SYSTEM_ERROR: Critical pipeline failure. Details: {str(e)}")

if __name__ == "__main__":
    process_sentiment_pipeline()