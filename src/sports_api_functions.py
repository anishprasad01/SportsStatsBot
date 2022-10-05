# sports_api_functions.py
# This class is responsible for holding the functions that GET data from the football API 
# and parse it into blocks that can be sent back to Slack
# It performs error checking on recieved data and logs errors if they occur

import os
import requests
import json
import dateutil.parser
import datetime
import logging

# Use dynamo functions
import dynamo_functions as db

# Set API URL and league ID, and configure logging
__url = "https://v3.football.api-sports.io/"
__league_id = 39
logging.basicConfig(filename='sports_stats_bot_api_functions.log', filemode='a', format='%(name)s - %(levelname)s - %(message)s')

# Get standings information for all 20 clubs in the EPL
def get_standings_data_all(client, message, return_card = False):
    # Limit number of results when returning a card to avoid overloading the user's view
    return_card_limit = 3

    league_standings = None

    # If getting the data fails, log the error and ask the user to try again later
    try:
        # GET and parse the standings data from the API
        standings_endpoint = __url + "standings"
        standings_json = requests.get(standings_endpoint, params={"league":__league_id, "season":datetime.date.today().year}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
        standings_dict = json.loads(standings_json.content)
        league_standings = standings_dict.get("response")[0].get("league").get("standings")[0]
    except Exception:
        logging.error(Exception)
        result = client.chat_postMessage(
                channel=message["channel"],
				text="Error Getting Data from API",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Unable to get standings. Please try again later.",
                        "emoji": False
                    }
                },
            ])
    
    # Create the card that will hold the standings blocks
    header_text = "Current English Premier League Top 3" if return_card else "Current English Premier League Standings"

    standings_card = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{header_text}",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            },
        ]
    }

    # Get the required info out of the JSON response for each club in the standings
    count = 0
    for team_entry in league_standings:
        count += 1

        # Extract standings data from api response
        curr_team_data = __extract_standings_data(team_entry)

        # Create a set of blocks for the current team
        standings_entry = __create_team_card_block(curr_team_data)

        # Inform the user if the API sends back malformed data and return
        if not standings_entry:
            result = client.chat_postMessage(
                channel=message["channel"],
				text="Error Getting Data from API",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Error in standings data from API. Please try again later.",
                        "emoji": False
                    }
                },
            ])
            return

        # Add the blocks to the card
        for item in standings_entry:
            standings_card.get("blocks").append(item)

        # Returns the top 3 teams in a card instead of printing it to Slack
        # Used for the App Home Tab
        if return_card and count == return_card_limit:
            return standings_card
        
        # Send the blocks to Slack for every 5 teams to avoid Slack's 50 block limit
        if count == 5 or team_entry == None: 
            result = client.chat_postMessage(
                    channel=message["channel"],
					text="EPL Standings Card",
					blocks=json.dumps(standings_card.get("blocks")))
            standings_card.get("blocks").clear()
            count = 0

# Get statistics for the team requested by the user
def get_team_stats_data(client, message, team_name):
    team_stats = None
    team_info_dict = None

    try:
        #call team info endpoint
        teams_endpoint = __url + "teams"
        team_info_json = requests.get(teams_endpoint, params={"name":team_name}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
        team_info_dict = json.loads(team_info_json.content).get("response")[0]
        team_id = team_info_dict.get("team").get("id")

        #call stats endpoint
        endpoint_path = "teams/statistics"
        endpoint = __url + endpoint_path
        stats_json = requests.get(endpoint, params={"league":__league_id, "season":datetime.date.today().year, "team": team_id}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
        stats_dict = json.loads(stats_json.content)
        team_stats = stats_dict.get("response")
    except Exception:
        logging.error(Exception)
        result = client.chat_postMessage(
                channel=message["channel"],
				text="Error Getting Data from API",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Unable to get team stats. Please ensure you have provided a valid EPL team name or try again later.",
                        "emoji": False
                    }
                },
            ])

    # Extract team stats from api response
    team_data = __extract_team_stats_data(team_stats, team_info_dict)

    # Create the card to hold the blocks for the team stats
    team_info_card = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Current English Premier League Stats for {team_name}",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            },
        ]
    }   
    
    # Generate the stats card
    team_stats_card = __create_stats_card_block(team_data)

    # Inform the user if the API sends back malformed data and return
    if not team_stats_card:
        result = client.chat_postMessage(
            channel=message["channel"],
            text="Error Getting Data from API",
            blocks=[{
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "Error in stats data from API. Please try again later.",
                    "emoji": False
                }
            },
        ])
        return

    # Add stats blocks to the card
    for item in team_stats_card:
            team_info_card.get("blocks").append(item)
    
    # Send the blocks back to the client
    client.chat_postMessage(
                channel=message["channel"],
                text="EPL Team Stats Card",
                blocks=json.dumps(team_info_card.get("blocks")))

