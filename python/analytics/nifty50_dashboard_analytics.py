import os
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


# =========================================================
# 1. LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

server = os.getenv("SQL_SERVER")
database = os.getenv("SQL_DATABASE")
username = os.getenv("SQL_USERNAME")
password = os.getenv("SQL_PASSWORD")


if not all([server, database, username, password]):
    raise ValueError(
        "Missing SQL connection settings. Check the .env file."
    )


# =========================================================
# 2. CREATE AZURE SQL CONNECTION
# =========================================================

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


# =========================================================
# 3. LOAD DASHBOARD CURRENT STATE
# =========================================================

current_state_query = """
SELECT
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
FROM dbo.Nifty50_Dashboard_CurrentState
ORDER BY
    CASE MemoryType
        WHEN 'DAILY' THEN 1
        WHEN 'WEEK' THEN 2
        WHEN 'MONTH' THEN 3
        WHEN 'YEAR' THEN 4
        ELSE 5
    END;
"""

current_state = pd.read_sql(
    current_state_query,
    engine
)


# =========================================================
# 4. LOAD CONDITIONAL SUMMARY
# =========================================================

conditional_summary_query = """
SELECT
    CandleDirection,
    HistoricalCompletedEvents,
    PositiveFollowingWeeks,
    NegativeFollowingWeeks,
    FlatFollowingWeeks,
    PositiveProbabilityPct,
    NegativeProbabilityPct,
    AverageStreakReturnPct,
    AverageFollowingWeekReturnPct,
    WorstFollowingWeekReturnPct,
    BestFollowingWeekReturnPct
FROM dbo.Nifty50_Dashboard_ConditionalSummary
ORDER BY
    CASE CandleDirection
        WHEN 'RED' THEN 1
        WHEN 'GREEN' THEN 2
        ELSE 3
    END;
"""

conditional_summary = pd.read_sql(
    conditional_summary_query,
    engine
)


# =========================================================
# 5. LOAD ACTIVE CONDITIONAL EVENT
# =========================================================

active_event_query = """
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
    EventStatus,
    CreatedAt
FROM dbo.Nifty50_Dashboard_ActiveConditionalEvent;
"""

active_event = pd.read_sql(
    active_event_query,
    engine
)


# =========================================================
# 6. DISPLAY CURRENT MARKET STATE
# =========================================================

print("=" * 70)
print("NIFTY 50 DASHBOARD ANALYTICS")
print("=" * 70)

print("\nCURRENT MARKET STATE")
print("-" * 70)

print(
    current_state[
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


# =========================================================
# 7. DISPLAY CONDITIONAL MARKET MEMORY
# =========================================================

print("\nCONDITIONAL MARKET MEMORY")
print("-" * 70)

print(
    conditional_summary.to_string(index=False)
)


# =========================================================
# 8. DISPLAY ACTIVE CONDITIONAL EVENT
# =========================================================

print("\nACTIVE CONDITIONAL EVENT")
print("-" * 70)

if active_event.empty:
    print("No active conditional event found.")
else:
    print(
        active_event[
            [
                "ConditionalMemoryID",
                "CandleDirection",
                "StreakStartDate",
                "StreakEndDate",
                "StreakLength",
                "StreakReturnPct",
                "FollowingWeekStartDate",
                "FollowingWeekEndDate",
                "FollowingWeekReturnPct",
                "FollowingWeekDirection",
                "MagnitudeBucket",
                "EventStatus",
            ]
        ].to_string(index=False)
    )


# =========================================================
# 9. BASIC DATA VALIDATION
# =========================================================

print("\nDATASET VALIDATION")
print("-" * 70)

print(
    f"Current State Rows       : {len(current_state)}"
)

print(
    f"Conditional Summary Rows : {len(conditional_summary)}"
)

print(
    f"Active Event Rows        : {len(active_event)}"
)


# =========================================================
# 10. FINAL STATUS
# =========================================================

print("\nSUCCESS: Python dashboard analytics layer is working.")
print("=" * 70)