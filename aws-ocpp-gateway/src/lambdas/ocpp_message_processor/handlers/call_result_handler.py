import json
from datetime import datetime
import logging
from ocpp_message_processor.handlers.handler import Handler

logger = logging.getLogger(__name__)

class CallResultHandler(Handler):
    """
    Handler for CallResult messages.
    
    This handler processes CallResult messages that are responses to remote commands
    sent to charge points, such as RequestStartTransaction and RequestStopTransaction.
    """
    
    def __init__(self, iot_client=None):
        self.iot = iot_client
    
    def handle(self, charge_point_id, message):
        """
        Handle CallResult messages by logging and updating the charge point's shadow.
        
        Args:
            charge_point_id (str): ID of the charge point
            message: The CallResult message
            
        Returns:
            None: CallResults don't require a response
        """
        logger.info(f"Handling CallResult from {charge_point_id}: {message}")
        
        # We don't need to send a response to a CallResult
        # Just process it and update shadow if needed
        
        # Try to determine what command this is a response to based on payload
        if 'status' in message.payload:
            status = message.payload.get('status')
            # Update shadow with the call result info if IoT client is available
            if self.iot:
                self._update_shadow(charge_point_id, message)
                
            if status == "Accepted":
                logger.info(f"Remote command was accepted by {charge_point_id}")
            else:
                logger.warning(f"Remote command was rejected by {charge_point_id}: {message.payload}")
        
        # Return None to indicate no response is needed
        # The message processor should check for None and not attempt to send a response
        return None
    
    def _update_shadow(self, charge_point_id, message):
        """
        Update the charge point's shadow with the call result information.
        
        Args:
            charge_point_id (str): ID of the charge point
            message: The CallResult message
        """
        # Create a shadow document with the call result info
        shadow_update = {
            "state": {
                "reported": {
                    "lastCallResult": {
                        "messageId": message.unique_id,
                        "receivedAt": datetime.utcnow().isoformat(),
                        "payload": message.payload
                    }
                }
            }
        }
        
        try:
            response = self.iot.publish(
                topic=f"$aws/things/{charge_point_id}/shadow/update",
                qos=1,
                payload=json.dumps(shadow_update)
            )
            logger.debug(f"Shadow update response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error updating shadow: {e}")
            return None 