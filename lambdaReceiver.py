import json

import boto3

# def lambda_handler(event, context):
#     client = boto3.client('lambda')

#     response = client.invoke(
#         FunctionName='lambdaSlackResponse',
#         InvocationType='Event',
#         Payload=json.dumps(event)
#     )

#     return {
#         'statusCode': 200,
#         'body': json.dumps({'msg': "message recevied"})
#     }


def lambda_handler(event, context):
    body = json.loads(event['body'])

    return {
        'statusCode': 200,
        'body': body['challenge']
    }