import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import create_engine
from config import get_connection_string

st.set_page_config(page_title="BrandPulse VoC Engine", layout="wide")

@st.cache_data(ttl=10)
def fetch_telemetry_data() -> pd.DataFrame:
    try:
        engine = create_engine(get_connection_string())
        query = """
            SELECT ReviewDate, StarRating, Category, SentimentScore, RawText, TranslatedText, IsAnomaly, DataSource 
            FROM SentimentLogs 
            ORDER BY ReviewDate DESC
        """
        return pd.read_sql(query, engine)
    except Exception as error:
        st.error(f"DATABASE_CONNECTION_FAILURE: {str(error)}")
        return pd.DataFrame()

def build_gauge_widget(average_polarity: float):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=average_polarity,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Brand Health Index (NLP Polarity)"},
        gauge={
            'axis': {'range': [-1, 1]},
            'bar': {'color': "#1F77B4"},
            'steps': [
                {'range': [-1, -0.15], 'color': "#FF4B4B"}, 
                {'range': [-0.15, 0.15], 'color': "#F0F2F6"},
                {'range': [0.15, 1], 'color': "#09AB3B"}     
            ]
        }
    ))

def format_category(cat: str) -> str:
    if cat == 'Positive': return '[ POSITIVE ]'
    elif cat == 'Negative': return '[ NEGATIVE ]'
    return '[ NEUTRAL ]'

def initialize_dashboard():
    st.title("BrandPulse: Voice of the Customer (VoC) Monitor")
    st.markdown("---")

    dataset = fetch_telemetry_data()

    if dataset.empty:
        st.warning("SYSTEM_IDLE: No records found in telemetry database.")
        return

    latest_source = dataset['DataSource'].iloc[0]
    if latest_source == 'SYNTHETIC_FALLBACK':
        st.error("WARNING: Operating under SYNTHETIC_FALLBACK mode. Displaying simulated fault-tolerant data.")
    else:
        st.success("LIVE API: Consuming real-time production data.")

    global_sentiment = dataset['SentimentScore'].mean()
    anomaly_count = int(dataset['IsAnomaly'].sum())

    panel_left, panel_right = st.columns([0.35, 0.65])

    with panel_left:
        st.subheader("Global Polarity Index")
        gauge_fig = build_gauge_widget(global_sentiment)
        st.plotly_chart(gauge_fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        col1.metric(label="Processed Volume", value=f"{len(dataset)} Records")
        col2.metric(label="Detected Anomalies", value=f"{anomaly_count} Flags")

    with panel_right:
        st.subheader("Data Telemetry & Audit")
        
        display_data = dataset.copy()
        display_data['FormattedRating'] = display_data['StarRating'].apply(lambda x: f"{int(x)} / 5")
        display_data['NLP_Verdict'] = display_data['Category'].apply(format_category)
        display_data['Anomaly_Flag'] = display_data['IsAnomaly'].apply(lambda x: 'YES' if x == 1 else 'NO')

        st.dataframe(
            display_data[['ReviewDate', 'FormattedRating', 'Anomaly_Flag', 'NLP_Verdict', 'SentimentScore', 'RawText', 'TranslatedText']],
            column_config={
                "ReviewDate": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD"),
                "FormattedRating": "App Rating",
                "Anomaly_Flag": "Incongruence",
                "NLP_Verdict": "NLP Verdict",
                "RawText": "Raw User Feedback",
                "TranslatedText": "NLP Translation",
                "SentimentScore": st.column_config.ProgressColumn(
                    "Polarity Score",
                    format="%.2f",
                    min_value=-1,
                    max_value=1,
                ),
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )

if __name__ == "__main__":
    initialize_dashboard()