# Get data on recently completed games for the team requested by the user
def get_past_games_data(client, message, team_name = None):
    # Set the number of games to get data for 
    number_of_games = 3

    team_games_stats = None

    try:
        # If no team name provided, get prior games from any team
        if not team_name or team_name.isspace():
            # Get completed games in the current season in oldest-newest order
            fixtures_endpoint = __url + "fixtures"
            team_games_json = requests.get(fixtures_endpoint, params={"league":__league_id, "season":datetime.date.today().year, "status":"FT"}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
            team_games_stats = json.loads(team_games_json.content).get("response")

        else:
            # Get the ID the API uses to identify a team
            teams_endpoint = __url + "teams"
            team_info_json = requests.get(teams_endpoint, params={"name":team_name}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
            team_info_dict = json.loads(team_info_json.content).get("response")[0]
            team_id = team_info_dict.get("team").get("id")

            # Get completed games for this team in the current season in oldest-newest order
            fixtures_endpoint = __url + "fixtures"
            team_games_json = requests.get(fixtures_endpoint, params={"team":team_id, "league":__league_id, "season":datetime.date.today().year, "status":"FT"}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
            team_games_stats = json.loads(team_games_json.content).get("response")
    except Exception:
        logging.error(Exception)
        
        result = client.chat_postMessage(
                channel=message["channel"],
				text="Error Getting Team Stats from API",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Unable to get past games. Please ensure you have provided a valid EPL team name or try again later.",
                        "emoji": False
                    }
                },
            ])

    # Set header text based on whether a team was requested
    header_text = f"Recent Games Played by {team_name}" if team_name else "Recent English Premier League Games"

    # Create card to hold recent game data blocks
    recent_game_card = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{header_text}",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            },
        ]
    }

     # If there are no past games, add a message to the card and do not bother trying to parse the response
    if len(team_games_stats) == 0:
        upcoming_game_card.get("blocks").append(
            {
                "type": "plain_text",
                "text": f"No past games found for {team_name} in the current season.",
                "emoji": False
            }
        )
    else:
        # Go through the game information in newest to oldest chronological order
        count = 0
        for i in range(len(team_games_stats)-1, 0, -1):
            # Limit the number of games displayed to not overload the user's screen with a wall of info
            if count == number_of_games: break

            curr_game = team_games_stats[i]

            # Get the data for the current game
            past_game_data = __extract_past_games_data(curr_game)

            # Generate blocks for prior games data
            curr_game_card = __create_prior_games_card_block(past_game_data)

            # Inform the user if the API sends back malformed data and return
            if not curr_game_card:
                result = client.chat_postMessage(
                    channel=message["channel"],
                    text="Error Getting Data from API",
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": "Error in past games data from API. Please try again later.",
                            "emoji": False
                        }
                    },
                ])
                return
            
            # Add the blocks to the card
            for item in curr_game_card:
                recent_game_card.get("blocks").append(item)

            count += 1

    # Send the blocks back to the user
    client.chat_postMessage(
                channel=message["channel"],
                text="EPL Team Info Card",
                blocks=json.dumps(recent_game_card.get("blocks")))

