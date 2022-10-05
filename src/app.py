import os
import re
import string

# Use the package we installed
from slack_bolt import App, Say, BoltContext
from slack_sdk import WebClient

# Import function to connect to football data api
import sports_api_functions as sports_api
import dynamo_functions as db

# Define format for accepted commands
__help_command = re.compile("(help|Help|HELP)")
__standings_command = re.compile("(standings|Standings|STANDINGS)")
__team_command = "team"
__past_games_command = "pastgames"
__next_games_command = "nextgames"
__fav_team_set_command = "faveset"
__fav_team_get_command = "faveget"
__fav_team_delete_command = "favedel"

# Initializes app with bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Handle team join event to let the user know how to see available commands
@app.event("team_join")
def handle_team_join(messagesay):
    say("Welcome! Type *help* to see my commands!")

# Handle mention event to let the user know how to see available commands
@app.event("app_mention")
def event_test(body, say, logger):
    logger.info(body)
    say(f"How's it going? I hope you're having a great day! \nType *help* to see available commands.")

# Help command. Bot tells the user what commands they can use
@app.message(__help_command)
def show_help(message, say):
    user = message['user']
    say(f"Hi <@{user}>!"
    + "\n\nHere are the currently available commands:" 
    + "\n*standings*: Get current English Premier League (EPL) standings."
    + "\n*team [team_name]*: Get the current EPL standings for the specified team."
    + "\n*pastgames*: Get details of the past 3 EPL games."
    + "\n*pastgames [team_name]*: Get details of the past 3 games the specified team has played."
    + "\n*nextgames*: Get details of the next 3 EPL games."
    + "\n*nextgames [team_name]*: Get details of the next 3 games the specified team is scheduled to play."
    + "\n*faveset [team name]*: Set (or change) your favorite EPL team. Favorite team is used to personalize the home tab."
    + "\n*faveget*: See your currently set favorite EPL team."
    + "\n*favedel*: Delete your currently set favorite EPL team."
    + "\n\n_Note_: When the bot recognizes a command, it will acknowledge it with a 👍 reaction to let you know the bot is working on it.")

# For all long running commands, the bot responds to recognized commands with a thumbs up reaction
# This lets the user know that the bot has understood the command and is running it

# Standings command. Gets current EPL standings
@app.message(__standings_command)
def league_standings(client, message, say, body: dict, context: BoltContext):
    message_ts = body["event"]["ts"]
    api_response = client.reactions_add(
        channel=context.channel_id,
        timestamp=message_ts,
        name="thumbsup",
      )
    sports_api.get_standings_data_all(client, message)

# Team command. Gets current team stats for specified team
@app.message(__team_command)
def team_lookup(client, message, say, body: dict, context: BoltContext):
    message_ts = body["event"]["ts"]
    api_response = client.reactions_add(
        channel=context.channel_id,
        timestamp=message_ts,
        name="thumbsup",
      )

    try:
        # Get team name from message
        msg = message['text']
        start_index = msg.find(__team_command) + len(__team_command)
        team_name = string.capwords(msg[start_index:].strip())

        # Get data from API
        sports_api.get_team_stats_data(client, message, team_name)
        sports_api.get_past_games_data(client, message, team_name)
    except IndexError:
        say("Please ensure you have provided a valid EPL team name.")

# Past games command. Gets past 3 games for a team or generally for the EPL
@app.message(__past_games_command)
def past_game(client, message, say, body: dict, context: BoltContext):
    message_ts = body["event"]["ts"]
    api_response = client.reactions_add(
        channel=context.channel_id,
        timestamp=message_ts,
        name="thumbsup",
      )

    try:
        # Get team name from message
        msg = message['text']
        start_index = msg.find(__past_games_command) + len(__past_games_command)
        team_name = string.capwords(msg[start_index:].strip())

        # Get data from API
        sports_api.get_past_games_data(client, message, team_name)
    except IndexError:
        say("Please ensure you have provided a valid EPL team name.")

# Next games command. Gets next 3 games for a team or generally for the EPL
@app.message(__next_games_command)
def next_game(client, message, say, body: dict, context: BoltContext):
    message_ts = body["event"]["ts"]
    api_response = client.reactions_add(
        channel=context.channel_id,
        timestamp=message_ts,
        name="thumbsup",
      )

    try:
        # Get team name from message
        msg = message['text']
        start_index = msg.find(__next_games_command) + len(__next_games_command)
        team_name = string.capwords(msg[start_index:].strip())

        # Get data from API
        sports_api.get_next_game_data(client, message, team_name)
    except IndexError:
        say("Please ensure you have provided a valid EPL team name.")

# Set the user's favorite team in DynamoDB
@app.message(__fav_team_set_command)
def set_favorite_team(client, message, say, body: dict, context: BoltContext):
    message_ts = body["event"]["ts"]
    api_response = client.reactions_add(
      channel=context.channel_id,
      timestamp=message_ts,
      name="thumbsup",
    )

    # Extract the team name from the message
    msg = message['text']
    start_index = msg.find(__fav_team_set_command) + len(__fav_team_set_command)
    team_name = string.capwords(msg[start_index:].strip())

    # Get user ID and call dynamo to create/update the entry
    user_id = message['user']
    res = db.set_favorite_team(user_id, team_name)

    if res:
      say(f"Your favorite team has been set to {team_name}")
    else:
      say("Unable to set favorite team. Please ensure you have provided a valid EPL team name or try again later.")

# Get the user's favorite team from DynamoDB
@app.message(__fav_team_get_command)
def get_favorite_team(client, message, say, body: dict, context: BoltContext):
    message_ts = body["event"]["ts"]
    api_response = client.reactions_add(
      channel=context.channel_id,
      timestamp=message_ts,
      name="thumbsup",
    )

    # Get user ID and call dynamo to get the entry
    user_id = message['user']
    result = db.get_favorite_team(user_id)

    if result is not None:
      team_name = result.get("team_name")
      say(f"Your favorite team is currently set to {team_name}. Use *{__fav_team_set_command}* to change it.")
    else:
      say(f"You currently do not have a favorite team set. Use *{__fav_team_set_command}* to set it.")

# Remove the user's favorite team from DynamoDB
@app.message(__fav_team_delete_command)
def remove_favorite_team(client, message, say, body: dict, context: BoltContext):
    message_ts = body["event"]["ts"]
    api_response = client.reactions_add(
      channel=context.channel_id,
      timestamp=message_ts,
      name="thumbsup",
    )

    # Get user ID and call dynamo to delete the entry
    user_id = message['user']
    res = db.remove_favorite_team(user_id)

    if res == 200:
      say("Your favorite team has been removed.")
    elif res == 404:
      say(f"You currently do not have a favorite team set. Use *{__fav_team_set_command}* to set it.")
    else:
      say("Unable to remove favorite team. Please try again later.")


# Handle App Home event. Updates App Home with top 3 teams and next 3 EPL games
@app.event("app_home_opened")
def update_home_tab(client, event, logger):
  try:
    client.views_publish(
      user_id=event["user"],
      view={
        "type": "home",
        "callback_id": "home_view",

        # Get blocks to display as app home
        "blocks": sports_api.get_app_home_data(client, event)
      }
    )
  except Exception as e:
    logger.error(f"Error publishing home tab: {e}")

# Handle error conditions not caught elsewhere
@app.error
def global_error_handler(error, body, logger):
    logger.exception(error)
    logger.info(body)

# Start your app
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))