#!/usr/bin/env python3
"""
Create the modeling dataset in BigQuery if it doesn't exist.
"""

import os
import json
from google.cloud import bigquery
from google.oauth2 import service_account

# Load credentials from .env
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "project-7dd4e548-9904-449d-9b7")
GCP_SERVICE_ACCOUNT_KEY = os.getenv("GCP_SERVICE_ACCOUNT_KEY")

if not GCP_SERVICE_ACCOUNT_KEY:
    raise ValueError("GCP_SERVICE_ACCOUNT_KEY not found in environment")

# Parse the service account JSON
credentials_info = json.loads(GCP_SERVICE_ACCOUNT_KEY)
credentials = service_account.Credentials.from_service_account_info(credentials_info)
client = bigquery.Client(credentials=credentials, project=GCP_PROJECT_ID)

# Define dataset
dataset_id = "modeling"
full_dataset_id = f"{GCP_PROJECT_ID}.{dataset_id}"

# Check if dataset exists
try:
    client.get_dataset(full_dataset_id)
    print(f"✅ Dataset {full_dataset_id} already exists")
except Exception:
    print(f"Creating dataset {full_dataset_id}...")

    # Create dataset
    dataset = bigquery.Dataset(full_dataset_id)
    dataset.location = "US"  # or your preferred location
    dataset.description = "ML modeling tables including prediction datasets and outcomes"

    try:
        dataset = client.create_dataset(dataset, timeout=30)
        print(f"✅ Successfully created dataset {full_dataset_id}")
    except Exception as e:
        print(f"❌ Error creating dataset: {e}")
        exit(1)
