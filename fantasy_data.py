"""
ESPN Fantasy Football Data Functions
All functions for fetching and processing fantasy football data
"""

from espn_api.football import League

# 2025 NFL Bye Weeks
BYE_WEEKS = {
    "ARI": 8,
    "ATL": 5,
    "BAL": 7,
    "BUF": 7,
    "CAR": 14,
    "CHI": 5,
    "CIN": 10,
    "CLE": 9,
    "DAL": 10,
    "DEN": 12,
    "DET": 8,
    "GB": 5,
    "HOU": 6,
    "IND": 11,
    "JAX": 8,
    "KC": 10,
    "LV": 8,
    "LAC": 12,
    "LAR": 8,
    "MIA": 12,
    "MIN": 6,
    "NE": 14,
    "NO": 11,
    "NYG": 14,
    "NYJ": 9,
    "PHI": 9,
    "PIT": 5,
    "SF": 14,
    "SEA": 8,
    "TB": 9,
    "TEN": 10,
    "WSH": 12
}


def get_player_bye_week(player):
    """Get bye week for a player based on their NFL team"""
    if hasattr(player, 'proTeam') and player.proTeam in BYE_WEEKS:
        return BYE_WEEKS[player.proTeam]
    return None


def identify_my_team(league, swid):
    """Identify user's team in the league"""
    target_swid = swid.strip('{}').upper()  # Remove braces and normalize case
    my_team = None
    
    for team in league.teams:
        # Check if owner is marked as 'You'
        if hasattr(team, 'owner') and team.owner == 'You':
            my_team = team
            break
        
        # Check owners list for SWID match
        if hasattr(team, 'owners') and team.owners:
            for owner in team.owners:
                if isinstance(owner, dict) and 'id' in owner:
                    owner_id = owner['id'].strip('{}').upper()
                    if owner_id == target_swid:
                        my_team = team
                        return my_team
                elif isinstance(owner, str):
                    owner_clean = owner.strip('{}').upper()
                    if owner_clean == target_swid:
                        my_team = team
                        return my_team
    
    if not my_team:
        print(f"Warning: Could not identify your team using SWID {swid}")
        print("Available teams:")
        for i, team in enumerate(league.teams, 1):
            print(f"{i}. {team.team_name}")
        
        # Let user select their team
        while True:
            try:
                selection = int(input("\nSelect your team number: ")) - 1
                if 0 <= selection < len(league.teams):
                    my_team = league.teams[selection]
                    break
                else:
                    print("Invalid selection. Please try again.")
            except (ValueError, KeyboardInterrupt):
                print("Using first team as default.")
                my_team = league.teams[0]
                break
    
    return my_team


def fetch_preseason_rosters(league):
    """Fetch rosters for pre-season (week 0) when normal roster is empty"""
    try:
        # In pre-season, rosters might be empty but we can get drafted players
        for team in league.teams:
            if not team.roster or len(team.roster) == 0:
                # Try to fetch the team's roster using internal methods
                if hasattr(team, '_fetch_roster'):
                    team._fetch_roster()
    except Exception as e:
        print(f"Note: Could not fetch pre-season rosters: {e}")






