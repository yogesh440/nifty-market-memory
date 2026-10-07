"""
NIFTY 50 Analytics Summary
--------------------------
Purpose:
    Read the validated NIFTY 50 Market Memory and Conditional Market Memory
    tables from Azure SQL and produce a clean analytical summary.

Source tables:
    dbo.Nifty50_MarketMemory
    dbo.Nifty50_ConditionalMarketMemory

This script is read-only.
It does not modify Azure SQL data.
"""

import os
import urllib.parse

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ============================================================
# 1. LOAD ENVIRONMENT
# ============================================================

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")


if not all(
    [
        SQL_SERVER,
        SQL_DATABASE,
        SQL_USERNAME,
        SQL_PASSWORD,
    ]
):
    raise ValueError(
        "Missing SQL connection settings. "
        "Check the .env file."
    )


# ============================================================
# 2. CREATE AZURE SQL CONNECTION
# ============================================================

connection_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SQL_SERVER},1433;"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USERNAME};"
    f"PWD={SQL_PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)

encoded_connection = urllib.parse.quote_plus(connection_string)

engine = create_engine(
    f"mssql+pyodbc:///?odbc_connect={encoded_connection}",
    pool_pre_ping=True,
)


# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def print_title(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_table(df: pd.DataFrame) -> None:
    if df.empty:
        print("No data found.")
        return

    print(df.to_string(index=False))


# ============================================================
# 4. TEST CONNECTION
# ============================================================

with engine.connect() as connection:
    connection.execute(text("SELECT 1"))

print_title("NIFTY 50 ANALYTICS SUMMARY")
print("SUCCESS: Connected to Azure SQL.")
print(f"Database: {SQL_DATABASE}")


# ============================================================
# 5. LOAD MARKET MEMORY
# ============================================================

market_memory_query = """
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
ORDER BY PeriodEndDate, MemoryType;
"""

market_memory = pd.read_sql(
    market_memory_query,
    engine,
)


# ============================================================
# 6. LOAD CONDITIONAL MARKET MEMORY
# ============================================================

conditional_query = """
SELECT
    ConditionalMemoryID,
    CandleDirection,
    StreakStartDate,
    StreakEndDate,
    StreakLength,
    StreakReturnPct,
    FollowingWeekStartDate,
    FollowingWeekEndDate,
    FollowingWeekReturnPct,
    FollowingWeekDirection,
    MagnitudeBucket,
    ResearchCondition,
    CreatedAt
FROM dbo.Nifty50_ConditionalMarketMemory
ORDER BY StreakEndDate, CandleDirection;
"""

conditional_memory = pd.read_sql(
    conditional_query,
    engine,
)


# ============================================================
# 7. BASIC DATASET SUMMARY
# ============================================================

print_title("DATASET SUMMARY")

print(f"Market Memory Rows       : {len(market_memory):,}")
print(f"Conditional Memory Rows  : {len(conditional_memory):,}")

if not market_memory.empty:
    print(
        f"Market Memory Start Date : "
        f"{market_memory['PeriodStartDate'].min()}"
    )

    print(
        f"Market Memory End Date   : "
        f"{market_memory['PeriodEndDate'].max()}"
    )


# ============================================================
# 8. PERIOD PERFORMANCE SUMMARY
# ============================================================

print_title("PERIOD PERFORMANCE SUMMARY")

performance_rows = []

for memory_type in ["DAILY", "WEEK", "MONTH", "YEAR"]:

    df = market_memory[
        market_memory["MemoryType"] == memory_type
    ].copy()

    if df.empty:
        continue

    returns = pd.to_numeric(
        df["ReturnPct"],
        errors="coerce",
    ).dropna()

    drawdowns = pd.to_numeric(
        df["DrawdownPct"],
        errors="coerce",
    ).dropna()

    positive_count = int((returns > 0).sum())
    negative_count = int((returns < 0).sum())
    flat_count = int((returns == 0).sum())

    performance_rows.append(
        {
            "MemoryType": memory_type,
            "Periods": len(df),
            "PositivePeriods": positive_count,
            "NegativePeriods": negative_count,
            "FlatPeriods": flat_count,
            "PositivePct": (
                positive_count / len(returns) * 100
                if len(returns) > 0
                else None
            ),
            "AverageReturnPct": returns.mean(),
            "BestReturnPct": returns.max(),
            "WorstReturnPct": returns.min(),
            "MaxDrawdownPct": drawdowns.min(),
        }
    )


performance_summary = pd.DataFrame(
    performance_rows
)

print_table(performance_summary)


# ============================================================
# 9. CURRENT MARKET STATE
# ============================================================

print_title("CURRENT MARKET STATE")

current_state_rows = []

for memory_type in ["DAILY", "WEEK", "MONTH", "YEAR"]:

    df = market_memory[
        market_memory["MemoryType"] == memory_type
    ].copy()

    if df.empty:
        continue

    latest = df.sort_values(
        "PeriodEndDate"
    ).iloc[-1]

    current_state_rows.append(
        {
            "MemoryType": memory_type,
            "Period": latest["MemoryLabel"],
            "PeriodStart": latest["PeriodStartDate"],
            "PeriodEnd": latest["PeriodEndDate"],
            "Close": latest["ClosePrice"],
            "ReturnPct": latest["ReturnPct"],
            "Direction": latest["Direction"],
            "DrawdownPct": latest["DrawdownPct"],
            "PeakDate": latest["PeakDate"],
            "NewATH": latest["IsNewAllTimeHigh"],
        }
    )


current_state = pd.DataFrame(
    current_state_rows
)

print_table(current_state)


# ============================================================
# 10. ATH SUMMARY
# ============================================================

print_title("ALL-TIME-HIGH SUMMARY")

