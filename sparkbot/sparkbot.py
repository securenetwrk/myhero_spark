#! /usr/bin/python
'''
    Spark Bot for room and team management

    This Bot will use a provided Spark Account (identified by the Developer Token)
    and create a webhook to receive all messages sent to the account.

    This is the an example Service for a basic microservice demo application.
    The application was designed to provide a simple demo for Cisco Mantl

    There are several pieces of information needed to run this application.  It is
    suggested to set them as OS Environment Variables.  Here is an example on how to
    set them:

    # Details on the Cisco Spark Account to Use
    export spark_bot_email=demo@domain.com
    export spark_token=adfiafdadfadfaij12321kaf

    # Address and key for the Spark Bot itself
    export spark_bot_url=http://spark.domain.com
    export spark_bot_secret=DemoBotKey

    # Rooms to actively listen in:
    export active_rooms=Abcd1234Efgh5678ijkl1234mnop1234qrst5678uvwx1234abcd1234efgh5678ijkl1234,Abcd1234Efgh5678ijkl1234mnop1234qrst5678uvwx1234abcd1234efgh5678ijkl1235,Abcd1234Efgh5678ijkl1234mnop1234qrst5678uvwx1234abcd1234efgh5678ijkl1236
'''


__author__ = 'securenetwrk'


from flask import Flask, request, Response
import requests, json, re, logging, time

app = Flask(__name__)

spark_host = "https://api.ciscospark.com/"
spark_headers = {}
spark_headers["Content-type"] = "application/json"

commands = {
    "/invite": "Invite you to a team. Format: `/invite TeamName` ",
    "/inviteroom": "Invite you to a room. Format: `/invite RoomName` ",
    #    "/add": "Add a user to a team. Format: `/add OPTION` ",
    "/help": "Get help."
}



@app.route('/', methods=["POST"])
def process_webhook():
    post_data = request.get_json(force=True)
    # pprint(post_data)
    process_incoming_message(post_data)
    return ""

# Function to take action on incoming message
def process_incoming_message(post_data):
    pprint(post_data)

    webhook_id = post_data["id"]
    room_id = post_data["data"]["roomId"]

    message_id = post_data["data"]["id"]
#    pprint(message_id)
    message = get_message(message_id)
#    pprint(message)

    # First make sure not processing a message from the bot
    if message["personEmail"] == bot_email:
        return ""

    # Next make sure it is a Cisco employee
    if not message["personEmail"].endswith("@cisco.com"):
#        reply = "This is not the droid you are looking for"
#        send_message_to_room(room_id, reply)
        return ""

    ## Next make sure we are processing a message from an active room
    if message["roomType"] == "group":
        if message["roomId"] not in activerooms:
        #pprint(message["roomId"])
            return ""
        message["text"] = message["text"].partition(' ')[2]

    command = ""
    for c in commands.items():
        if message["text"].find(c[0]) == 0:
            command = c[0]
            sys.stderr.write("Found command: " + command + "\n")
            # debug_msg(post_data, "Found command: " + command)
            break

    # Take action based on command
    # If no command found, send help

    reply = "None"

    if command in ["/h","/help"]:
        reply = send_help(post_data)
    elif command in ["/invite"]:
        reply = invite_to_team(message)
    elif command in ["/inviteroom"]:
        reply = invite_to_room(message)
    elif command in ["/add"]:
        reply = add_to_team(message)

    if reply not in ["None"]:
        send_message_to_room(room_id, reply)

    time.sleep(2) #avoid too much spam

def send_help(post_data):
    message = "Thanks for your interest in me.  \n"
    message = message + "I understand the following commands:  \n"
    for c in commands.items():
        message = message + "* **%s**: %s \n" % (c[0], c[1])
    return message


def debug_msg(post_data, message):
    send_message_to_room(get_message(post_data["data"]["id"])["roomId"], message)



# Spark Utility Functions
#### Message Utilities
def send_message_to_email(email, message):
    spark_u = spark_host + "v1/messages"
    message_body = {
        "toPersonEmail" : email,
        "markdown" : message
    }
    page = requests.post(spark_u, headers = spark_headers, json=message_body)
    message = page.json()
    return message

def send_message_to_room(room_id, message):
    spark_u = spark_host + "v1/messages"
    message_body = {
        "roomId" : room_id,
        "markdown" : message
    }
    page = requests.post(spark_u, headers = spark_headers, json=message_body)
    message = page.json()
    return message

