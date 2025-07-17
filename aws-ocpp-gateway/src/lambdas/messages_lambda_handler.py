import json
import logging
import ocpp.messages

from ocpp_message_processor import MessageProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create processor instance
processor = MessageProcessor()

def lambda_handler(event, _):
    """AWS Lambda entry point for processing OCPP messages"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    for record in event["Records"]:
        logger.debug(f"Processing record: {json.dumps(record)}")
        handle_record(record)

    return {"statusCode": 200, "body": "Messages processed successfully"}


def handle_record(record):
    """Process a single SQS record containing an OCPP message"""
    try:
        body = json.loads(record["body"])
        charge_point_id = body["chargePointId"]
        message_json = json.dumps(body["message"])
        
        logger.info(f"Processing message from charge point {charge_point_id}: {message_json}")
        
        # Unpack the message from JSON to OCPP object
        message = ocpp.messages.unpack(message_json)
        
        # Process the message
        processor.process_message(charge_point_id, message)
        
        logger.info(f"Successfully processed message from {charge_point_id}")
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        # Don't re-raise to avoid failing the entire batch