# Get data on upcoming game by team or in general
def get_next_game_data(client, message, team_name = None, return_card = False):
    # Set the number of games to get data for 
    number_of_games = 3

    future_games = None

    try:
        fixtures_endpoint = __url + "fixtures"

        if not team_name or team_name.isspace():
            # Get upcoming teams games for current season in closest to current date order
            future_games_json = requests.get(fixtures_endpoint, params={"league":__league_id, "season":datetime.date.today().year, "status":"NS"}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
            future_games = json.loads(future_games_json.content).get("response")
        else:
            # Get team id for API
            teams_endpoint = __url + "teams"
            team_info_json = requests.get(teams_endpoint, params={"name":team_name}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
            team_info_dict = json.loads(team_info_json.content).get("response")[0]
            team_id = team_info_dict.get("team").get("id")

            # Get upcoming teams games for current season in closest to current date order for given tea,
            future_games_json = requests.get(fixtures_endpoint, params={"team":team_id, "league":__league_id, "season":datetime.date.today().year, "status":"NS"}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
            future_games = json.loads(future_games_json.content).get("response")
    except Exception:
        logging.error(Exception)
        
        result = client.chat_postMessage(
                channel=message["channel"],
				text="Error Getting Team Stats from API",
                blocks=[{
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Unable to get upcoming games. Please ensure you have provided a valid EPL team name or try again later.",
                        "emoji": False
                    }
                },
            ])

    # Set header text based on whether a team was requested
    header_text = f"Upcoming Games Featuring {team_name}" if team_name else "Upcoming English Premier League Games"

    # Create the card to hold the blocks
    upcoming_game_card = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{header_text}",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            },
        ]
    }

    # If there are no upcoming games, add a message to the card and do not bother trying to parse the response
    if len(future_games) == 0:
        upcoming_game_card.get("blocks").append(
            {
                "type": "plain_text",
                "text": f"No upcoming games found for {team_name} in the current season.",
                "emoji": False
            }
        )
    else:
        # Create blocks for each game returned by the API
        count = 0
        for i in range(0, len(future_games)):
            # Limit the number of games displayed to not overload the user's screen with a wall of info
            if count == number_of_games: break

            curr_game = future_games[i]

            future_game_prediction = None

            # Get predicted winner for each game
            try:
                predictions_endpoint = __url + "predictions"
                future_game_prediction_json = requests.get(predictions_endpoint, params={"fixture":curr_game.get("fixture").get("id")}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})
                future_game_prediction = json.loads(future_game_prediction_json.content).get("response")[0]
            except Exception:
                logging.error(Exception)

            # Extract data from game and prediction results
            next_games_data = __extract_next_games_data(curr_game, future_game_prediction)

            # Create blocks for future game data
            curr_game_card = __create_future_games_card_block(next_games_data)

            # Inform the user if the API sends back malformed data and return
            if not curr_game_card:
                result = client.chat_postMessage(
                    channel=message["channel"],
                    text="Error Getting Data from API",
                    blocks=[{
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": "Error in upcoming games data from API. Please try again later.",
                            "emoji": False
                        }
                    },
                ])
                return

            # Add blocks to card
            for item in curr_game_card:
                upcoming_game_card.get("blocks").append(item)

            count += 1

    # If a generic card was requested, return it
    # Primarily used for App Home
    if return_card: return upcoming_game_card

    # Send team-specific blocks to client for display
    client.chat_postMessage(
                channel=message["channel"],
                text="EPL Team Info Card",
                blocks=json.dumps(upcoming_game_card.get("blocks")))