def get_message(message_id):
    spark_u = spark_host + "v1/messages/" + message_id
    #pprint(spark_u)
    page = requests.get(spark_u, headers = spark_headers)
    message = page.json()
    #pprint(message)
    return message

#### Webhook Utilities
def current_webhooks():
    spark_u = spark_host + "v1/webhooks"
    page = requests.get(spark_u, headers = spark_headers)
    webhooks = page.json()
    return webhooks["items"]

def create_webhook(roomId, target, webhook_name = "New Webhook"):
    spark_u = spark_host + "v1/webhooks"
    spark_body = {
        "name": webhook_name,
        "targetUrl": target,
        "resource": "messages",
        "event": "created"
    }
    #pprint(spark_body)

    if (roomId != ""):
        {
            spark_body["filter"]: "roomId=" + roomId
        }

    page = requests.post(spark_u, headers = spark_headers, json=spark_body)
    webhook = page.json()
    #pprint(webhook)
    return webhook

def update_webhook(webhook_id, target, name):
    spark_u = spark_host + "v1/webhooks/" + webhook_id
    spark_body = {
        "name" : name,
        "targetUrl" : target
    }
    page = requests.put(spark_u, headers = spark_headers, json=spark_body)
    webhook = page.json()
    return webhook

def delete_webhook(webhook_id):
    spark_u = spark_host + "v1/webhooks/" + webhook_id
    page = requests.delete(spark_u, headers = spark_headers)

def setup_webhook(room_id, target, name):
    webhooks = current_webhooks()
    webhook_id = ""
    #pprint(webhooks)

    # Legacy test for room based demo
    if (room_id != ""):
        # Look for a Web Hook for the Room
        for webhook in webhooks:
            if webhook["filter"] == "roomId=" + room_id:
                # print("Found Webhook")
                webhook_id = webhook["id"]
                break
    # For Global Webhook
    else:
        for webhook in webhooks:
            if webhook["name"] == name:
                # print("Found Webhook")
                webhook_id = webhook["id"]
                break

    # If Web Hook not found, create it
    if webhook_id == "":
        webhook = create_webhook(room_id, target, name)
        webhook_id = webhook["id"]
    # If found, update url
    else:
        webhook = update_webhook(webhook_id, target, name)

    # pprint(webhook)
    return webhook_id

#### Room Utilities
def current_rooms():
    spark_u = spark_host + "v1/rooms"
    page = requests.get(spark_u, headers = spark_headers)
    rooms = page.json()
    return rooms["items"]

def leave_room(room_id):
    membership_id = get_membership_for_room(room_id)
    spark_u = spark_host + "v1/memberships/" + membership_id
    page = requests.delete(spark_u, headers = spark_headers)

def get_membership_for_room(room_id):
    # Get Membership ID for Room
    spark_u = spark_host + "v1/memberships?roomId=%s" % (room_id)
    page = requests.get(spark_u, headers = spark_headers)
    memberships = page.json()["items"]
    return memberships

def find_room(message):
    # Find a room within a list of current room
    messagetext = message["text"]
    messagetext = messagetext.partition(' ')[2]
    pprint(messagetext)
    roompage = current_rooms()
#    pprint(roompage)
    for room in roompage:
        if room["title"].lower() == messagetext.lower():
            sys.stderr.write("Found a matching room: " + room["title"] + " - " + room["id"] + " for " + message["personEmail"] + "\n")
            return room
    return "None"

def invite_to_room(message):
    # Invite user to a team
    room = find_room(message)
    if room == "None":
        return "None"
    spark_u = spark_host + "v1/memberships"
    message_body = {
        "roomId" : room["id"],
        "personEmail" : message["personEmail"]
    }
    page = requests.post(spark_u, headers = spark_headers, json=message_body)
    message = page.json()
    return message

#### Team Utilities
def get_current_teams():
    # Get list of teams
    spark_u = spark_host + "v1/teams"
    page = requests.get(spark_u, headers = spark_headers)
    teams = page.json()
    return teams["items"]

def get_membership_for_team(team_id):
    # Get Membership for Team
    spark_u = spark_host + "v1/team/memberships?teamId=%s" % (team_id)
    page = requests.get(spark_u, headers = spark_headers)
    memberships = page.json()
    return memberships

def find_team(message):
    # Find a team within a list of current teams
    messagetext = message["text"]
    messagetext = messagetext.partition(' ')[2]
    teampage = get_current_teams()
    for team in teampage:
        if team["name"].lower() == messagetext.lower():
            sys.stderr.write("Found a matching team: " + team["name"] + " - " + team["id"] + " for " + message["personEmail"] + "\n")
            return team
    return "None"

