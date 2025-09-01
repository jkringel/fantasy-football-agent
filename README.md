# Fantasy Football AI Analyzer

An AI-powered fantasy football analyzer that connects to ESPN Fantasy Football leagues to provide intelligent roster analysis, lineup recommendations, and waiver wire suggestions using OpenAI's GPT models.

## Features

- **AI-Powered Analysis**: Uses OpenAI GPT-5 to analyze your fantasy football team with expert insights
- **Real-time Data**: Connects directly to ESPN Fantasy Football API for up-to-date league information
- **Comprehensive Tools**: 
  - Starting lineup optimization
  - Waiver wire recommendations
  - Opponent analysis
  - Player statistics and trends
  - Injury updates and news integration
- **Interactive Debug Mode**: Test and explore fantasy data functions interactively

## Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- ESPN Fantasy Football league access
- OpenAI API key

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd fantasy-football-agent
   ```

2. **Install dependencies using uv**:
   ```bash
   uv sync
   ```

## Configuration

1. **Create a `.env` file** in the project root with the following variables:
   ```env
   ESPN_S2=your_espn_s2_cookie
   SWID=your_swid_cookie
   OPENAI_API_KEY=your_openai_api_key
   LEAGUE_ID=your_league_id
   YEAR=2025
   ```

2. **Get ESPN Credentials**:
   - Log into ESPN Fantasy Football in your browser
   - Open Developer Tools (F12)
   - Go to Application/Storage → Cookies
   - Find and copy the values for `espn_s2` and `SWID`

3. **Get League ID**:
   - Navigate to your ESPN fantasy league
   - The League ID is in the URL: `https://fantasy.espn.com/football/team?leagueId=XXXXXXX`

## Usage

### Main Analysis Tool

Run the AI-powered fantasy football analysis:

```bash
uv run main.py
```

This will:
- Connect to your ESPN Fantasy league
- Analyze your roster and matchups
- Provide AI-generated recommendations for:
  - Starting lineup decisions
  - Waiver wire pickups
  - Roster moves
  - Matchup strategy

### Debug Mode

View the AI prompt without making API calls:

```bash
uv run main.py --debug
```

### Interactive Debug Tool

Explore individual fantasy data functions:

```bash
uv run debug_espn.py
```

This provides an interactive menu to test:
- Waiver wire analysis
- Team roster details
- Player statistics
- League standings
- Opponent summaries

## Project Structure

```
fantasy-football-agent/
├── main.py              # Main AI analysis application
├── fantasy_data.py      # ESPN API data fetching functions
├── debug_espn.py        # Interactive debugging tool
├── pyproject.toml       # uv project configuration
├── .env                 # Environment variables (create this)
└── README.md            # This file
```

## Key Components

### Data Functions (`fantasy_data.py`)
- `identify_my_team()`: Finds your team in the league
- `get_waiver_wire_for_tool()`: Retrieves available players
- `get_team_details_for_tool()`: Gets detailed roster information
- `get_player_stats_for_tool()`: Fetches player performance data
- `get_lightweight_roster_summary()`: Optimized roster summaries

### AI Integration (`main.py`)
- Uses OpenAI Responses API with function calling
- Supports web search for current NFL news and updates
- Implements retry logic with exponential backoff
- Token-optimized prompts for cost efficiency

## Dependencies

- **espn-api**: ESPN Fantasy Football API client
- **openai**: OpenAI Python SDK
- **python-dotenv**: Environment variable management
- **tenacity**: Retry logic for API calls

## Troubleshooting

### Common Issues

1. **ESPN Authentication Errors**:
   - Verify your `ESPN_S2` and `SWID` cookies are current
   - ESPN cookies expire periodically - refresh them by logging in again

2. **League Not Found**:
   - Double-check your `LEAGUE_ID` in the `.env` file
   - Ensure you have access to the league

3. **OpenAI API Errors**:
   - Verify your `OPENAI_API_KEY` is valid
   - Check your OpenAI account has sufficient credits

4. **Pre-season Mode**:
   - The tool automatically detects pre-season and provides limited functionality
   - Full analysis is available once the NFL season begins

### Getting Help

If you encounter issues:
1. Check the troubleshooting section in the console output
2. Run in debug mode to see the data being processed
3. Use the interactive debug tool to test individual components

## License

See `LICENSE` file for details.