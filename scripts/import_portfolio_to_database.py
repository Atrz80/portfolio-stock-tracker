import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


project_root = Path(__file__).resolve().parents[1]
portfolio_path = project_root / "portfolio.json"
database_url = os.getenv("PORTFOLIO_DATABASE_URL")

if not database_url:
    raise SystemExit("Set PORTFOLIO_DATABASE_URL to the hosted PostgreSQL connection string.")
if not portfolio_path.is_file():
    raise SystemExit(f"Portfolio file not found: {portfolio_path}")

with portfolio_path.open(encoding="utf-8") as portfolio_file:
    positions = json.load(portfolio_file)
if not isinstance(positions, list) or not all(isinstance(item, dict) for item in positions):
    raise SystemExit("The portfolio file must contain a JSON array of position objects.")

with psycopg.connect(database_url, connect_timeout=10) as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_state (
                id SMALLINT PRIMARY KEY CHECK (id = 1),
                positions JSONB NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cursor.execute(
            "SELECT positions FROM portfolio_state WHERE id = 1 FOR UPDATE"
        )
        if cursor.fetchone():
            raise SystemExit(
                "The hosted portfolio already contains data; refusing to overwrite it."
            )
        cursor.execute(
            """
            INSERT INTO portfolio_state (id, positions, updated_at)
            VALUES (1, %s, NOW())
            """,
            (Jsonb(positions),),
        )

print(f"Imported {len(positions)} positions into the hosted database.")
