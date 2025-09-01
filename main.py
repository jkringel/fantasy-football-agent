#!/usr/bin/env python3
"""
Fantasy Football AI Analyzer
Analyzes your roster and provides AI-powered recommendations
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from espn_api.football import League
from openai import OpenAI
from datetime import datetime
import json
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from fantasy_data import (
    identify_my_team,
    fetch_preseason_rosters,
    get_waiver_wire_for_tool,
    get_team_details_for_tool,
    get_player_stats_for_tool,
    get_lightweight_roster_summary,
    get_minimal_league_standings,
    get_concise_opponent_summary
)


def build_prompt(league, my_team):
    """Build the prompt for AI analysis - optimized for minimal tokens"""
    # Get lightweight summaries instead of full data dumps
    my_roster_summary = get_lightweight_roster_summary(league, my_team)
    league_standings_text = get_minimal_league_standings(league)
    opponent_summary = get_concise_opponent_summary(league, my_team)
    
    # Calculate my team's projected total from box scores
    my_starters_projected = 0
    if league.current_week > 0:
        try:
            box_scores = league.box_scores()
            for matchup in box_scores:
                if hasattr(matchup, 'home_team') and hasattr(matchup, 'away_team'):
                    if my_team in [matchup.home_team, matchup.away_team]:
                        my_lineup = matchup.home_lineup if my_team == matchup.home_team else matchup.away_lineup
                        for player in my_lineup:
                            if hasattr(player, 'lineupSlot') and player.lineupSlot not in ['BE', 'IR']:
                                if hasattr(player, 'projected_points'):
                                    my_starters_projected += player.projected_points
                        break
        except:
            pass
    
    # Calculate my average points per week
    my_avg_points_per_week = (
        my_team.points_for / max(league.current_week - 1, 1) 
        if league.current_week > 1 else 0
    )
    
    # Get current date for context
    current_date = datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""Analyze this fantasy football team and provide actionable recommendations for Week {league.current_week}.

{league.year} SEASON - WEEK {league.current_week} | {current_date}
Team: {my_team.team_name} | Record: {my_team.wins}-{my_team.losses} | Points For: {my_team.points_for:.1f} | Avg/Week: {my_avg_points_per_week:.1f}
Projected Total (starters): {my_starters_projected:.1f}

MY ROSTER:
{my_roster_summary}

OPPONENT:
{opponent_summary}

LEAGUE STANDINGS:
{league_standings_text}

Tools available for deeper analysis:
- web_search: Get current Week {league.current_week} NFL news, injuries, weather, and matchup insights
- get_waiver_wire: Find top available players, optionally filtered by position  
- get_team_details: Analyze any team's roster using their team_id from standings above
- get_player_stats: Get detailed weekly breakdown stats for any player by player_id

Use these tools to enhance your analysis with latest information and identify opportunities.

Provide recommendations in these sections:

## EXECUTIVE SUMMARY
Key insights and most critical decisions for this week.

## STARTING LINEUP
Optimal lineup with brief reasoning for key decisions. Consider injuries, matchups, bye weeks, and recent performance.

## ROSTER MOVES
Use the get_waiver_wire tool to find available players, then provide specific add/drop recommendations. Consider upcoming bye weeks when evaluating long-term roster needs.

## MATCHUP STRATEGY  
How to approach this specific opponent and maximize win probability.

## ACTION ITEMS
Prioritized list of moves to make immediately.

Be specific with player names and confident in recommendations. Focus on what matters most for winning this week."""
    
    return prompt


