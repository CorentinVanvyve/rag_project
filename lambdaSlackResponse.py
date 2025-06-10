import json
import logging
import os

import boto3
import urllib3
from botocore.exceptions import BotoCoreError, ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
SLACK_TOKEN = os.environ.get("slackToken") # you can get this from the slack app : OAuth & Permissions > Bot User OAuth Token
SLACK_URL = os.environ.get("slackUrl") # https://slack.com/api/chat.postMessage
REGION_NAME = os.environ.get("regionName") # you can get this from the bedrock agent
AGENT_ID = os.environ.get("agentId") # you can get this from the bedrock agent
AGENT_ALIAS_ID = os.environ.get("agentAliasId") # you can get this from the bedrock agent

# Reuse HTTP connection
http = urllib3.PoolManager()

#  Send message to Slack
def send_slack_message(message: str, channel: str, ts: str = None) -> dict:
    data = {
        "channel": channel,
        "text": message,
        "thread_ts": ts
    }
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = http.request("POST", SLACK_URL, headers=headers, body=json.dumps(data))
        logger.info(f"Slack request sent: {data}")
        return json.loads(response.data.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to send message to Slack: {e}")
        return {"ok": False, "error": str(e)}

#  Call Bedrock agent
def invoke_bedrock_agent(question: str, session_id: str, channel: str, ts: str) -> str:
    client = boto3.client("bedrock-agent-runtime", region_name=REGION_NAME)
    full_response = ""

    try:
        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=question
        )
        logger.info("Agent invoked successfully.")

        for event in response.get("completion", []):
            if "chunk" in event:
                message_part = event["chunk"]["bytes"].decode("utf-8")
                send_slack_message(message_part, channel, ts)
                full_response += message_part

    except (BotoCoreError, ClientError) as e:
        logger.error(f"Bedrock agent invocation failed: {e}")
    return full_response

#  Lambda handler
def lambda_handler(raw_event, context):
    logger.info(f"Lambda triggered: {context.function_name} | Request ID: {context.aws_request_id}")

    try:
        payload = json.loads(raw_event.get("body", "{}"))
        event = payload.get("event", {})
        event_type = event.get("type")

        # Extract required values
        question = event.get("text")
        ts = event.get("ts")
        thread_ts = event.get("thread_ts")
        channel = event.get("channel")
        slack_user_id = event.get("user")

        logger.info(f"Event type: {event_type}, Channel: {channel}, User: {slack_user_id}")

        # Respond to direct messages from users (exclude bot's own ID)
        if (
            event_type == "message"
            and event.get("channel_type") == "im"
            and slack_user_id != "U08QUTRS6SZ"
        ):
            send_slack_message("Thinking ...", channel, ts)
            invoke_bedrock_agent(question, thread_ts or ts, channel, ts)

        return {
            "statusCode": 200,
            "body": json.dumps({"msg": "Message received"})
        }

    except Exception as e:
        logger.error(f"Error handling event: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Server Error"})
        }
