"""Debug script to inspect MLB Statcast data structure."""

import json
import sys

from src.integrations.mlb import MlbStatsApi


def inspect_game_data(game_id: int):
    """Inspect the structure of play-by-play data for a game."""
    api = MlbStatsApi()
    
    print(f"Fetching play-by-play data for game {game_id}...")
    try:
        payload = api._get_json("game_playByPlay", {"gamePk": game_id})
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
    
    all_plays = payload.get("allPlays", [])
    print(f"\nFound {len(all_plays)} plays in game {game_id}\n")
    
    # Find a play with hit data
    plays_with_hit_data = []
    plays_with_hit_data_in_events = []
    
    for i, play in enumerate(all_plays[:20]):  # Check first 20 plays
        if not isinstance(play, dict):
            continue
        
        # Check play result level
        result = play.get("result", {})
        play_events = play.get("playEvents", [])
        
        # Check for hitData in result
        if isinstance(result, dict) and "hitData" in result:
            plays_with_hit_data.append(i)
        
        # Check for hitData in events
        for event in play_events:
            if isinstance(event, dict) and "hitData" in event:
                plays_with_hit_data_in_events.append(i)
                break
    
    print(f"Plays with hitData in result: {plays_with_hit_data}")
    print(f"Plays with hitData in events: {plays_with_hit_data_in_events}")
    
    # Show structure of first play with hit data
    if plays_with_hit_data:
        idx = plays_with_hit_data[0]
        play = all_plays[idx]
        print(f"\n{'='*80}")
        print(f"Structure of play {idx} (has hitData in result):")
        print(f"{'='*80}")
        
        result = play.get("result", {})
        print(f"\nResult keys: {list(result.keys())}")
        
        if "hitData" in result:
            print(f"\nHit Data structure:")
            print(json.dumps(result["hitData"], indent=2))
    
    elif plays_with_hit_data_in_events:
        idx = plays_with_hit_data_in_events[0]
        play = all_plays[idx]
        print(f"\n{'='*80}")
        print(f"Structure of play {idx} (has hitData in events):")
        print(f"{'='*80}")
        
        for event in play.get("playEvents", []):
            if isinstance(event, dict) and "hitData" in event:
                print(f"\nEvent keys: {list(event.keys())}")
                print(f"\nHit Data structure:")
                print(json.dumps(event["hitData"], indent=2))
                break
    
    else:
        print(f"\n⚠️  No plays with hitData found in first 20 plays!")
        print(f"\nShowing structure of first play:")
        if all_plays:
            play = all_plays[0]
            print(f"\nPlay keys: {list(play.keys())}")
            print(f"\nResult keys: {list(play.get('result', {}).keys())}")
            print(f"\nFirst event keys: {list(play.get('playEvents', [{}])[0].keys())}")
            
            # Show a sample event
            if play.get("playEvents"):
                print(f"\nSample event structure:")
                print(json.dumps(play["playEvents"][0], indent=2)[:2000])


if __name__ == "__main__":
    # Default to a recent game
    game_id = int(sys.argv[1]) if len(sys.argv) > 1 else 746089
    inspect_game_data(game_id)
