#!/usr/bin/env python3
"""
Debug script to test all fantasy data functions with interactive selector
"""

import os
import json
import sys
from dotenv import load_dotenv
from espn_api.football import League
from fantasy_data import (
    identify_my_team,
    get_waiver_wire_for_tool,
    get_team_details_for_tool,
    get_player_stats_for_tool,
    get_lightweight_roster_summary,
    get_minimal_league_standings,
    get_concise_opponent_summary,
    fetch_preseason_rosters
)

def display_menu():
    """Display the available tool options"""
    print("\n" + "="*60)
    print("FANTASY DATA FUNCTION SELECTOR")
    print("="*60)
    print("1.  get_waiver_wire_for_tool")
    print("2.  get_team_details_for_tool")
    print("3.  get_player_stats_for_tool")
    print("4.  get_lightweight_roster_summary")
    print("5.  get_minimal_league_standings")
    print("6.  get_concise_opponent_summary")
    print("7.  identify_my_team")
    print("8.  fetch_preseason_rosters")
    print("0.  Exit")
    print("="*60)

def get_user_input(prompt, input_type=str, default=None, choices=None):
    """Get user input with validation"""
    while True:
        try:
            if default is not None:
                user_input = input(f"{prompt} (default: {default}): ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()
                
            if input_type == int:
                result = int(user_input)
            elif input_type == bool:
                result = user_input.lower() in ['true', 't', 'yes', 'y', '1']
            else:
                result = user_input
                
            if choices and result not in choices:
                print(f"Please choose from: {choices}")
                continue
                
            return result
        except ValueError:
            print(f"Please enter a valid {input_type.__name__}")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

def test_function(choice, league, my_team):
    """Test the selected function"""
    print(f"\n{'='*60}")
    print(f"TESTING FUNCTION #{choice}")
    print(f"{'='*60}")
    
    try:
        if choice == 1:
            # get_waiver_wire_for_tool
            position = get_user_input("Position filter (QB/RB/WR/TE/K/D/ST or leave blank for all)", default=None)
            if position == "":
                position = None
            size = get_user_input("Number of players", int, default=5)
            print(f"Testing: get_waiver_wire_for_tool(league, position={position}, size={size})")
            result = get_waiver_wire_for_tool(league, position=position, size=size)
            
        elif choice == 2:
            # get_team_details_for_tool
            print("Available teams:")
            for i, team in enumerate(league.teams):
                print(f"  Team ID {team.team_id if hasattr(team, 'team_id') else i+1}: {team.team_name}")
            
            team_id = get_user_input("Team ID", int)
            print(f"Testing: get_team_details_for_tool(league, team_id={team_id})")
            result = get_team_details_for_tool(league, team_id=team_id)
            
        elif choice == 3:
            # get_player_stats_for_tool
            # First show some players from roster by using team details
            print("Getting your team details to show player IDs...")
            team_details = get_team_details_for_tool(league, my_team.team_id if hasattr(my_team, 'team_id') else 1)
            if 'lineup' in team_details:
                print("Players from your roster:")
                all_players = team_details['lineup']['starters'] + team_details['lineup']['bench']
                for player in all_players[:10]:  # Show first 10 players
                    if player.get('player_id'):
                        print(f"  Player ID {player['player_id']}: {player['name']} ({player['position']})")
            
            player_id = get_user_input("Player ID", int)
            print(f"Testing: get_player_stats_for_tool(league, player_id={player_id})")
            result = get_player_stats_for_tool(league, player_id=player_id)
            
        elif choice == 4:
            # get_lightweight_roster_summary
            print("Testing: get_lightweight_roster_summary(league, my_team)")
            result = get_lightweight_roster_summary(league, my_team)
            # This returns a string, not JSON
            print("RESULT:")
            print(result)
            return
            
        elif choice == 5:
            # get_minimal_league_standings
            print("Testing: get_minimal_league_standings(league)")
            result = get_minimal_league_standings(league)
            # This returns a string, not JSON
            print("RESULT:")
            print(result)
            return
            
        elif choice == 6:
            # get_concise_opponent_summary
            print("Testing: get_concise_opponent_summary(league, my_team)")
            result = get_concise_opponent_summary(league, my_team)
            # This returns a string, not JSON
            print("RESULT:")
            print(result)
            return
            
        elif choice == 7:
            # identify_my_team
            swid = os.getenv('SWID')
            print(f"Testing: identify_my_team(league, '{swid}')")
            result = identify_my_team(league, swid)
            if result:
                print(f"RESULT: Found team - {result.team_name}")
            else:
                print("RESULT: Team not found")
            return
            
        elif choice == 8:
            # fetch_preseason_rosters
            print("Testing: fetch_preseason_rosters(league)")
            result = fetch_preseason_rosters(league)
            print(f"RESULT: {result}")
            return
            
        # Display JSON result for functions that return structured data
        print("RESULT:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Error testing function: {e}")
        import traceback
        traceback.print_exc()

def main():
    load_dotenv()
    
    espn_s2 = os.getenv('ESPN_S2')
    swid = os.getenv('SWID')
    
    if not espn_s2 or not swid:
        print("Please set ESPN_S2 and SWID in your .env file")
        return
    
    league_id = os.getenv('LEAGUE_ID')
    if not league_id:
        print("Please add your LEAGUE_ID to your .env file")
        return
    league_id = int(league_id)
    
    year = os.getenv('YEAR')
    if not year:
        print("Please add your YEAR to your .env file")
        return
    year = int(year)
    
    print("Connecting to ESPN Fantasy...")
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    
    # Identify user's team
    my_team = identify_my_team(league, swid)
    if not my_team:
        print("Warning: Could not identify your team, using first team for testing")
        my_team = league.teams[0]
    
    print(f"✓ League: {league.settings.name}")
    print(f"✓ Your team: {my_team.team_name}")
    print(f"✓ Current Week: {league.current_week}")
    
    # Handle preseason
    if league.current_week == 0:
        print("⏰ Pre-season detected - fetching rosters...")
        fetch_preseason_rosters(league)
    
    # Interactive menu loop
    while True:
        display_menu()
        
        try:
            choice = int(input("Enter your choice (0-8): ").strip())
            
            if choice == 0:
                print("Goodbye!")
                break
            elif 1 <= choice <= 8:
                test_function(choice, league, my_team)
                
                # Ask if user wants to continue
                cont = input("\nPress Enter to continue, 'q' to quit: ").strip().lower()
                if cont == 'q':
                    break
            else:
                print("Invalid choice. Please enter a number between 0-8.")
                
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()