def invite_to_team(message):
    # Invite user to a team
    team = find_team(message)
    if team == "None":
        return "None"
    spark_u = spark_host + "v1/team/memberships"
    message_body = {
        "teamId" : team["id"],
        "personEmail" : message["personEmail"]
    }
    page = requests.post(spark_u, headers = spark_headers, json=message_body)
    message = page.json()
    return message


# Standard Utility
def valid_request_check(request):
    try:
        if request.headers["key"] == secret_key:
            return (True, "")
        else:
            error = {"Error": "Invalid Key Provided."}
            sys.stderr.write(error + "\n")
            status = 401
            resp = Response(json.dumps(error), content_type='application/json', status=status)
            return (False, resp)
    except KeyError:
        error = {"Error": "Method requires authorization key."}
        sys.stderr.write(str(error) + "\n")
        status = 400
        resp = Response(json.dumps(error), content_type='application/json', status=status)
        return (False, resp)

if __name__ == '__main__':
    from argparse import ArgumentParser
    import os, sys
    from pprint import pprint

    # Setup and parse command line arguments
    parser = ArgumentParser("MyHero Spark Interaction Bot")
    parser.add_argument(
        "-t", "--token", help="Spark User Bearer Token", required=False
    )
    parser.add_argument(
        "-u", "--boturl", help="Local Host Address for this Bot", required=False
    )
    parser.add_argument(
        "-b", "--botemail", help="Email address of the Bot", required=False
    )
    parser.add_argument(
        "--demoemail", help="Email Address to Add to Demo Room", required=False
    )
    parser.add_argument(
        "-s", "--secret", help="Key Expected in API Calls", required=False
    )
    parser.add_argument(
        "-a", "--activerooms", help="comma-delimited list of active rooms", required=False
    )
    parser.add_argument(
        "-au", "--authorizedusers", help="comma-delimited list of authorized users", required=False
    )

    args = parser.parse_args()

    # Set application run-time variables
    # Values can come from
    #  1. Command Line
    #  2. OS Environment Variables
    #  3. Raw User Input
    bot_url = args.boturl
    if (bot_url == None):
        bot_url = os.getenv("spark_bot_url")
        if (bot_url == None):
            bot_url = raw_input("What is the Application Address for this Bot? ")
    # print "Bot URL: " + bot_url
    sys.stderr.write("Bot URL: " + bot_url + "\n")

    bot_email = args.botemail
    if (bot_email == None):
        bot_email = os.getenv("spark_bot_email")
        if (bot_email == None):
            bot_email = raw_input("What is the Email Address for this Bot? ")
    # print "Bot Email: " + bot_email
    sys.stderr.write("Bot Email: " + bot_email + "\n")

    spark_token = args.token
    # print "Spark Token: " + str(spark_token)
    if (spark_token == None):
        spark_token = os.getenv("spark_token")
        # print "Env Spark Token: " + str(spark_token)
        if (spark_token == None):
            get_spark_token = raw_input("What is the Cisco Spark Token? ")
            # print "Input Spark Token: " + str(get_spark_token)
            spark_token = get_spark_token
    # print "Spark Token: " + spark_token
    # sys.stderr.write("Spark Token: " + spark_token + "\n")
    sys.stderr.write("Spark Token: REDACTED\n")

    secret_key = args.secret
    if (secret_key == None):
        secret_key = os.getenv("spark_bot_secret")
        if (secret_key == None):
            get_secret_key = raw_input("What is the Authorization Key to Require? ")
            secret_key = get_secret_key
    sys.stderr.write("Secret Key: " + secret_key + "\n")

    active_rooms = args.activerooms
    if (active_rooms == None):
        active_rooms = os.getenv("active_rooms")
        activerooms = active_rooms.split(",")
   # sys.stderr.write("Active rooms: " + active_rooms + "\n")

    authorized_users = args.authorizedusers
    if (authorized_users == None):
        authorized_users = os.getenv("authorized_users")
        authorizedusers = authorized_users.split(",")
    # sys.stderr.write("Active rooms: " + active_rooms + "\n")

    # Set Authorization Details for external requests
    spark_headers["Authorization"] = "Bearer " + spark_token

    # Create Web Hook to recieve ALL messages
#    global_webhook_id = setup_webhook("", bot_url, "Global Webhook")
#    sys.stderr.write("Global Web Hook ID: " + global_webhook_id + "\n")

    app.run(debug=True, host='0.0.0.0', port=int("5000"))