# Get top 3 standings and next 3 games to update the app home
def get_app_home_data(client, event):
    # Get the user's ID and look up their favorite team
    user_id=event["user"]
    result = db.get_favorite_team(user_id)

    team_name = None
    if result is not None:
        team_name = result.get("team_name")

    # Reuse standings and upcoming games functionality to get blocks with required data
    top_3_standings_blocks = get_standings_data_all(None, None, True)
    upcoming_games_blocks = get_next_game_data(None, None, team_name, True)

    # Handle None responses
    if not top_3_standings_blocks or not upcoming_games_blocks:
        logging.error("Missing Standings or Upcoming Games Data")
        return []

    # Get current time. App home will tell the user when it was updated in local time.
    update_time = datetime.datetime.now()

    # Show the user what their current favorite team is
    fav_team = None

    if team_name is not None:
        fav_team = f"*{team_name}*. Displaying future games for this team."
    else:
        fav_team =  "*None Set*. Displaying future games featuring any team."

    # Create card for the app home
    app_home_blocks = {
        "blocks" : [
          {
            "type": "header",
            "text": {
              "type": "plain_text",
              "text": "👋 Welcome to the Home of SportsStatsBot! ⚽",
              "emoji": True
            }
          },
          {
			"type": "context",
			"elements": [
				{
					"type": "mrkdwn",
					"text": f"Last Updated: {update_time} | Favorite Team: {fav_team}"
				}
			]
		},
        {
        "type": "divider"
        },
        ]
    }

    # Add blocks to the card
    for item in top_3_standings_blocks.get("blocks"):
            app_home_blocks.get("blocks").append(item)

    for item in upcoming_games_blocks.get("blocks"):
            app_home_blocks.get("blocks").append(item)
    
    # Return the card
    return json.dumps(app_home_blocks.get("blocks"))

# Get the API's ID representing an EPL team
def get_team_id(team_name):
    teams_endpoint = __url + "teams"
    team_info_json = requests.get(teams_endpoint, params={"name":team_name}, headers={"x-apisports-key":os.environ.get("FOOTBALL_API_TOKEN")})

    if json.loads(team_info_json.content).get("results") == 0:
        return None
    else:
        team_info_dict = json.loads(team_info_json.content).get("response")[0]
        team_id = team_info_dict.get("team").get("id")
        return team_id
    
# Create set of blocks representing standings for a team
def __create_team_card_block(team_data):
    # Invoke None error handling in caller
    if not team_data:
        return None

    # Extract required data from supplied object
    team_name = team_data.get("team_name")
    team_rank = team_data.get("team_rank")
    team_logo_url = team_data.get("team_logo_url")
    team_wins = team_data.get("team_wins")
    team_draws = team_data.get("team_draws")
    team_losses = team_data.get("team_losses")
    team_total_points = team_data.get("team_total_points")
    team_home_wins = team_data.get("team_home_wins")
    team_home_draws = team_data.get("team_home_draws")
    team_home_losses = team_data.get("team_home_losses")
    team_away_wins = team_data.get("team_wins")
    team_away_draws = team_data.get("team_draws")
    team_away_losses = team_data.get("team_losses")

    # Create the blocks and inject values
    standings_entry = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Rank {team_rank} - {team_name}*"
            },
            "accessory": {
                "type": "image",
                "image_url": f"{team_logo_url}",
                "alt_text": "Team Logo"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Total Wins*: {team_wins} | *Total Draws*: {team_draws} | *Total Losses*: {team_losses} | *Total Points*: {team_total_points}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Home Wins*: {team_home_wins} | *Home Draws*: {team_home_draws} | *Home Losses*: {team_home_losses}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Away Wins*: {team_away_wins} | *Away Draws*: {team_away_draws} | *Away Losses*: {team_away_losses}"
            }
        },
        {
            "type": "divider"
        },
    ]
    # Return completed card
    return standings_entry