daily_memory = market_memory[
    market_memory["MemoryType"] == "DAILY"
].copy()

if not daily_memory.empty:

    ath_count = int(
        daily_memory["IsNewAllTimeHigh"]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    highest_close = daily_memory[
        "ClosePrice"
    ].max()

    highest_close_row = daily_memory.loc[
        daily_memory["ClosePrice"].idxmax()
    ]

    print(f"New ATH Days             : {ath_count:,}")
    print(f"Highest Recorded Close   : {highest_close:,.2f}")
    print(
        "Highest Close Date       : "
        f"{highest_close_row['PeriodEndDate']}"
    )


# ============================================================
# 11. CONDITIONAL MEMORY SUMMARY
# ============================================================

print_title("CONDITIONAL MARKET MEMORY SUMMARY")

conditional_summary_rows = []

for direction in ["RED", "GREEN"]:

    df = conditional_memory[
        conditional_memory["CandleDirection"] == direction
    ].copy()

    if df.empty:
        continue

    following_returns = pd.to_numeric(
        df["FollowingWeekReturnPct"],
        errors="coerce",
    ).dropna()

    positive_count = int(
        (following_returns > 0).sum()
    )

    negative_count = int(
        (following_returns < 0).sum()
    )

    flat_count = int(
        (following_returns == 0).sum()
    )

    conditional_summary_rows.append(
        {
            "CandleDirection": direction,
            "HistoricalEvents": len(df),
            "PositiveFollowingWeeks": positive_count,
            "NegativeFollowingWeeks": negative_count,
            "FlatFollowingWeeks": flat_count,
            "PositiveProbabilityPct": (
                positive_count
                / len(following_returns)
                * 100
                if len(following_returns) > 0
                else None
            ),
            "NegativeProbabilityPct": (
                negative_count
                / len(following_returns)
                * 100
                if len(following_returns) > 0
                else None
            ),
            "AverageStreakReturnPct": pd.to_numeric(
                df["StreakReturnPct"],
                errors="coerce",
            ).mean(),
            "AverageFollowingWeekReturnPct": (
                following_returns.mean()
            ),
            "WorstFollowingWeekReturnPct": (
                following_returns.min()
            ),
            "BestFollowingWeekReturnPct": (
                following_returns.max()
            ),
        }
    )


conditional_summary = pd.DataFrame(
    conditional_summary_rows
)

print_table(conditional_summary)


# ============================================================
# 12. LONGEST STREAK SUMMARY
# ============================================================

print_title("LONGEST CONDITIONAL STREAKS")

streak_summary_rows = []

for direction in ["RED", "GREEN"]:

    df = conditional_memory[
        conditional_memory["CandleDirection"] == direction
    ].copy()

    if df.empty:
        continue

    longest_length = int(
        df["StreakLength"].max()
    )

    longest_events = df[
        df["StreakLength"] == longest_length
    ].copy()

    for _, row in longest_events.iterrows():

        streak_summary_rows.append(
            {
                "Direction": direction,
                "StreakLength": longest_length,
                "StartDate": row["StreakStartDate"],
                "EndDate": row["StreakEndDate"],
                "StreakReturnPct": row["StreakReturnPct"],
                "FollowingWeekReturnPct": row[
                    "FollowingWeekReturnPct"
                ],
                "FollowingWeekDirection": row[
                    "FollowingWeekDirection"
                ],
            }
        )


longest_streaks = pd.DataFrame(
    streak_summary_rows
)

print_table(longest_streaks)


# ============================================================
# 13. MAGNITUDE ANALYSIS
# ============================================================

print_title("CONDITIONAL MAGNITUDE ANALYSIS")

if not conditional_memory.empty:

    magnitude_summary = (
        conditional_memory
        .groupby(
            [
                "CandleDirection",
                "MagnitudeBucket",
            ],
            dropna=False,
        )
        .agg(
            Events=(
                "ConditionalMemoryID",
                "count",
            ),
            AverageStreakReturnPct=(
                "StreakReturnPct",
                "mean",
            ),
            AverageFollowingWeekReturnPct=(
                "FollowingWeekReturnPct",
                "mean",
            ),
        )
        .reset_index()
    )

    print_table(magnitude_summary)


# ============================================================
# 14. LATEST CONDITIONAL EVENT
# ============================================================

print_title("LATEST CONDITIONAL EVENT")

if not conditional_memory.empty:

    latest_event = conditional_memory.sort_values(
        "ConditionalMemoryID"
    ).iloc[-1]

    latest_event_df = pd.DataFrame(
        [
            {
                "Direction": latest_event[
                    "CandleDirection"
                ],
                "StreakStart": latest_event[
                    "StreakStartDate"
                ],
                "StreakEnd": latest_event[
                    "StreakEndDate"
                ],
                "StreakLength": latest_event[
                    "StreakLength"
                ],
                "StreakReturnPct": latest_event[
                    "StreakReturnPct"
                ],
                "FollowingWeekStart": latest_event[
                    "FollowingWeekStartDate"
                ],
                "FollowingWeekEnd": latest_event[
                    "FollowingWeekEndDate"
                ],
                "FollowingWeekReturnPct": latest_event[
                    "FollowingWeekReturnPct"
                ],
                "FollowingWeekDirection": latest_event[
                    "FollowingWeekDirection"
                ],
                "MagnitudeBucket": latest_event[
                    "MagnitudeBucket"
                ],
                "ResearchCondition": latest_event[
                    "ResearchCondition"
                ],
            }
        ]
    )

    print_table(latest_event_df)


# ============================================================
# 15. FINAL STATUS
# ============================================================

print_title("FINAL STATUS")

print("SUCCESS: Python analytics summary layer is working.")
print("Azure SQL → Python → Analytics Summary is connected.")
print("=" * 80)