def get_waiver_wire_for_tool(league, position=None, size=5):
    """Tool-callable method for AI to get waiver wire data - optimized for minimal tokens"""
    if position and position not in ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST', 'DST']:
        return {"error": f"Invalid position: {position}. Valid positions are QB, RB, WR, TE, K, D/ST"}
    
    # Handle DST vs D/ST naming
    if position == 'DST':
        position = 'D/ST'
        
    # Get waiver wire data inline instead of calling separate function
    fetch_size = 75 if position else 50
    free_agents = league.free_agents(size=fetch_size)
    
    waiver_players = []
    for player in free_agents:
        if position and hasattr(player, 'position') and player.position != position:
            continue
        
        # Get current week's projection - prioritize weekly over season average
        weekly_projection = 0
        if hasattr(player, 'stats') and isinstance(player.stats, dict):
            current_week = league.current_week
            if current_week in player.stats and 'projected_points' in player.stats[current_week]:
                weekly_projection = player.stats[current_week]['projected_points']
        
        # Only use players who have a meaningful weekly projection
        if weekly_projection > 2.0:
            bye_week = get_player_bye_week(player)
            player_info = {
                'player_id': player.playerId if hasattr(player, 'playerId') else None,
                'name': player.name if hasattr(player, 'name') else str(player),
                'position': player.position if hasattr(player, 'position') else 'N/A',
                'team': player.proTeam if hasattr(player, 'proTeam') else 'N/A',
                'projected_points': weekly_projection,
                'bye_week': bye_week,
                'injury_status': player.injuryStatus if hasattr(player, 'injuryStatus') else None
            }
            waiver_players.append(player_info)
    
    # Sort by projected points for this week and limit to requested size
    waiver_data = sorted(waiver_players, key=lambda x: x['projected_points'], reverse=True)[:size]
    
    if not waiver_data:
        return {"message": f"No available players found for position {position}" if position else "No available players found"}
    
    # Round projected points for cleaner output
    for player in waiver_data:
        player['projected_points'] = round(player['projected_points'], 1)
    
    return {
        "position": position if position else "All",
        "available_players": waiver_data,
        "count": len(waiver_data),
        "note": "Use get_player_stats tool with player_id for detailed analysis of any player"
    }




def get_team_details_for_tool(league, team_id):
    """Tool-callable method to get roster info for a specific team"""
    target_team = None
    
    # Find team by team_id
    for team in league.teams:
        if hasattr(team, 'team_id') and team.team_id == team_id:
            target_team = team
            break
    
    if not target_team:
        return {"error": f"Team with ID '{team_id}' not found"}
    
    # Always return structured lineup with player_ids for deeper analysis
    roster_summary = get_structured_roster_summary_with_ids(league, target_team)
    return {
        'team_name': target_team.team_name,
        'record': f"{target_team.wins}-{target_team.losses}",
        'points_for': target_team.points_for,
        'points_against': target_team.points_against if hasattr(target_team, 'points_against') else 0,
        'roster_strength': calculate_roster_strength(target_team),
        'lineup': roster_summary,
        'note': "Use get_player_stats tool with player_id for detailed player analysis"
    }




def calculate_roster_strength(team):
    """Calculate overall roster strength score"""
    roster = team.roster if hasattr(team, 'roster') else []
    total_projected = 0
    
    for player in roster:
        # Use weekly average projections for roster strength
        if hasattr(player, 'projected_avg_points'):
            total_projected += player.projected_avg_points
    
    return round(total_projected, 2)




def get_opponent_details(league, my_team):
    """Get detailed opponent information for the current matchup"""
    if league.current_week == 0:
        return None
        
    try:
        if hasattr(league, 'box_scores'):
            current_matchup = league.box_scores()
            for matchup in current_matchup:
                if hasattr(matchup, 'home_team') and hasattr(matchup, 'away_team'):
                    if my_team in [matchup.home_team, matchup.away_team]:
                        opponent = matchup.away_team if matchup.home_team == my_team else matchup.home_team
                        
                        # Get the actual lineup from box score for accurate projections
                        opponent_lineup = matchup.away_lineup if opponent == matchup.away_team else matchup.home_lineup
                        
                        # Calculate starters projected total from box score lineup
                        starters_projected = 0
                        for player in opponent_lineup:
                            if hasattr(player, 'lineupSlot') and player.lineupSlot not in ['BE', 'IR']:
                                if hasattr(player, 'projected_points'):
                                    starters_projected += player.projected_points
                        
                        opponent_details = {
                            'team_name': opponent.team_name,
                            'team_id': opponent.team_id if hasattr(opponent, 'team_id') else None,
                            'record': f"{opponent.wins}-{opponent.losses}",
                            'projected_total': starters_projected,
                            'recent_performance': opponent.points_for / max(league.current_week - 1, 1) if league.current_week > 1 else 0
                        }
                        return opponent_details
    except Exception as e:
        pass
    
    return None


