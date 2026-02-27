#!/usr/bin/env python3
"""
Create the ml_mlb__model_predictions_raw table in BigQuery.
This is a one-time setup script for the ML inference integration.
"""

import os
import json
from google.cloud import bigquery

# Load credentials from .env
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-7dd4e548-9904-449d-9b7")
GCP_SERVICE_ACCOUNT_KEY = os.getenv("GCP_SERVICE_ACCOUNT_KEY")

if not GCP_SERVICE_ACCOUNT_KEY:
    raise ValueError("GCP_SERVICE_ACCOUNT_KEY not found in environment")

# Parse the service account JSON
credentials_info = json.loads(GCP_SERVICE_ACCOUNT_KEY)

# Initialize BigQuery client
from google.oauth2 import service_account
credentials = service_account.Credentials.from_service_account_info(credentials_info)
client = bigquery.Client(credentials=credentials, project=GCP_PROJECT_ID)

# Define the table
dataset_id = "mlb_modeling"
table_id = "ml_mlb__model_predictions_raw"
full_table_id = f"{GCP_PROJECT_ID}.{dataset_id}.{table_id}"

# Check if table already exists
try:
    client.get_table(full_table_id)
    print(f"✅ Table {full_table_id} already exists")

    # Show table info
    table = client.get_table(full_table_id)
    print(f"   - Created: {table.created}")
    print(f"   - Partitioning: {table.time_partitioning}")
    print(f"   - Clustering: {table.clustering_fields}")
    print(f"   - Num rows: {table.num_rows}")
    exit(0)

except Exception as e:
    print(f"Table does not exist yet. Creating {full_table_id}...")

# Define schema
schema = [
    bigquery.SchemaField("player_id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("game_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("pitcher_id", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("hit_probability", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("model_version", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("predicted_at", "TIMESTAMP", mode="REQUIRED"),
]

# Create table with partitioning and clustering
table = bigquery.Table(full_table_id, schema=schema)

# Set up time partitioning by game_date
table.time_partitioning = bigquery.TimePartitioning(
    type_=bigquery.TimePartitioningType.DAY,
    field="game_date"
)

# Set up clustering
table.clustering_fields = ["player_id", "pitcher_id"]

# Set description and labels
table.description = "Raw model predictions from ML inference pipeline. Populated daily by beat-the-streak-ml repo."
table.labels = {
    "source": "ml_inference",
    "league": "mlb"
}

# Create the table
try:
    table = client.create_table(table)
    print(f"✅ Successfully created table {full_table_id}")
    print(f"   - Partitioning: BY DAY on game_date")
    print(f"   - Clustering: player_id, pitcher_id")
    print(f"   - Schema: 7 columns")
    print(f"\nTable is ready for ML inference pipeline to write predictions!")

except Exception as e:
    print(f"❌ Error creating table: {e}")
    exit(1)
