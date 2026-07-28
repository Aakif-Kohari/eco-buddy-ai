import sqlite3
import pandas as pd

DB_NAME = "eco_buddy.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            transport TEXT,
            distance REAL,
            electricity REAL,
            diet TEXT,
            flights INTEGER,
            footprint REAL,
            eco_score INTEGER
        )
    """)

    conn.commit()
    conn.close()


def save_assessment(
    transport,
    distance,
    electricity,
    diet,
    flights,
    footprint,
    eco_score
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO assessments (
            transport,
            distance,
            electricity,
            diet,
            flights,
            footprint,
            eco_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        transport,
        distance,
        electricity,
        diet,
        flights,
        footprint,
        eco_score
    ))

    conn.commit()
    conn.close()


def get_assessments():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM assessments
        ORDER BY date DESC
    """)

    data = cursor.fetchall()

    conn.close()
    return data


def get_assessments_df():
    """Return all assessment history as a labelled pandas DataFrame.

    Columns preserve the original database names so that downstream CSV
    consumers (e.g. Excel / Google Sheets) get self-documenting headers.
    Returns an empty DataFrame with the correct columns when no records exist.
    """
    columns = [
        "id", "date", "transport", "distance_km",
        "electricity_kwh", "diet", "flights",
        "footprint_kg_co2", "eco_score"
    ]
    data = get_assessments()
    return pd.DataFrame(data, columns=columns)