import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus


# ============================================================
# NIFTY 50 DATA VALIDATION
# Python -> Azure SQL
# ============================================================


# ============================================================
# 1. LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")


# ============================================================
# 2. CHECK ENVIRONMENT VARIABLES
# ============================================================

required_variables = {
    "SQL_SERVER": SQL_SERVER,
    "SQL_DATABASE": SQL_DATABASE,
    "SQL_USERNAME": SQL_USERNAME,
    "SQL_PASSWORD": SQL_PASSWORD,
}

missing_variables = [
    name
    for name, value in required_variables.items()
    if not value
]

if missing_variables:
    raise ValueError(
        "Missing environment variables: "
        + ", ".join(missing_variables)
    )


# ============================================================
# 3. CREATE AZURE SQL CONNECTION
# ============================================================

connection_string = (
    "mssql+pyodbc://"
    f"{quote_plus(SQL_USERNAME)}:"
    f"{quote_plus(SQL_PASSWORD)}@"
    f"{SQL_SERVER}:1433/"
    f"{SQL_DATABASE}"
    "?driver=ODBC+Driver+18+for+SQL+Server"
    "&Encrypt=yes"
    "&TrustServerCertificate=no"
    "&Connection+Timeout=30"
)

engine = create_engine(connection_string)


# ============================================================
# 4. HELPER FUNCTION
# ============================================================

def run_query(query):
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection)


# ============================================================
# 5. START VALIDATION
# ============================================================

print("=" * 75)
print("NIFTY 50 DATA VALIDATION")
print("=" * 75)


validation_results = []


# ============================================================
# 6. PRICE TABLE VALIDATION
# ============================================================

price_query = """
SELECT
    COUNT(*) AS TotalRows,
    MIN(HistoricalDate) AS EarliestDate,
    MAX(HistoricalDate) AS LatestDate,
    SUM(
        CASE
            WHEN HistoricalDate IS NULL THEN 1
            ELSE 0
        END
    ) AS MissingDates,
    SUM(
        CASE
            WHEN ClosePrice IS NULL THEN 1
            ELSE 0
        END
    ) AS MissingClose
FROM dbo.Nifty50_Price;
"""

price = run_query(price_query).iloc[0]


duplicate_price_query = """
SELECT COUNT(*) AS DuplicateDateGroups
FROM
(
    SELECT HistoricalDate
    FROM dbo.Nifty50_Price
    GROUP BY HistoricalDate
    HAVING COUNT(*) > 1
) AS DuplicateDates;
"""

duplicate_price = run_query(
    duplicate_price_query
).iloc[0]


print("\nPRICE TABLE")
print("-" * 75)
print(f"Rows             : {price['TotalRows']}")
print(f"Earliest date    : {price['EarliestDate']}")
print(f"Latest date      : {price['LatestDate']}")
print(f"Missing dates    : {price['MissingDates']}")
print(f"Missing close    : {price['MissingClose']}")
print(
    f"Duplicate dates  : "
    f"{duplicate_price['DuplicateDateGroups']}"
)


price_checks = [
    price["TotalRows"] > 0,
    price["EarliestDate"] is not None,
    price["LatestDate"] is not None,
    price["MissingDates"] == 0,
    price["MissingClose"] == 0,
    duplicate_price["DuplicateDateGroups"] == 0,
]

price_status = all(price_checks)

validation_results.append(
    ("Price Table", price_status)
)


# ============================================================
# 7. TOTAL RETURN TABLE VALIDATION
# ============================================================

tr_query = """
SELECT
    COUNT(*) AS TotalRows,
    MIN(HistoricalDate) AS EarliestDate,
    MAX(HistoricalDate) AS LatestDate,
    SUM(
        CASE
            WHEN HistoricalDate IS NULL THEN 1
            ELSE 0
        END
    ) AS MissingDates,
    SUM(
        CASE
            WHEN TotalReturnIndex IS NULL THEN 1
            ELSE 0
        END
    ) AS MissingTRIndex,
    SUM(
        CASE
            WHEN NTRValue IS NULL THEN 1
            ELSE 0
        END
    ) AS MissingNTRValue
FROM dbo.Nifty50_TR;
"""

tr = run_query(tr_query).iloc[0]


duplicate_tr_query = """
SELECT COUNT(*) AS DuplicateDateGroups
FROM
(
    SELECT HistoricalDate
    FROM dbo.Nifty50_TR
    GROUP BY HistoricalDate
    HAVING COUNT(*) > 1
) AS DuplicateDates;
"""