def analyze_with_openai(league, my_team, openai_client):
    """Use OpenAI to analyze roster and provide recommendations"""
    print("\n🤖 Starting AI analysis...")
    print("   Note: Tool calls will be displayed as they occur\n")
    
    prompt = build_prompt(league, my_team)
    
    # Create instructions to establish the AI as a fantasy football expert
    instructions = """You are an expert fantasy football analyst with deep NFL knowledge. You combine statistical analysis with understanding of matchups, injuries, bye weeks, and game script to provide actionable fantasy advice.

IMPORTANT: The initial data provided is intentionally concise to optimize token usage. Use the available tools strategically to gather detailed information as needed:

- web_search: Get current NFL news, injuries, weather, and matchup insights
- get_waiver_wire: Find top available players (use position filter for focused searches)
- get_team_details: Get full roster details for any team using team_id from standings
- get_player_stats: Get detailed weekly stats breakdown for any player using player_id

Start your analysis with the provided summary data, then use tools to drill down into areas that need deeper investigation. Focus on high-impact decisions and actionable recommendations.

CRITICAL OUTPUT FORMATTING RULES:
- NEVER include URLs, links, or web addresses in your output
- NEVER include citations, sources, or references like ([website.com]) or [website.com](url)
- NEVER include domain names or source attributions
- DO NOT add any form of citation such as "(Source: ...)" or "(via ...)" or "(from ...)"
- Present all information as YOUR expert analysis, not as sourced content
- Write with authority as the fantasy football expert providing original analysis
- Synthesize web search findings into your own insights without attribution

Example of INCORRECT output (DO NOT DO THIS):
"Justin Fields has rushing upside ([nypost.com](url))" 
"According to ESPN, the player is injured"
"(Source: NFL.com)"

Example of CORRECT output (DO THIS):
"Justin Fields has rushing upside in this matchup"
"The player is dealing with an injury"
"Weather conditions favor the passing game"

Remember: You are THE expert providing analysis. All insights should be presented as your professional assessment without any citations or source references."""
    
    # Create tool definitions for OpenAI format
    waiver_tool = {
        "type": "function",
        "name": "get_waiver_wire",
        "description": "Get top available players from the waiver wire, sorted by projected points (highest first), optionally filtered by position",
        "parameters": {
            "type": "object",
            "properties": {
                "position": {
                    "type": "string",
                    "enum": ["QB", "RB", "WR", "TE", "K", "D/ST"],
                    "description": "Position to filter by (optional)"
                },
                "size": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Number of players to return (default: 3, max: 8)"
                }
            }
        }
    }
    
    team_details_tool = {
        "type": "function",
        "name": "get_team_details",
        "description": "Get roster information for a specific team including lineup structure with player IDs. Use team_id from league standings. Use get_player_stats tool with player_id for detailed individual player analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {
                    "type": "integer",
                    "description": "The team_id from the league standings. Example: 123"
                }
            },
            "required": ["team_id"]
        }
    }
    
    player_stats_tool = {
        "type": "function",
        "name": "get_player_stats",
        "description": "Get detailed weekly breakdown stats for any player. Useful for analyzing usage trends, projections, and performance patterns. Use the player_id from roster data.",
        "parameters": {
            "type": "object", 
            "properties": {
                "player_id": {
                    "type": "integer",
                    "description": "The player_id from roster data. Example: 4426515"
                }
            },
            "required": ["player_id"]
        }
    }
    
    # Create completion function with exponential backoff
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    def responses_with_backoff(**kwargs):
        return openai_client.responses.create(**kwargs)
    
    # Create initial API call with the Responses API
    response = responses_with_backoff(
        model="gpt-5",
        instructions=instructions,
        input=prompt,
        tools=[
            {"type": "web_search"},
            waiver_tool,
            team_details_tool,
            player_stats_tool
        ]
    )
    
    # Loop until no more function calls are needed
    while True:
        # Log token usage for monitoring
        if hasattr(response, 'usage'):
            usage = response.usage
            print(f"   Token usage - Input: {usage.input_tokens}, Output: {usage.output_tokens}")
        
        # Check for function calls that need our handling (not web search)
        function_calls_to_execute = []
        
        # Process the output array for tool calls
        for item in response.output:
            # Check for web search calls (handled by OpenAI, don't need tool results)
            if hasattr(item, 'type') and item.type == 'web_search_call':
                print(f"\n🔧 Tool Call: web_search")
                if hasattr(item, 'action') and hasattr(item.action, 'query'):
                    print(f"   Query: {item.action.query}")
                print(f"   → Web search executed by AI")
                
            # Check for function calls (custom tools that need our handling)  
            elif hasattr(item, 'type') and item.type == 'function_call':
                function_calls_to_execute.append(item)
        
        # If no function calls to execute, we're done
        if not function_calls_to_execute:
            break
            
        # Execute function calls and collect results for this iteration
        function_call_outputs = []
        for tool_call in function_calls_to_execute:
            tool_name = tool_call.name if hasattr(tool_call, 'name') else None
            # Parse JSON arguments if they're in string format
            tool_args = {}
            if hasattr(tool_call, 'arguments'):
                try:
                    tool_args = json.loads(tool_call.arguments)
                except:
                    tool_args = {}
            tool_call_id = tool_call.call_id if hasattr(tool_call, 'call_id') else None
            
            if tool_name:
                print(f"\n🔧 Tool Call: {tool_name}")
                if tool_args:
                    print(f"   Parameters: {json.dumps(tool_args, indent=2)}")
                
                # Execute the appropriate tool
                result = None
                if tool_name == 'get_waiver_wire':
                    position = tool_args.get('position', None)
                    size = tool_args.get('size', 3)
                    result = get_waiver_wire_for_tool(league, position=position, size=size)
                    
                    if 'available_players' in result:
                        print(f"   → Found {len(result['available_players'])} players")
                        
                elif tool_name == 'get_team_details':
                    team_id = tool_args.get('team_id', None)
                    result = get_team_details_for_tool(league, team_id=team_id)
                    
                    if 'team_name' in result:
                        print(f"   → Retrieved team details for {result['team_name']}")
                    elif 'error' in result:
                        print(f"   → Error: {result['error']}")
                        
                elif tool_name == 'get_player_stats':
                    player_id = tool_args.get('player_id', None)
                    result = get_player_stats_for_tool(league, player_id=player_id)
                    
                    if 'name' in result:
                        print(f"   → Retrieved stats for {result['name']}")
                    elif 'error' in result:
                        print(f"   → Error: {result['error']}")
                
                # Add function call output for this iteration
                if result is not None:
                    function_call_outputs.append({
                        "type": "function_call_output",
                        "call_id": tool_call_id,
                        "output": json.dumps(result)
                    })
        
        # Continue conversation using previous_response_id with only the function outputs
        response = responses_with_backoff(
            model="gpt-5",
            instructions=instructions,
            previous_response_id=response.id,
            input=function_call_outputs,
            tools=[
                {"type": "web_search"},
                waiver_tool,
                team_details_tool,
                player_stats_tool
            ]
        )
    
    print("\n✅ Analysis complete!\n")
    
    # Extract text output - try SDK convenience property first
    if hasattr(response, 'output_text') and response.output_text:
        return response.output_text
    
    # Fallback: Extract text from message content in output array
    final_text = ""
    if hasattr(response, 'output'):
        for item in response.output:
            if hasattr(item, 'type') and item.type == 'message':
                if hasattr(item, 'content') and isinstance(item.content, list):
                    for content_item in item.content:
                        if hasattr(content_item, 'type') and content_item.type == 'output_text':
                            if hasattr(content_item, 'text'):
                                final_text += content_item.text
    
    return final_text if final_text else "Analysis complete."