# Create set of blocks representing stats for a team
def __create_stats_card_block(team_data):
    # Invoke None error handling in caller
    if not team_data:
        return None

    # Extract Data from object
    team_name = team_data.get("team_name")
    team_logo_url = team_data.get("team_logo_url")
    team_wins = team_data.get("team_wins")
    team_draws = team_data.get("team_draws")
    team_losses = team_data.get("team_losses")
    team_home_wins = team_data.get("team_home_wins")
    team_home_draws = team_data.get("team_home_draws")
    team_home_losses = team_data.get("team_home_losses")
    team_away_wins = team_data.get("team_away_wins")
    team_away_draws = team_data.get("team_away_draws")
    team_away_losses = team_data.get("team_away_losses")
    team_goals_scored = team_data.get("team_goals_scored")
    team_goals_allowed = team_data.get("team_goals_allowed")
    team_home_goals_scored = team_data.get("team_home_goals_scored")
    team_home_goals_allowed = team_data.get("team_home_goals_allowed")
    team_away_goals_scored = team_data.get("team_away_goals_scored")
    team_away_goals_allowed = team_data.get("team_away_goals_allowed")
    venue_name = team_data.get("venue_name")
    venue_address = team_data.get("venue_address")
    venue_city = team_data.get("venue_city")
    venue_capacity = team_data.get("venue_capacity")
    venue_surface = team_data.get("venue_surface")

    # Create blocks representing team stats data and inject values
    team_stats_card = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Home Venue*: {venue_name} - {venue_address}, {venue_city} | *Capacity*: {venue_capacity} - *Surface*: {venue_surface}"
            },
            "accessory": {
                "type": "image",
                "image_url": f"{team_logo_url}",
                "alt_text": "Team Logo"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Home Wins*: {team_home_wins} | *Home Draws*: {team_home_draws} | *Home Losses*: {team_home_losses} | *Home Goals Scored*: {team_home_goals_scored} | *Home Goals Allowed*: {team_home_goals_allowed}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Away Wins*: {team_away_wins} | *Away Draws*: {team_away_draws} | *Away Losses*: {team_away_losses} | *Away Goals Scored*: {team_away_goals_scored} | *Away Goals Allowed*: {team_away_goals_allowed}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Total Wins*: {team_wins} | *Total Draws*: {team_draws} | *Total Losses*: {team_losses} | *Total Goals Scored*: {team_goals_scored} | *Total Goals Allowed*: {team_goals_allowed}"
            }
        },
        {
            "type": "divider"
        },
    ]
    
    # Return completed card
    return team_stats_card

# Create set of blocks representing a prior game
def __create_prior_games_card_block(game_data):
    # Invoke None error handling in caller
    if not game_data:
        return None

    # Extract Data from object
    home_name = game_data.get("home_name")
    away_name = game_data.get("away_name")
    home_goals = game_data.get("home_goals")
    away_goals = game_data.get("away_goals")
    venue_name = game_data.get("venue_name")
    venue_city = game_data.get("venue_city")
    game_datetime = game_data.get("game_datetime")

    winner_name = ""

    if int(away_goals) > int(home_goals):
        away_goals = f"*{away_goals}*"
        winner_name = away_name
    else:
        home_goals = f"*{home_goals}*"
        winner_name = home_name

    # Create card representing prior games and inject values
    game_card = [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*{away_name}* at *{home_name}*"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"_Final Score_: {away_name} - {away_goals} | {home_goals} - {home_name}"
			}
		},
        {
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"_Winner_: {winner_name}"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"_Venue_: *{venue_name}*, {venue_city} @ {game_datetime} UTC"
			}
		},
		{
			"type": "divider"
		},
	]
    
    # Return completed card
    return game_card

# Create set of blocks representing a future game
def __create_future_games_card_block(game_data):
    # Invoke None error handling in caller
    if not game_data:
        return None

    # Extract Data from object
    home_name = game_data.get("home_name")
    away_name = game_data.get("away_name")
    venue_name = game_data.get("venue_name")
    venue_city = game_data.get("venue_city")
    season_round = game_data.get("season_round")
    game_datetime = game_data.get("game_datetime")
    predicted_winner = game_data.get("predicted_winner")

    # Create card representing future games and inject values
    game_card = [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*{away_name}* at *{home_name}*"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"_Round_: *{season_round}*"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"_Venue_: *{venue_name}*, {venue_city} @ {game_datetime} UTC"
			}
		},
        {
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"_Predicted Winner_: *{predicted_winner}*"
			}
		},
		{
			"type": "divider"
		},
	]

    # Return completed card
    return game_card

