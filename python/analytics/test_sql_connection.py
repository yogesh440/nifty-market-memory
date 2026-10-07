import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus


# Load .env
load_dotenv()

server = os.getenv("SQL_SERVER")
database = os.getenv("SQL_DATABASE")
username = os.getenv("SQL_USERNAME")
password = os.getenv("SQL_PASSWORD")


# Check settings
if not all([server, database, username, password]):
    raise ValueError("Missing SQL connection settings in .env")


# Azure SQL connection
connection_string = (
    "mssql+pyodbc://"
    f"{quote_plus(username)}:{quote_plus(password)}@"
    f"{server}:1433/{database}"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&Encrypt=yes"
    "&TrustServerCertificate=no"
    "&Connection+Timeout=30"
)

engine = create_engine(connection_string)


# Test connection
with engine.connect() as connection:
    result = connection.execute(
        text("SELECT DB_NAME() AS DatabaseName, GETDATE() AS ServerTime")
    )

    row = result.fetchone()

    print("SUCCESS: Connected to Azure SQL")
    print(f"Database: {row.DatabaseName}")
    print(f"Server time: {row.ServerTime}")