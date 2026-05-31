# Job Market Data Pipeline Ingestion Layer

This repository contains the ingestion and load layer for the job market data
pipeline. It reads the raw job posting CSV, prepares the semi-structured fields,
and loads the raw records into PostgreSQL.

## Scope

This project only covers:

- Reads and ingests the raw `data_jobs.csv` file with pandas.
- Parsing semi-structured CSV columns into Python list and dictionary values.
- Loading raw records into a PostgreSQL staging table and schema.
- Logging ingestion and load progress while the pipeline runs.

## Design Decisions

The pipeline is split into two small stages so each part has one clear
responsibility:

- `src/ingest_data.py` reads the raw CSV from `src/data/data_jobs.csv` and parses
  `job_skills` and `job_type_skills` from text into structured Python values.
- `src/load_data.py` prepares the ingested data for PostgreSQL and loads it into
  the `stg.raw_jobs` table.

The staging table intentionally keeps the data close to the source file. This
preserves the raw job posting fields for downstream transformation while still
normalizing database friendly types such as timestamps, booleans, numerics, and
JSONB skill columns.

PostgreSQL is used as the load target because it is flexible and straightforward
to use for this staging layer. The load step uses an upsert on `raw_row_id` so
the pipeline can be re-run without creating duplicate rows.

The raw CSV file should be placed locally at `src/data/data_jobs.csv` before running the pipeline.

## Security and Configuration

Database credentials are not hardcoded in the source code. The load script reads
the PostgreSQL connection settings from environment variables stored in a local
`.env` file.

This keeps sensitive values such as the database user and password out of the
codebase. The `.env` file is ignored by Git, so each user should create it
locally before running the pipeline.

## Execution Instructions

1. Create and activate a Python virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the project dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with the PostgreSQL settings used by
   Docker and the load script:

   ```bash
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=job_market
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   ```

4. Add the raw CSV file at:

   ```text
   src/data/data_jobs.csv
   ```

5. Start PostgreSQL:

   ```bash
   docker compose up -d
   ```

6. Run the ingestion check:

   ```bash
   python src/ingest_data.py
   ```

7. Load the raw data into PostgreSQL:

   ```bash
   python src/load_data.py
   ```

After the load completes, the data will be available in `stg.raw_jobs`.

