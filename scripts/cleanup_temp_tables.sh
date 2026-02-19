#!/bin/bash
# Clean up orphaned temporary BigQuery tables
# Run this occasionally if you're worried about leftover temp tables

set -e

PROJECT_ID="${GCP_PROJECT_ID}"
DATASET="raw"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID environment variable not set"
    exit 1
fi

echo "Checking for temp tables in ${PROJECT_ID}.${DATASET}..."

# List all tables ending with _temp*
bq ls --format=json --max_results=1000 "${PROJECT_ID}:${DATASET}" 2>/dev/null | \
    jq -r '.[] | select(.tableReference.tableId | test("_temp")) | .tableReference.tableId' | \
    while read -r table; do
        echo "  Found temp table: $table"
        bq rm -f -t "${PROJECT_ID}:${DATASET}.${table}"
        echo "  ✓ Deleted $table"
    done

echo "Cleanup complete!"
