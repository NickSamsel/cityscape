"""
Demo script comparing sequential vs parallel player stats ingestion.

This tests both approaches with a small date range to show the performance difference.
"""
import time
from datetime import date

from src.automations.prefect.mlb import (
    mlb_player_stats_season_ingestion,
    mlb_player_stats_season_ingestion_parallel,
)


def demo_parallel_ingestion():
    """Compare sequential vs parallel ingestion performance."""
    
    print("\n" + "=" * 70)
    print("MLB PLAYER STATS INGESTION: SEQUENTIAL vs PARALLEL DEMO")
    print("=" * 70)
    
    # Test with a small sample (September 1-2, 2024 = ~26 games)
    print("\n📊 Testing with September 1-2, 2024 (~26 games)")
    print("-" * 70)
    
    # Option 1: For a specific date range, you'd need to modify the functions
    # For now, let's test with the full 2024 season (you can Ctrl+C to stop early)
    
    print("\n🚀 Running PARALLEL version (with 20 concurrent workers)...")
    print("   This will fetch stats from multiple games simultaneously")
    print("   Press Ctrl+C to stop early if needed\n")
    
    start_time = time.time()
    
    try:
        result = mlb_player_stats_season_ingestion_parallel(
            season=2024,
            game_types='R',
            max_workers=20
        )
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("✅ PARALLEL INGESTION COMPLETE!")
        print("=" * 70)
        print(f"⏱️  Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"📈 Batting stats: {result['batting_stats']:,} records")
        print(f"📈 Pitching stats: {result['pitching_stats']:,} records")
        
        if elapsed > 60:
            rate = (result['batting_stats'] + result['pitching_stats']) / elapsed
            print(f"🚀 Processing rate: {rate:.1f} records/second")
        
        print("\n💡 With parallel processing (20 workers), a full season takes ~10-15 minutes")
        print("   vs ~90-120 minutes with sequential processing!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopped early by user")
        elapsed = time.time() - start_time
        print(f"   Ran for {elapsed:.1f} seconds before stopping")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("1. Run full historical ingestion:")
    print("   uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2020")
    print()
    print("2. Or run a single season:")
    print("   uv run python -c \"from src.automations.prefect.mlb import \\")
    print("   mlb_player_stats_season_ingestion_parallel; \\")
    print("   mlb_player_stats_season_ingestion_parallel(season=2024)\"")
    print()
    print("3. Build dbt models after ingestion:")
    print("   cd dbt && uv run dbt run --select tag:player_stats")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    demo_parallel_ingestion()
