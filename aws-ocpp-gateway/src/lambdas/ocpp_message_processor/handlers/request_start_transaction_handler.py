import json
import boto3
import uuid
from datetime import datetime, timezone
from ocpp_message_processor.handlers.handler import Handler

class RequestStartTransactionHandler(Handler):
    """
    Handler for RequestStartTransaction messages.
    
    This handler processes incoming RequestStartTransaction messages from the central system
    and returns a response to indicate the status of the transaction start request.
    """
    
    def __init__(self, iot_client=None):
        self.iot = iot_client
    
    def handle(self, charge_point_id, message):
        """
        Handle RequestStartTransaction messages by creating an appropriate response.
        
        Args:
            charge_point_id (str): ID of the charge point
            message: The RequestStartTransaction message
            
        Returns:
            The response to send back to the charge point
        """
        print(f"Handling RequestStartTransaction for {charge_point_id}")
        print(f"Message payload: {message.payload}")
        
        # Extract information from the message
        id_token = message.payload.get('idToken')
        evse_id = message.payload.get('evseId')
        remote_start_id = message.payload.get('remoteStartId')
        
        # Check if the connector/evse is available for charging
        # In a real implementation, you would check the charge point's status
        # For now, we'll always accept the request
        
        # Generate a transaction ID
        transaction_id = int(uuid.uuid4().int & 0xFFFFFFFF)
        
        # Update shadow with transaction information if iot client is available
        if self.iot:
            self._update_transaction_info(charge_point_id, transaction_id, evse_id, id_token)
        
        # Create and return the response according to OCPP 2.0.1 spec
        # RequestStartTransactionResponse has status (RequestStartStopStatusEnumType) field
        response = message.create_call_result({
            "status": "Accepted"  # OCPP 2.0.1 options: Accepted or Rejected
        })
        
        return response
    
    def _update_transaction_info(self, charge_point_id, transaction_id, evse_id, id_token):
        """Update the charge point shadow with transaction information"""
        
        transaction_info = {
            "transactionId": transaction_id,
            "evseId": evse_id,
            "idToken": id_token,
            "startTime": datetime.now(timezone.utc).isoformat(),
            "status": "Started"
        }
        
        shadow_update = {
            "state": {
                "reported": {
                    "currentTransaction": transaction_info
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