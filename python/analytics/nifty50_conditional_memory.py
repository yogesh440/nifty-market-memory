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
# 3. LOAD CONDITIONAL MARKET MEMORY
# =========================================================

query = """
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
ORDER BY
    StreakEndDate,
    ConditionalMemoryID;
"""

df = pd.read_sql(query, engine)


# =========================================================
# 4. CONVERT DATE COLUMNS
# =========================================================

date_columns = [
    "StreakStartDate",
    "StreakEndDate",
    "FollowingWeekStartDate",
    "FollowingWeekEndDate",
    "CreatedAt",
]

for column in date_columns:
    df[column] = pd.to_datetime(df[column])


# =========================================================
# 5. BASIC DATA VALIDATION
# =========================================================

print("=" * 75)
print("NIFTY 50 CONDITIONAL MARKET MEMORY")
print("=" * 75)

print(f"\nTotal Events : {len(df):,}")

if not df.empty:
    print(f"Earliest Event : {df['StreakStartDate'].min().date()}")
    print(f"Latest Event   : {df['StreakStartDate'].max().date()}")


# =========================================================
# 6. RED / GREEN EVENT COUNTS
# =========================================================

print("\nEVENT COUNTS")
print("-" * 75)

event_counts = (
    df["CandleDirection"]
    .value_counts()
    .sort_index()
)

print(event_counts.to_string())


# =========================================================
# 7. COMPLETED FOLLOWING-WEEK EVENTS
# =========================================================

completed = df[
    df["FollowingWeekReturnPct"].notna()
].copy()

print("\nCOMPLETED FOLLOWING-WEEK EVENTS")
print("-" * 75)

print(
    f"Completed Events : {len(completed):,}"
)


# =========================================================
# 8. RED STREAK ANALYSIS
# =========================================================

red = completed[
    completed["CandleDirection"] == "RED"
].copy()

print("\nRED STREAK ANALYSIS")
print("-" * 75)

if red.empty:
    print("No completed RED events found.")
else:

    red_summary = (
        red.groupby("StreakLength")
        .agg(
            HistoricalOccurrences=("ConditionalMemoryID", "count"),
            AverageFollowingWeekReturnPct=(
                "FollowingWeekReturnPct",
                "mean",
            ),
            WorstFollowingWeekReturnPct=(
                "FollowingWeekReturnPct",
                "min",
            ),
            BestFollowingWeekReturnPct=(
                "FollowingWeekReturnPct",
                "max",
            ),
            FollowingWeekPositiveCount=(
                "FollowingWeekReturnPct",
                lambda x: (x > 0).sum(),
            ),
            FollowingWeekNegativeCount=(
                "FollowingWeekReturnPct",
                lambda x: (x < 0).sum(),
            ),
        )
        .reset_index()
        .sort_values("StreakLength")
    )

    red_summary[
        "FollowingWeekPositiveProbabilityPct"
    ] = (
        red_summary["FollowingWeekPositiveCount"]
        / red_summary["HistoricalOccurrences"]
        * 100
    )

    red_summary[
        "FollowingWeekNegativeProbabilityPct"
    ] = (
        red_summary["FollowingWeekNegativeCount"]
        / red_summary["HistoricalOccurrences"]
        * 100
    )

    print(
        red_summary.to_string(index=False)
    )


# =========================================================
# 9. GREEN STREAK ANALYSIS
# =========================================================

green = completed[
    completed["CandleDirection"] == "GREEN"
].copy()

print("\nGREEN STREAK ANALYSIS")
print("-" * 75)

if green.empty:
    print("No completed GREEN events found.")
else:

    green_summary = (
        green.groupby("StreakLength")
        .agg(
            HistoricalOccurrences=("ConditionalMemoryID", "count"),
            AverageFollowingWeekReturnPct=(
                "FollowingWeekReturnPct",
                "mean",
            ),
            WorstFollowingWeekReturnPct=(
                "FollowingWeekReturnPct",
                "min",
            ),
            BestFollowingWeekReturnPct=(
                "FollowingWeekReturnPct",
                "max",
            ),
            FollowingWeekPositiveCount=(
                "FollowingWeekReturnPct",
                lambda x: (x > 0).sum(),
            ),
            FollowingWeekNegativeCount=(
                "FollowingWeekReturnPct",
                lambda x: (x < 0).sum(),
            ),
        )
        .reset_index()
        .sort_values("StreakLength")
    )

    green_summary[
        "FollowingWeekPositiveProbabilityPct"
    ] = (
        green_summary["FollowingWeekPositiveCount"]
        / green_summary["HistoricalOccurrences"]
        * 100
    )

    green_summary[
        "FollowingWeekNegativeProbabilityPct"
    ] = (
        green_summary["FollowingWeekNegativeCount"]
        / green_summary["HistoricalOccurrences"]
        * 100
    )

    print(
        green_summary.to_string(index=False)
    )


# =========================================================
# 10. OVERALL RED / GREEN REVERSAL SUMMARY
# =========================================================

print("\nOVERALL REVERSAL SUMMARY")
print("-" * 75)

overall = (
    completed.groupby("CandleDirection")
    .agg(
        HistoricalOccurrences=("ConditionalMemoryID", "count"),
        PositiveFollowingWeeks=(
            "FollowingWeekReturnPct",
            lambda x: (x > 0).sum(),
        ),
        NegativeFollowingWeeks=(
            "FollowingWeekReturnPct",
            lambda x: (x < 0).sum(),
        ),
        FlatFollowingWeeks=(
            "FollowingWeekReturnPct",
            lambda x: (x == 0).sum(),
        ),
        AverageFollowingWeekReturnPct=(
            "FollowingWeekReturnPct",
            "mean",
        ),
        WorstFollowingWeekReturnPct=(
            "FollowingWeekReturnPct",
            "min",
        ),
        BestFollowingWeekReturnPct=(
            "FollowingWeekReturnPct",
            "max",
        ),
    )
    .reset_index()
)

overall[
    "PositiveProbabilityPct"
] = (
    overall["PositiveFollowingWeeks"]
    / overall["HistoricalOccurrences"]
    * 100
)

overall[
    "NegativeProbabilityPct"
] = (
    overall["NegativeFollowingWeeks"]
    / overall["HistoricalOccurrences"]
    * 100
)

print(
    overall.to_string(index=False)
)


# =========================================================
# 11. CURRENT / LATEST CONDITIONAL EVENT
# =========================================================

print("\nLATEST CONDITIONAL EVENT")
print("-" * 75)

if df.empty:
    print("No conditional events found.")
else:

    latest_event = (
        df.sort_values(
            "ConditionalMemoryID"
        )
        .tail(1)
    )

    print(
        latest_event[
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
                "ResearchCondition",
            ]
        ].to_string(index=False)
    )


# =========================================================
# 12. FINAL STATUS
# =========================================================

print("\nSUCCESS: Python conditional market memory analytics is working.")
print("=" * 75)