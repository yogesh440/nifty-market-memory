import os
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


# ---------------------------------------------------------
# 1. Load environment variables
# ---------------------------------------------------------

load_dotenv()

server = os.getenv("SQL_SERVER")
database = os.getenv("SQL_DATABASE")
username = os.getenv("SQL_USERNAME")
password = os.getenv("SQL_PASSWORD")


# ---------------------------------------------------------
# 2. Validate configuration
# ---------------------------------------------------------

if not all([server, database, username, password]):
    raise ValueError(
        "Missing SQL connection settings. "
        "Check the .env file."
    )


# ---------------------------------------------------------
# 3. Create Azure SQL connection
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# 4. Read NIFTY 50 Market Memory
# ---------------------------------------------------------

query = """
SELECT
    MarketMemoryID,
    MemoryType,
    MemoryYear,
    MemoryNumber,
    MemoryLabel,
    PeriodStartDate,
    PeriodEndDate,
    OpenPrice,
    HighPrice,
    LowPrice,
    ClosePrice,
    PreviousClose,
    ReturnPct,
    Direction,
    RunningPeak,
    DrawdownPct,
    PeakDate,
    IsNewAllTimeHigh
FROM dbo.Nifty50_MarketMemory
ORDER BY
    PeriodEndDate,
    MemoryType;
"""


df = pd.read_sql(query, engine)


# ---------------------------------------------------------
# 5. Basic validation
# ---------------------------------------------------------

print("=" * 60)
print("NIFTY 50 MARKET MEMORY - PYTHON ANALYTICS")
print("=" * 60)

print(f"Rows loaded       : {len(df):,}")
print(f"Columns loaded    : {len(df.columns)}")

if not df.empty:
    print(f"First period date : {df['PeriodStartDate'].min()}")
    print(f"Last period date  : {df['PeriodEndDate'].max()}")

print("\nMemory Type Counts")
print("-" * 60)

print(
    df["MemoryType"]
    .value_counts()
    .sort_index()
)


print("\nDirection Counts")
print("-" * 60)

print(
    df["Direction"]
    .value_counts()
    .sort_index()
)


print("\nLatest Market Memory")
print("-" * 60)

latest = (
    df.sort_values("PeriodEndDate")
      .tail(10)
)

print(
    latest[
        [
            "MemoryType",
            "MemoryLabel",
            "PeriodStartDate",
            "PeriodEndDate",
            "ClosePrice",
            "ReturnPct",
            "Direction",
            "DrawdownPct",
        ]
    ].to_string(index=False)
)


print("\nSUCCESS: Python analytics layer can read Azure SQL.")
print("=" * 60)