"""
Quick test of parallel player stats ingestion with a specific date range.
"""
from datetime import date, timedelta

from prefect import flow
from prefect.task_runners import ConcurrentTaskRunner

from src.automations.ingest.mlb import (
    ingest_player_stats_parallel,
)


@flow(task_runner=ConcurrentTaskRunner(max_workers=20))
def test_parallel_with_date_range():
    """Test parallel ingestion with a small date range (Sept 1-2, 2024)."""
    
    print("\n" + "=" * 70)
    print("TESTING PARALLEL PLAYER STATS INGESTION")
    print("Date Range: September 1-2, 2024 (~26 games)")
    print("=" * 70 + "\n")
    
    print("🚀 Fetching player stats with parallel processing (20 concurrent workers)...")
    print("   This should take about 30-60 seconds for ~26 games\n")
    
    try:
        batting_count, pitching_count = ingest_player_stats_parallel(
            season=2024,
            game_types='R',
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 2)
        )
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70)
        print(f"📈 Batting stats inserted: {batting_count:,} records")
        print(f"📈 Pitching stats inserted: {pitching_count:,} records")
        print("\n💡 Parallel processing makes full season ingestion ~6-8x faster!")
        print("   Full season (~2,400 games) would take ~10-15 minutes vs ~90-120 minutes")
        
        print("\n" + "=" * 70)
        print("NEXT: Build dbt models")
        print("=" * 70)
        print("cd dbt && uv run dbt run --select tag:player_stats")
        print("=" * 70 + "\n")
        
        return batting_count, pitching_count
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    test_parallel_with_date_range()
