# dynamo_functions.py
# This class is responsible for holding the functions that interact with AWS DynamoDB
import boto3

import sports_api_functions as sports_api

# Creat dynamo resource and set table resource
__dynamodb = boto3.resource('dynamodb')
__dynamo_table = __dynamodb.Table('sports_bot_user_preferences')

# Create/Update user's favorite team in Dynamo
def set_favorite_team(user_id, team_name):
    team_id = sports_api.get_team_id(team_name)
    
    if team_id is None: return False

    res =__dynamo_table.put_item(
        Item={
            "user_id" : user_id,
            "team_name": team_name,
            "team_id": team_id
        }
    )
    return res.get("ResponseMetadata").get("HTTPStatusCode") == 200

# Read user's favorite team in Dynamo
def get_favorite_team(user_id):
    res = __dynamo_table.get_item(
        Key={
            "user_id" : user_id
        }
    )
    if "Item" in res:
        team_name = res.get("Item").get("team_name")
        team_id = res.get("Item").get("team_id")
        return {"team_name" : team_name, "team_id" : int(team_id)}
    else:
        return None

# Delete user's favorite team in Dynamo
def remove_favorite_team(user_id):
    # Check if the user hss a favorite team
    fav_res = get_favorite_team(user_id)
    if fav_res is None:
        return 404

    # Delete it if the user has a favorite team set
    res = __dynamo_table.delete_item(
        Key={
            "user_id" : user_id
        }
    )
    return res.get("ResponseMetadata").get("HTTPStatusCode")
