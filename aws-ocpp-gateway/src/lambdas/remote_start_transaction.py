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
    # Extract charge point ID and other parameters from the event
    try:
        charge_point_id = body['chargePointId']
        id_tag = body.get('idTag', str(uuid.uuid4()))
        connector_id = body.get('connectorId', 1)
        
        # Optional parameters
        transaction_data = {}
        if 'transactionData' in event:
            transaction_data = event['transactionData']
    except KeyError as e:
        logger.error(f"Missing required parameter: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Missing required parameter: {str(e)}'})
        }
    
    # Create RequestStartTransaction OCPP 2.0.1 command
    message = [
        2,  # Call message type
        str(uuid.uuid4()),  # Unique message ID
        "RequestStartTransaction",
        {
            "idToken": {
                "idToken": id_tag,
                "type": "ISO14443"
            },
            "evseId": connector_id,
            "remoteStartId": int(uuid.uuid4().int & 0xFFFFFFFF)  # Generate a numeric ID within 32-bit range
        }
    ]
    
    # Add additional transaction data if provided
    if transaction_data:
        message[3].update(transaction_data)
    
    logger.info(f"Sending RequestStartTransaction to {charge_point_id}: {json.dumps(message)}")
    
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
                'message': 'RequestStartTransaction command sent successfully',
                'messageId': message[1],
                'chargePointId': charge_point_id
            })
        }
    except Exception as e:
        logger.error(f"Error publishing message: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to publish message: {str(e)}'})
        } 