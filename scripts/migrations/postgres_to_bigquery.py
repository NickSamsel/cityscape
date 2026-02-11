#!/usr/bin/env python3
"""Copy data from Cloud SQL (Postgres) to BigQuery"""

import os
from google.cloud import bigquery
import psycopg2

# BigQuery setup
project_id = os.environ['GCP_PROJECT_ID']
bq_client = bigquery.Client(project=project_id)

# Create datasets
print("Creating BigQuery datasets...")
for dataset_name in ['raw', 'analytics_stg', 'analytics_int', 'analytics_core']:
    dataset_id = f"{project_id}.{dataset_name}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    try:
        dataset = bq_client.create_dataset(dataset, exists_ok=True)
        print(f"✓ Created dataset {dataset_name}")
    except Exception as e:
        print(f"✗ Error creating {dataset_name}: {e}")

# Postgres connection
pg_conn = psycopg2.connect(
    host=os.environ['DBT_HOST'],
    port=5432,
    user=os.environ['DBT_USER'],
    password=os.environ['DBT_PASSWORD'],
    database=os.environ['DBT_DBNAME']
)

# Copy MLB tables
tables = ['mlb_games', 'mlb_teams']

for table in tables:
    print(f"\nCopying {table}...")
    
    # Query from Postgres
    query = f"SELECT * FROM raw.{table}"
    df = None
    
    try:
        import pandas as pd
        df = pd.read_sql(query, pg_conn)
        print(f"  Read {len(df)} rows from Postgres")
        
        # Load to BigQuery
        table_id = f"{project_id}.raw.{table}"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE",
        )
        
        job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        
        print(f"✓ Loaded {len(df)} rows to BigQuery raw.{table}")
        
    except Exception as e:
        print(f"✗ Error copying {table}: {e}")

pg_conn.close()
print("\n✓ Data migration complete!")
