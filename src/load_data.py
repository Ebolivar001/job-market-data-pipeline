import logging
import os
from pathlib import Path
import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb
from ingest_data import extract_data

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

TABLE_SCHEMA = "stg"
TABLE_NAME = "raw_jobs"
FULL_TABLE_NAME = f"{TABLE_SCHEMA}.{TABLE_NAME}"
CHUNK_SIZE = 10000

TABLE_COLUMNS = [
    "raw_row_id",
    "job_title_short",
    "job_title",
    "job_location",
    "job_via",
    "job_schedule_type",
    "job_work_from_home",
    "search_location",
    "job_posted_date",
    "job_no_degree_mention",
    "job_health_insurance",
    "job_country",
    "salary_rate",
    "salary_year_avg",
    "salary_hour_avg",
    "company_name",
    "job_skills",
    "job_type_skills",
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_connection_config() -> dict:
    # Read database connection values from the environment variables
    load_dotenv(PROJECT_DIR / ".env")

    return {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT"),
        "dbname": os.getenv("POSTGRES_DB"),
        "user": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }


def create_table(cursor) -> None:
    # Create the staging schema and raw jobs table if they do not exist.
    logger.info("Creating schema and table if they do not exist")
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {TABLE_SCHEMA}")
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {FULL_TABLE_NAME} (
            raw_row_id BIGINT PRIMARY KEY,
            job_title_short TEXT,
            job_title TEXT,
            job_location TEXT,
            job_via TEXT,
            job_schedule_type TEXT,
            job_work_from_home BOOLEAN,
            search_location TEXT,
            job_posted_date TIMESTAMPTZ,
            job_no_degree_mention BOOLEAN,
            job_health_insurance BOOLEAN,
            job_country TEXT,
            salary_rate TEXT,
            salary_year_avg NUMERIC,
            salary_hour_avg NUMERIC,
            company_name TEXT,
            job_skills JSONB,
            job_type_skills JSONB,
            ingested_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
    )

def prepare_data(jobs_df: pd.DataFrame) -> pd.DataFrame:
    # Add a row id and clean date values before loading.
    logger.info("Preparing data before loading to PostgreSQL")
    jobs_df = jobs_df.copy()
    jobs_df.insert(0, "raw_row_id", jobs_df.index + 1)
    jobs_df["job_posted_date"] = pd.to_datetime(
        jobs_df["job_posted_date"],
        errors="coerce",
        utc=True,
    )

    return jobs_df[TABLE_COLUMNS]

def clean_value(value):
    # Convert pandas and output values into friendly values.
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, (list, dict)):
        return Jsonb(value)

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        return value.item()

    return value

def build_records(jobs_df: pd.DataFrame) -> list:
    # Convert the df rows into tuples for inserting.
    records = []

    for row in jobs_df.itertuples(index=False, name=None):
        records.append(tuple(clean_value(value) for value in row))

    return records

def upsert_jobs(cursor, records: list) -> None:
    # Insert rows or update them when the raw row id already exists.
    columns = ", ".join(TABLE_COLUMNS)
    placeholders = ", ".join(["%s"] * len(TABLE_COLUMNS))
    update_columns = [column for column in TABLE_COLUMNS if column != "raw_row_id"]
    update_statement = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in update_columns
    )

    upsert_query = f"""
        INSERT INTO {FULL_TABLE_NAME} ({columns})
        VALUES ({placeholders})
        ON CONFLICT (raw_row_id)
        DO UPDATE SET
            {update_statement},
            ingested_at = NOW()
    """

    cursor.executemany(upsert_query, records)


def load_data_to_postgres() -> None:
    # Run the full data into postgresql
    jobs_df = prepare_data(extract_data())

    logger.info("Connecting to PostgreSQL")
    with psycopg.connect(**get_connection_config()) as connection:
        with connection.cursor() as cursor:
            create_table(cursor)

            logger.info("Upserting %s rows into %s", len(jobs_df), FULL_TABLE_NAME)
            for start in range(0, len(jobs_df), CHUNK_SIZE):
                chunk = jobs_df.iloc[start:start + CHUNK_SIZE]
                records = build_records(chunk)
                upsert_jobs(cursor, records)
                logger.info("Upserted rows %s to %s", start + 1, start + len(chunk))

        connection.commit()
        logger.info("Changes committed to PostgreSQL")

    logger.info("Data successfully upserted")


if __name__ == "__main__":
    load_data_to_postgres()
