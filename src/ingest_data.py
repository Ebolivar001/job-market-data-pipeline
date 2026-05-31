import ast
import logging
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_JOBS_PATH = BASE_DIR / "data" / "data_jobs.csv"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_python_value(value):
    if pd.isna(value):
        return None

    # Convert CSV text into a real list or dict.
    return ast.literal_eval(value)


def parse_semi_structured_columns(jobs_df: pd.DataFrame) -> pd.DataFrame:
    # Parse skill columns from text into lists and dictionaries for better handling in the database.
    jobs_df = jobs_df.copy()
    jobs_df["job_skills"] = jobs_df["job_skills"].apply(parse_python_value)
    jobs_df["job_type_skills"] = jobs_df["job_type_skills"].apply(parse_python_value)

    return jobs_df


def extract_data(data_jobs_path: Path = DATA_JOBS_PATH) -> pd.DataFrame:
    # Read the CSV file and prepare the skill columns.
    logger.info("Reading data from %s", data_jobs_path)
    jobs_df = pd.read_csv(data_jobs_path)

    logger.info("Parsing semi-structured columns")
    jobs_df = parse_semi_structured_columns(jobs_df)

    logger.info("Finished reading %s rows", len(jobs_df))
    return jobs_df


def print_structured_data(jobs_df: pd.DataFrame) -> None:
    # This outputs a quick check that the skill columns were parsed properly.
    skills_examples = jobs_df["job_skills"].dropna()
    type_skills_examples = jobs_df["job_type_skills"].dropna()

    print(f"Read successfully {len(jobs_df)} rows")
    print(f"job_skills parsed as: {type(skills_examples.iloc[0]).__name__}")
    print(f"job_type_skills parsed as: {type(type_skills_examples.iloc[0]).__name__}")
    print("\n=== Structured data sample ===")
    print(jobs_df[["job_title_short", "job_skills", "job_type_skills"]].head())


if __name__ == "__main__":
    jobs_df = extract_data()
    print_structured_data(jobs_df)
