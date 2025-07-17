import json
import boto3
from datetime import datetime, timezone
from ocpp_message_processor.handlers.handler import Handler

class RequestStopTransactionHandler(Handler):
    """
    Handler for RequestStopTransaction messages.
    
    This handler processes incoming RequestStopTransaction messages from the central system
    and returns a response to indicate the status of the transaction stop request.
    """
    
    def __init__(self, iot_client=None):
        self.iot = iot_client
    
    def handle(self, charge_point_id, message):
        """
        Handle RequestStopTransaction messages by creating an appropriate response.
        
        Args:
            charge_point_id (str): ID of the charge point
            message: The RequestStopTransaction message
            
        Returns:
            The response to send back to the charge point
        """
        print(f"Handling RequestStopTransaction for {charge_point_id}")
        print(f"Message payload: {message.payload}")
        
        # Extract transaction ID from the message
        transaction_id = message.payload.get('transactionId')
        
        # In a real implementation, you might want to validate the transaction exists
        # and belongs to this charge point before accepting the stop request
        
        # Update shadow with transaction information if iot client is available
        if self.iot:
            self._update_transaction_info(charge_point_id, transaction_id)
        
        # Create and return the response
        response = message.create_call_result({
            "status": "Accepted"  # Could be "Accepted" or "Rejected"
        })
        
        return response
    
    def _update_transaction_info(self, charge_point_id, transaction_id):
        """Update the charge point shadow to indicate the transaction has ended"""
        
        shadow_update = {
            "state": {
                "reported": {
                    "currentTransaction": {
                        "transactionId": transaction_id,
                        "stopTime": datetime.now(timezone.utc).isoformat(),
                        "status": "Stopped"
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
            print(f"Shadow update response: {response}")
        except Exception as e:
            print(f"Error updating shadow: {e}") 