def get_structured_roster_summary_with_ids(league, team):
    """Get structured roster summary with clean JSON format including player_ids"""
    roster = team.roster if hasattr(team, 'roster') else []
    
    starters = []
    bench = []
    
    for player in roster:
        # Get key info only
        proj_points = 0
        if hasattr(player, 'stats') and isinstance(player.stats, dict):
            current_week = league.current_week
            if current_week in player.stats and 'projected_points' in player.stats[current_week]:
                proj_points = player.stats[current_week]['projected_points']
        if proj_points == 0 and hasattr(player, 'projected_avg_points'):
            proj_points = player.projected_avg_points
            
        lineup_slot = 'BE'  # Default to bench
        if hasattr(player, 'lineupSlot'):
            lineup_slot = player.lineupSlot
            
        injury = None
        if hasattr(player, 'injuryStatus') and player.injuryStatus:
            injury = player.injuryStatus
        
        bye_week = get_player_bye_week(player)
        
        player_info = {
            'player_id': player.playerId if hasattr(player, 'playerId') else None,
            'name': player.name if hasattr(player, 'name') else 'Unknown',
            'position': player.position if hasattr(player, 'position') else 'N/A',
            'lineup_slot': lineup_slot,
            'projected_points': round(proj_points, 1),
            'bye_week': bye_week,
            'injury_status': injury
        }
            
        # Categorize as starter or bench
        if lineup_slot not in ['BE', 'IR']:
            starters.append(player_info)
        elif lineup_slot not in ['IR']:  # Include all bench players except IR
            bench.append(player_info)
    
    # Sort starters by lineup slot for consistency
    lineup_slot_order = ['QB', 'RB', 'WR', 'TE', 'RB/WR/TE', 'K', 'D/ST']
    starters.sort(key=lambda x: lineup_slot_order.index(x['lineup_slot']) if x['lineup_slot'] in lineup_slot_order else 999)
    
    # Sort bench by projected points
    bench.sort(key=lambda x: x['projected_points'], reverse=True)
    
    return {
        'starters': starters,
        'bench': bench
    }


def get_lightweight_roster_summary(league, team):
    """Get concise roster summary for initial prompt - minimal tokens"""
    roster = team.roster if hasattr(team, 'roster') else []
    
    starters = []
    bench_highlights = []
    
    for player in roster:
        # Get key info only
        proj_points = 0
        if hasattr(player, 'stats') and isinstance(player.stats, dict):
            current_week = league.current_week
            if current_week in player.stats and 'projected_points' in player.stats[current_week]:
                proj_points = player.stats[current_week]['projected_points']
        if proj_points == 0 and hasattr(player, 'projected_avg_points'):
            proj_points = player.projected_avg_points
            
        lineup_slot = 'BENCH'
        if hasattr(player, 'lineupSlot'):
            lineup_slot = player.lineupSlot
            
        injury = None
        if hasattr(player, 'injuryStatus') and player.injuryStatus:
            injury = player.injuryStatus
            
        bye_week = get_player_bye_week(player)
            
        # Build player summary with lineup slot for starters
        if lineup_slot not in ['BE', 'IR']:
            player_summary = f"{lineup_slot}: {player.name} ({player.position if hasattr(player, 'position') else 'N/A'}) - {proj_points:.1f}pts"
        else:
            player_summary = f"{player.name} ({player.position if hasattr(player, 'position') else 'N/A'}) - {proj_points:.1f}pts"
        
        if bye_week:
            player_summary += f" (Bye: W{bye_week})"
        if injury:
            player_summary += f" [{injury}]"
            
        # Categorize as starter or bench
        if lineup_slot not in ['BE', 'IR']:
            starters.append(player_summary)
        elif lineup_slot not in ['IR']:  # Include all bench players except IR
            bench_highlights.append(player_summary)
    
    summary = "STARTERS:\n" + "\n".join(starters)
    if bench_highlights:
        summary += "\n\nBENCH:\n" + "\n".join(bench_highlights)
    
    return summary


def get_minimal_league_standings(league):
    """Get minimal league standings for prompt - just names, records, ranks"""
    standings = []
    for team in league.teams:
        standings.append({
            'team_id': team.team_id if hasattr(team, 'team_id') else None,
            'name': team.team_name,
            'record': f"{team.wins}-{team.losses}",
            'pts': round(team.points_for, 1)
        })
    
    # Sort by wins, then by points
    standings.sort(key=lambda x: (int(x['record'].split('-')[0]), x['pts']), reverse=True)
    
    # Create concise text format
    standings_text = []
    for i, team in enumerate(standings, 1):
        team_id_text = f" (team_id: {team['team_id']})" if team['team_id'] else ""
        standings_text.append(f"{i}. {team['name']} ({team['record']}) - {team['pts']}pts{team_id_text}")
    
    return '\n'.join(standings_text)