# Extract standings data and return dict with extracted data
def __extract_standings_data(team_entry):
    curr_team_data = {
        "team_name" : team_entry.get("team").get("name"),
        "team_rank" : team_entry.get("rank"),
        "team_logo_url" : team_entry.get("team").get("logo"),
        "team_wins" : team_entry.get("all").get("win"),
        "team_draws" : team_entry.get("all").get("draw"),
        "team_losses" : team_entry.get("all").get("lose"),
        "team_total_points" : team_entry.get("points"),
        "team_home_wins" : team_entry.get("home").get("win"),
        "team_home_draws" : team_entry.get("home").get("draw"),
        "team_home_losses" : team_entry.get("home").get("lose"),
        "team_away_wins" : team_entry.get("away").get("win"),
        "team_away_draws" : team_entry.get("away").get("draw"),
        "team_away_losses" : team_entry.get("away").get("lose"),
    }
    return curr_team_data

# Extract team stats data and return dict with extracted data
def __extract_team_stats_data(team_stats, team_info):
    team_data = {
        "team_name" : team_stats.get("team").get("name"),
        "team_logo_url" : team_stats.get("team").get("logo"),
        "team_wins" : team_stats.get("fixtures").get("wins").get("total"),
        "team_draws" : team_stats.get("fixtures").get("draws").get("total"),
        "team_losses" : team_stats.get("fixtures").get("loses").get("total"),
        "team_home_wins" : team_stats.get("fixtures").get("wins").get("home"),
        "team_home_draws" : team_stats.get("fixtures").get("draws").get("home"),
        "team_home_losses" : team_stats.get("fixtures").get("loses").get("home"),
        "team_away_wins" : team_stats.get("fixtures").get("wins").get("away"),
        "team_away_draws" : team_stats.get("fixtures").get("draws").get("away"),
        "team_away_losses" : team_stats.get("fixtures").get("loses").get("away"),
        "team_goals_scored": team_stats.get("goals").get("for").get("total").get("total"),
        "team_goals_allowed": team_stats.get("goals").get("against").get("total").get("total"),
        "team_home_goals_scored": team_stats.get("goals").get("for").get("total").get("home"),
        "team_home_goals_allowed": team_stats.get("goals").get("against").get("total").get("home"),
        "team_away_goals_scored": team_stats.get("goals").get("for").get("total").get("away"),
        "team_away_goals_allowed": team_stats.get("goals").get("against").get("total").get("away"),
        "venue_name" : team_info.get("venue").get("name"),
        "venue_address": team_info.get("venue").get("address"),
        "venue_city": team_info.get("venue").get("city"),
        "venue_capacity" : team_info.get("venue").get("capacity"),
        "venue_surface" : team_info.get("venue").get("surface").capitalize(),
    }
    return team_data

# Extract past games data and return dict with extracted data
def __extract_past_games_data(curr_game):
    date = curr_game.get("fixture").get("date")
    date_object = dateutil.parser.isoparse(date)

    past_games_data = {
        "home_name" : curr_game.get("teams").get("home").get("name"),
        "away_name" : curr_game.get("teams").get("away").get("name"),
        "home_goals" : curr_game.get("goals").get("home"),
        "away_goals" : curr_game.get("goals").get("away"),
        "venue_name" : curr_game.get("fixture").get("venue").get("name"),
        "venue_city" : curr_game.get("fixture").get("venue").get("city"),
        "game_datetime" : str(date_object),
    }
    return past_games_data
    
# Extract next games data and return dict with extracted data
def __extract_next_games_data(curr_game, future_game_prediction):
    date = curr_game.get("fixture").get("date")
    date_object = dateutil.parser.isoparse(date)

    next_games_data = {
        "home_name" : curr_game.get("teams").get("home").get("name"),
        "away_name" : curr_game.get("teams").get("away").get("name"),
        "venue_name" : curr_game.get("fixture").get("venue").get("name"),
        "venue_city" : curr_game.get("fixture").get("venue").get("city"),
        "season_round" : curr_game.get("league").get("round"),
        "game_datetime" : str(date_object),
        "predicted_winner": future_game_prediction.get("predictions").get("winner").get("name") or "Prediction Unavailable"
    }
    return next_games_data
