import os
from urllib.parse import quote_plus

class Config:
    DB_SERVER = os.environ.get("DB_SERVER", r"(localdb)\MSSQLLocalDB")
    DB_NAME = os.environ.get("DB_NAME", "SentimentAnalysisDB")
    DB_DRIVER = os.environ.get("DB_DRIVER", "ODBC Driver 17 for SQL Server")

def get_connection_string() -> str:
    raw_conn_str = (
        f"DRIVER={{{Config.DB_DRIVER}}};"
        f"SERVER={Config.DB_SERVER};"
        f"DATABASE={Config.DB_NAME};"
        "Trusted_Connection=yes;"
    )
    encoded_params = quote_plus(raw_conn_str)
    return f"mssql+pyodbc:///?odbc_connect={encoded_params}"