def get_concise_opponent_summary(league, my_team):
    """Get minimal opponent info for initial prompt"""
    opponent_details = get_opponent_details(league, my_team)
    if not opponent_details:
        return "No opponent data available"
    
    team_id_text = f" (team_id: {opponent_details['team_id']})" if opponent_details.get('team_id') else ""
    
    return f"{opponent_details['team_name']} ({opponent_details['record']}) - Proj: {opponent_details['projected_total']:.1f}pts{team_id_text}\nUse get_team_details tool for full roster analysis"


def get_player_stats_for_tool(league, player_id):
    """Get detailed stats for a specific player by player_id"""
    # Search for player by ID in all rosters
    for team in league.teams:
        roster = team.roster if hasattr(team, 'roster') else []
        for player in roster:
            if hasattr(player, 'playerId') and player.playerId == player_id:
                # Found the player, get detailed stats
                bye_week = get_player_bye_week(player)
                player_stats = {
                    'player_id': player.playerId,
                    'name': player.name,
                    'position': player.position if hasattr(player, 'position') else 'N/A',
                    'team': player.proTeam if hasattr(player, 'proTeam') else 'N/A',
                    'fantasy_team': team.team_name,
                    'projected_avg_points': round(player.projected_avg_points if hasattr(player, 'projected_avg_points') else 0, 1),
                    'bye_week': bye_week,
                    'injury_status': player.injuryStatus if hasattr(player, 'injuryStatus') else None
                }
                
                # Get weekly stats breakdown, filtering and organizing
                weekly_stats = {}
                if hasattr(player, 'stats') and isinstance(player.stats, dict):
                    for week, stats in player.stats.items():
                        # Skip Week 0 (preseason) - often contains season totals instead of weekly data
                        if week == 0 or week == '0':
                            continue
                            
                        if isinstance(stats, dict):
                            # Round projected and actual points
                            weekly_data = {
                                'projected_points': round(stats.get('projected_points', 0), 1),
                                'actual_points': round(stats.get('points', 0), 1),
                                'status': 'completed' if stats.get('points', 0) > 0 else 'projected'
                            }
                            
                            # Add key breakdown stats if available, with rounding
                            if 'projected_breakdown' in stats:
                                breakdown = stats['projected_breakdown']
                                if player.position in ['RB', 'WR', 'TE']:
                                    weekly_data['breakdown'] = {
                                        'rushing_attempts': round(breakdown.get('rushingAttempts', 0), 1),
                                        'rushing_yards': round(breakdown.get('rushingYards', 0), 1),
                                        'rushing_tds': round(breakdown.get('rushingTouchdowns', 0), 1),
                                        'receiving_targets': round(breakdown.get('receivingTargets', 0), 1),
                                        'receiving_receptions': round(breakdown.get('receivingReceptions', 0), 1),
                                        'receiving_yards': round(breakdown.get('receivingYards', 0), 1),
                                        'receiving_tds': round(breakdown.get('receivingTouchdowns', 0), 1)
                                    }
                                elif player.position == 'QB':
                                    weekly_data['breakdown'] = {
                                        'passing_attempts': round(breakdown.get('passingAttempts', 0), 1),
                                        'passing_completions': round(breakdown.get('passingCompletions', 0), 1),
                                        'passing_yards': round(breakdown.get('passingYards', 0), 1),
                                        'passing_tds': round(breakdown.get('passingTouchdowns', 0), 1),
                                        'rushing_attempts': round(breakdown.get('rushingAttempts', 0), 1),
                                        'rushing_yards': round(breakdown.get('rushingYards', 0), 1)
                                    }
                            
                            weekly_stats[str(week)] = weekly_data
                
                # Sort weeks chronologically and add to player stats
                player_stats['weekly_stats'] = dict(sorted(weekly_stats.items(), key=lambda x: int(x[0])))
                
                return player_stats
    
    return {"error": f"Player with ID '{player_id}' not found"}