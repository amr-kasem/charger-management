import boto3
import os
import logging

from ocpp.v201.enums import Action
from ocpp.messages import CallResult

# Import all handlers from the handlers module
from ocpp_message_processor.handlers import *

logger = logging.getLogger(__name__)

class MessageProcessor:
    """Main processor for OCPP messages"""
    
    def __init__(self):
        self.iot = boto3.client("iot-data", region_name=os.environ["AWS_REGION"])
        self._handlers = {
            # Incoming messages from charge points
            Action.boot_notification: BootNotificationHandler(self.iot),
            Action.heartbeat: HeartbeatHandler(),
            Action.status_notification: StatusNotificationHandler(),
            Action.transaction_event: TransactionEventHandler(self.iot),
            
            # Remote command handlers for messages sent from central system to charge points
            Action.request_start_transaction: RequestStartTransactionHandler(self.iot),
            Action.request_stop_transaction: RequestStopTransactionHandler(self.iot),
            
            # Add new handlers here as needed
        }
        # Handler for CallResult messages (responses to remote commands)
        self._call_result_handler = CallResultHandler(self.iot)
        self._default_handler = UnsupportedMessageHandler()
    
    def process_message(self, charge_point_id, message):
        """Process incoming message by delegating to the appropriate handler"""
        logger.info(f"Message received from {charge_point_id}: {message}")
        
        # Check if this is a CallResult message (response to a command we sent)
        # CallResult messages are identified by having no action or a message_type of 3
        if message is CallResult:
            logger.info(f"Processing CallResult from {charge_point_id}: {message}")
            response = self._call_result_handler.handle(charge_point_id, message)
            # CallResult responses don't need a response from us
            return
        elif not hasattr(message, 'action') or message.action is None:
            logger.info(f"Processing message with no action from {charge_point_id}: {message}")
            response = self._call_result_handler.handle(charge_point_id, message)
            # No action messages don't need a response
            return
        
        # For regular messages, get the appropriate handler and process
        handler = self._handlers.get(message.action, self._default_handler)
        response = handler.handle(charge_point_id, message)
        
        # Only send a response if one was returned by the handler
        if response is not None:
            self.send_message_to_charge_point(charge_point_id, response)

    def send_message_to_charge_point(self, charge_point_id, message):
        """Send a message to a charge point via IoT"""
        if message is None:
            logger.debug(f"No message to send to {charge_point_id}")
            return None
        
        iot_request = {
            "topic": f"{charge_point_id}/out",
            "qos": 1,
            "payload": message.to_json(),
        }
        logger.debug(f"Sending message to {charge_point_id}: {iot_request}")

        iot_response = self.iot.publish(**iot_request)
        logger.debug(f"IoT publish response: {iot_response}")

        return iot_response
