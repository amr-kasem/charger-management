import json
import boto3
import uuid
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

iot_client = boto3.client('iot-data')

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    body = json.loads(event['body'])
    
    # Extract charge point ID and transaction ID from the event
    try:
        charge_point_id = body['chargePointId']
        transaction_id = body['transactionId']
    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing required parameter: {str(e)}'})
        }
    
    # Create RequestStopTransaction OCPP 2.0.1 command
    message = [
        2,  # Call message type
        str(uuid.uuid4()),  # Unique message ID
        "RequestStopTransaction",
        {
            "transactionId": transaction_id
        }
    ]
    
    logger.info(f"Sending RequestStopTransaction to {charge_point_id}: {json.dumps(message)}")
    
    # Publish to the charge point's 'out' topic
    topic = f"{charge_point_id}/out"
    try:
        response = iot_client.publish(
            topic=topic,
            payload=json.dumps(message)
        )
        logger.info(f"Published message, response: {response}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'RequestStopTransaction command sent successfully',
                'messageId': message[1],
                'chargePointId': charge_point_id,
                'transactionId': transaction_id
            })
        }
    except Exception as e:
        logger.error(f"Error publishing message: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to publish message: {str(e)}'})
        } 