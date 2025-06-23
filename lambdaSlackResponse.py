import json
import logging
import os

import boto3
import urllib3
from botocore.exceptions import BotoCoreError, ClientError

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
SLACK_TOKEN = os.environ.get("slackToken") # you can get this from the slack app : OAuth & Permissions >
SLACK_URL = os.environ.get("slackUrl") # https://slack.com/api/chat.postMessage
REGION_NAME = os.environ.get("regionName") # you can get this from the bedrock agent
AGENT_ID = os.environ.get("agentId") # you can get this from the bedrock agent
AGENT_ALIAS_ID = os.environ.get("agentAliasId") # you can get this from the bedrock agent
BOT_USER_ID = "U090ZPKV2JE"  # Replace with your actual Bot User ID

# Initialize HTTP connection pool
http = urllib3.PoolManager()


def send_message_to_slack(message: str, channel: str ) -> dict:
    """
    Sends a message to a Slack channel.

    Args:
        message (str): The text to send.
        channel (str): The Slack channel ID.

    Returns:
        dict: Slack API response.
    """
    payload = {
        "channel": channel,
        "text": message
    }

    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = http.request("POST", SLACK_URL, headers=headers, body=json.dumps(payload))
        return json.loads(response.data.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to send message to Slack: {e}")
        return {"ok": False, "error": str(e)}


def query_bedrock_agent(question: str, session_id: str, channel: str ) -> str:
    """
    Sends a user question to the Bedrock agent and streams the response to Slack.

    Args:
        question (str): User input.
        session_id (str): Unique session ID.
        channel (str): Slack channel ID.

    Returns:
        str: Full concatenated agent response.
    """
    client = boto3.client("bedrock-agent-runtime", region_name=REGION_NAME)
    full_response = ""

    try:
        response = client.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=question
        )

        for event in response.get("completion", []):
            if "chunk" in event:
                part = event["chunk"]["bytes"].decode("utf-8")
                send_message_to_slack(part, channel)
                full_response += part

    except (BotoCoreError, ClientError) as e:
        logger.error(f"Bedrock agent invocation failed: {e}")
    return full_response


def lambda_handler(event, context):
    """
    AWS Lambda function entry point.

    Args:
        event (dict): Lambda event payload.
        context (LambdaContext): Runtime information.

    Returns:
        dict: HTTP response.
    """
    logger.info(f"Received event: {event}")

    try:
        body = json.loads(event.get("body", "{}"))
        slack_event = body.get("event", {})
        event_type = slack_event.get("type")

        user_message = slack_event.get("text")
        channel_id = slack_event.get("channel")
        timestamp = slack_event.get("ts")
        user_id = slack_event.get("user")
        channel_type = slack_event.get("channel_type")

        # Process only direct messages from users (not from the bot itself)
        if (
            event_type == "message"
            and channel_type == "im"
            and user_id != BOT_USER_ID
        ):
            send_message_to_slack("Thinking ...", channel_id)
            query_bedrock_agent(user_message, timestamp, channel_id)

        return {
            "statusCode": 200,
            "body": json.dumps({"msg": "Message received"})
        }

    except Exception as e:
        logger.error(f"Error processing event: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
