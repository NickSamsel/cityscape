"""
Quick test script to verify the MLB player stats ingestion pipeline.

This fetches player stats for a small sample of games to validate the pipeline.
"""
from datetime import date

from src.integrations.mlb.statsapi import MlbStatsApi


def test_player_stats_integration():
    """Test fetching player stats from the MLB Stats API."""
    
    print("Testing MLB Player Stats Integration")
    print("=" * 60)
    
    api = MlbStatsApi()
    
    # Get a few games from September 2024
    print("\n1. Fetching sample games from September 2024...")
    games = api.list_games(
        season=2024,
        game_types="R",
        start_date=date(2024, 9, 1),
        end_date=date(2024, 9, 2)
    )
    
    print(f"   Found {len(games)} games")
    
    if not games:
        print("   ❌ No games found. Try a different date range.")
        return
    
    # Test fetching player stats for the first game
    game = games[0]
    print(f"\n2. Fetching player stats for game_id={game.game_id}...")
    print(f"   Game: {game.game_date} - Status: {game.status}")
    
    try:
        batting_stats, pitching_stats = api.get_player_game_stats(game_id=game.game_id)
        
        print(f"   ✓ Found {len(batting_stats)} batting stat records")
        print(f"   ✓ Found {len(pitching_stats)} pitching stat records")
        
        # Show sample batting stats
        if batting_stats:
            print("\n3. Sample batting stats:")
            for i, batter in enumerate(batting_stats[:3], 1):
                print(f"   {i}. {batter.player_name} ({batter.position}): "
                      f"{batter.hits}H/{batter.at_bats}AB, {batter.home_runs}HR, {batter.rbi}RBI")
        
        # Show sample pitching stats
        if pitching_stats:
            print("\n4. Sample pitching stats:")
            for i, pitcher in enumerate(pitching_stats[:3], 1):
                print(f"   {i}. {pitcher.player_name}: "
                      f"{pitcher.innings_pitched}IP, {pitcher.strikeouts}K, {pitcher.earned_runs}ER")
        
        print("\n" + "=" * 60)
        print("✓ Integration test PASSED!")
        print("\nYou can now run the full ingestion pipeline:")
        print("  uv run python -c \"from src.automations.prefect.mlb import mlb_player_stats_season_ingestion; mlb_player_stats_season_ingestion(season=2024)\"")
        
    except Exception as e:
        print(f"   ❌ Error fetching player stats: {e}")
        raise


if __name__ == "__main__":
    test_player_stats_integration()