def get_prompt_for_debug(league, my_team):
    """Get the prompt without calling OpenAI (for debugging)"""
    return build_prompt(league, my_team)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fantasy Football AI Analyzer')
    parser.add_argument('--debug', action='store_true', help='Print the prompt instead of calling AI')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    espn_s2 = os.getenv('ESPN_S2')
    swid = os.getenv('SWID')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not espn_s2 or not swid:
        print("Error: ESPN credentials not found in .env file")
        print("Please add ESPN_S2 and SWID to your .env file")
        sys.exit(1)
    
    if not openai_key:
        print("Error: OPENAI_API_KEY not found in .env file")
        print("Please add your OpenAI API key to your .env file")
        sys.exit(1)
    
    # League details
    league_id = os.getenv('LEAGUE_ID')
    if not league_id:
        print("Please add your LEAGUE_ID to your .env file")
        sys.exit(1)
    league_id = int(league_id)
    
    year = os.getenv('YEAR')
    if not year:
        print("Please add your YEAR to your .env file")
        sys.exit(1)
    year = int(year)
    
    print("🏈 Fantasy Football AI Advisor")
    print("=" * 50)
    
    try:
        print("Connecting to ESPN Fantasy...")
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
        my_team = identify_my_team(league, swid)
        
        # For pre-season or week 0, we need to fetch roster differently
        if league.current_week == 0:
            fetch_preseason_rosters(league)
        
        print(f"✓ Connected to: {league.settings.name}")
        print(f"✓ Your team: {my_team.team_name}")
        print(f"✓ Current week: {'Pre-season' if league.current_week == 0 else league.current_week}")
        print("-" * 50)
        
        # Check if it's preseason
        if league.current_week == 0:
            print("\n⏰ It's currently pre-season!")
            print("-" * 50)
            print("\nThe season hasn't started yet. Come back when Week 1 begins to:")
            print("  • Get AI-powered lineup recommendations")
            print("  • Analyze start/sit decisions")
            print("  • Review waiver wire targets")
            print("  • Identify trade opportunities")
            print("  • Receive injury updates and matchup analysis")
            print("\nFor now, you can still view:")
            print("  • Top waiver wire players (use --waiver flag)")
            print("  • League standings and teams")
            print("\n" + "=" * 50)
            print("Check back when the season starts! 🏈")
            sys.exit(0)
        
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=openai_key)
        
        # AI-powered analysis
        if args.debug:
            print("\n🐛 DEBUG MODE - Showing Prompt")
            print("=" * 50)
            print("Getting data and building prompt...\n")
            prompt = get_prompt_for_debug(league, my_team)
            print("PROMPT TO AI:")
            print("-" * 50)
            print(prompt)
            print("-" * 50)
            print(f"\nPrompt length: {len(prompt)} characters")
        else:
            print("\n📊 Generating Comprehensive Daily Analysis")
            print("=" * 50)
            print("Analyzing roster, matchups, waiver wire, and league dynamics...")
            print("Preparing detailed recommendations...\n")
            
            analysis = analyze_with_openai(league, my_team, openai_client)
            print(analysis)
        
        print("\n" + "=" * 50)
        print("✅ Analysis complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your ESPN credentials are current")
        print("2. Ensure OPENAI_API_KEY is set in .env")
        print("3. Verify you have access to the league")
        sys.exit(1)

if __name__ == "__main__":
    main()