duplicate_tr = run_query(
    duplicate_tr_query
).iloc[0]


print("\nTOTAL RETURN TABLE")
print("-" * 75)
print(f"Rows             : {tr['TotalRows']}")
print(f"Earliest date    : {tr['EarliestDate']}")
print(f"Latest date      : {tr['LatestDate']}")
print(f"Missing dates    : {tr['MissingDates']}")
print(f"Missing TR index : {tr['MissingTRIndex']}")
print(f"Missing NTR      : {tr['MissingNTRValue']}")
print(
    f"Duplicate dates  : "
    f"{duplicate_tr['DuplicateDateGroups']}"
)


# NTRValue has a known historical exception:
# 1999-06-30 through 1999-12-30.
#
# Therefore historical NTR NULLs are documented
# and are NOT treated as a validation failure.

tr_checks = [
    tr["TotalRows"] > 0,
    tr["EarliestDate"] is not None,
    tr["LatestDate"] is not None,
    tr["MissingDates"] == 0,
    tr["MissingTRIndex"] == 0,
    duplicate_tr["DuplicateDateGroups"] == 0,
]

tr_status = all(tr_checks)

validation_results.append(
    ("Total Return Table", tr_status)
)


# ============================================================
# 8. MARKET MEMORY VALIDATION
# ============================================================

memory_query = """
SELECT
    COUNT(*) AS TotalRows,
    COUNT(DISTINCT MemoryType) AS MemoryTypeCount,
    MIN(PeriodStartDate) AS EarliestDate,
    MAX(PeriodEndDate) AS LatestDate
FROM dbo.Nifty50_MarketMemory;
"""

memory = run_query(memory_query).iloc[0]


print("\nMARKET MEMORY")
print("-" * 75)
print(f"Rows             : {memory['TotalRows']}")
print(f"Memory types     : {memory['MemoryTypeCount']}")
print(f"Earliest date    : {memory['EarliestDate']}")
print(f"Latest date      : {memory['LatestDate']}")


memory_checks = [
    memory["TotalRows"] > 0,
    memory["MemoryTypeCount"] == 4,
    memory["EarliestDate"] is not None,
    memory["LatestDate"] is not None,
]

memory_status = all(memory_checks)

validation_results.append(
    ("Market Memory", memory_status)
)


# ============================================================
# 9. CONDITIONAL MARKET MEMORY VALIDATION
# ============================================================

conditional_query = """
SELECT
    COUNT(*) AS TotalRows,
    COUNT(DISTINCT CandleDirection) AS DirectionCount,
    MIN(StreakStartDate) AS EarliestEvent,
    MAX(StreakEndDate) AS LatestEvent
FROM dbo.Nifty50_ConditionalMarketMemory;
"""

conditional = run_query(
    conditional_query
).iloc[0]


print("\nCONDITIONAL MARKET MEMORY")
print("-" * 75)
print(f"Rows             : {conditional['TotalRows']}")
print(f"Directions       : {conditional['DirectionCount']}")
print(f"Earliest event   : {conditional['EarliestEvent']}")
print(f"Latest event     : {conditional['LatestEvent']}")


conditional_checks = [
    conditional["TotalRows"] > 0,
    conditional["DirectionCount"] == 2,
    conditional["EarliestEvent"] is not None,
    conditional["LatestEvent"] is not None,
]

conditional_status = all(conditional_checks)

validation_results.append(
    ("Conditional Market Memory", conditional_status)
)


# ============================================================
# 10. FINAL VALIDATION SUMMARY
# ============================================================

print("\n")
print("=" * 75)
print("VALIDATION SUMMARY")
print("=" * 75)


overall_status = True


for name, status in validation_results:

    result = "PASS" if status else "FAIL"

    print(
        f"{name:<35} : {result}"
    )

    if not status:
        overall_status = False


print("-" * 75)


if overall_status:

    print("OVERALL STATUS : PASS")
    print("All critical data-quality checks passed.")

else:

    print("OVERALL STATUS : FAIL")
    print("One or more data-quality checks failed.")


print("=" * 75)


# ============================================================
# 11. FINAL STATUS
# ============================================================

if not overall_status:
    raise SystemExit(1)


print(
    "\nSUCCESS: Python data validation layer is working."
)