import statsapi
from datetime import datetime, timedelta

def get_player_id(player_name):
    """
    Looks up a player's ID using their name.
    """
    people = statsapi.lookup_player(player_name)
    if people:
        # Assuming the first result is the correct player
        return people[0]['id']
    return None

def get_shohei_ohtani_game_data(num_games=10):
    """
    Fetches Shohei Ohtani's recent game data and current season stats.
    """
    ohtani_id = get_player_id("Shohei Ohtani")

    if not ohtani_id:
        print("Shohei Ohtani not found.")
        return

    print(f"Found Shohei Ohtani with ID: {ohtani_id}\n")

    # Get current date for recent games
    today = datetime.now()
    start_date = (today - timedelta(days=num_games * 2)).strftime('%m/%d/%Y') # Get enough days to cover num_games
    end_date = today.strftime('%m/%d/%Y')

    print(f"Fetching game logs from {start_date} to {end_date}...\n")
    # Fetch schedule for the Dodgers for the specified date range
    # We'll filter for Ohtani's stats from each game later
    dodgers_id = statsapi.lookup_team("Dodgers")[0]['id']
    schedule = statsapi.schedule(start_date=start_date, end_date=end_date, team=dodgers_id)

    game_logs = []
    # Iterate through games in reverse chronological order for "last X games"
    for game in reversed(schedule):
        if len(game_logs) >= num_games:
            break # Stop once we have enough games

        game_id = game['game_id']
        game_date = game['game_date']
        opponent = game['away_name'] if game['home_id'] == dodgers_id else game['home_name']

        try:
            # Get boxscore data for the game
            boxscore_data = statsapi.boxscore_data(game_id)

            # Find Ohtani's batting stats in the boxscore
            ohtani_stats = None
            for player_id, player_data in boxscore_data['playerInfo'].items():
                if int(player_id) == ohtani_id:
                    ohtani_stats = player_data
                    break

            if ohtani_stats:
                # Batting stats are usually under 'batting' or similar
                # The exact keys might vary, so we'll look for common ones
                batting_info = {}
                if 'batting' in ohtani_stats:
                    batting_info = ohtani_stats['batting']
                elif 'stats' in ohtani_stats and 'batting' in ohtani_stats['stats']:
                     batting_info = ohtani_stats['stats']['batting']

                if batting_info:
                    log_entry = {
                        "Date": game_date,
                        "Opp": opponent,
                        "AB": batting_info.get('atBats', 0),
                        "R": batting_info.get('runs', 0),
                        "H": batting_info.get('hits', 0),
                        "2B": batting_info.get('doubles', 0),
                        "3B": batting_info.get('triples', 0),
                        "HR": batting_info.get('homeRuns', 0),
                        "RBI": batting_info.get('rbi', 0),
                        "BB": batting_info.get('walks', 0),
                        "SO": batting_info.get('strikeOuts', 0),
                        "SB": batting_info.get('stolenBases', 0),
                        "CS": batting_info.get('caughtStealing', 0),
                        "AVG": batting_info.get('avg', 'N/A'),
                        "OBP": batting_info.get('obp', 'N/A'),
                        "SLG": batting_info.get('slg', 'N/A'),
                        "OPS": batting_info.get('ops', 'N/A'),
                    }
                    game_logs.append(log_entry)
                else:
                    print(f"No batting stats found for Ohtani in game {game_id} on {game_date}")
            else:
                print(f"Ohtani not found in boxscore for game {game_id} on {game_date}")

        except Exception as e:
            print(f"Error fetching boxscore for game {game_id} on {game_date}: {e}")

    print("\n--- Recent Game Logs ---\n")
    if game_logs:
        # Print header
        header = "| " + " | ".join(game_logs[0].keys()) + " |"
        print(header)
        print("|" + "---|" * len(game_logs[0].keys()))
        for log in game_logs:
            row = "| " + " | ".join([str(log[key]) for key in log.keys()]) + " |"
            print(row)
    else:
        print("No recent game logs found.")

    print("\n--- 2025 Season Stats ---\n")
    # Get career/season stats
    # The 'stats' endpoint can be tricky. We want season stats for 2025.
    # The API can return various stat types, 'season' is common.
    # If a specific year is not yielding data, try removing the year parameter to get career, then filter.
    try:
        player_stats = statsapi.player_stat_data(ohtani_id, stats='season', group='hitting', sportStatsType='regularSeason', year=2025)

        if player_stats and 'stats' in player_stats and len(player_stats['stats']) > 0:
            current_season_stats = player_stats['stats'][0]['stats']
            print("2025 Regular Season Hitting Stats:")
            for stat, value in current_season_stats.items():
                print(f"  {stat.replace('_', ' ').title()}: {value}")
        else:
            print("No 2025 season stats found for Shohei Ohtani.")
    except Exception as e:
        print(f"Error fetching 2025 season stats: {e}")

# Run the function
get_shohei_ohtani_game_data(num_games=10)