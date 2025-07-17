import json
import boto3
from datetime import datetime
from ocpp_message_processor.handlers.handler import Handler

class TransactionEventHandler(Handler):
    """
    Handler for TransactionEvent messages.
    
    This handler processes transaction events from charge points,
    which include details about transaction state changes.
    """
    
    def __init__(self, iot_client=None):
        self.iot = iot_client
    
    def handle(self, charge_point_id, message):
        """
        Handle TransactionEvent messages by storing transaction data
        and returning an acknowledgment.
        
        Args:
            charge_point_id (str): ID of the charge point
            message: The TransactionEvent message
            
        Returns:
            The response to send back to the charge point
        """
        print(f"Handling TransactionEvent for {charge_point_id}")
        print(f"Message payload: {message.payload}")
        
        # Store transaction information in the charge point's shadow
        if self.iot:
            self.update_transaction_shadow(charge_point_id, message.payload)
        
        # In OCPP 2.0.1, TransactionEventResponse has no required fields
        # Just return an empty response object
        response = message.create_call_result({})
        return response
    
    def update_transaction_shadow(self, charge_point_id, transaction_data):
        """
        Update the charge point's shadow with transaction information.
        
        Args:
            charge_point_id (str): ID of the charge point
            transaction_data (dict): Transaction event data
        """
        # Extract relevant transaction information
        event_type = transaction_data.get('eventType')  # Started, Updated, Ended
        timestamp = transaction_data.get('timestamp')
        transaction_info = transaction_data.get('transactionInfo', {})
        transaction_id = transaction_info.get('transactionId')
        
        # Create shadow update document
        shadow_update = {
            "state": {
                "reported": {
                    "lastTransactionEvent": {
                        "eventType": event_type,
                        "timestamp": timestamp,
                        "transactionId": transaction_id,
                        "receivedAt": datetime.utcnow().isoformat()
                    }
                }
            }
        }
        
        # If this is a transaction start event, store more info
        if event_type == "Started":
            shadow_update["state"]["reported"]["activeTransaction"] = {
                "transactionId": transaction_id,
                "startTime": timestamp,
                "evseId": transaction_data.get('evse', {}).get('id'),
                "idToken": transaction_data.get('idToken')
            }
        
        # If this is a transaction end event, update the status
        elif event_type == "Ended":
            shadow_update["state"]["reported"]["activeTransaction"] = None
            shadow_update["state"]["reported"]["lastCompletedTransaction"] = {
                "transactionId": transaction_id,
                "startTime": transaction_info.get('startTime'),
                "stopTime": timestamp,
                "stoppedReason": transaction_data.get('stoppedReason')
            }
        
        # Add the full transaction data for reference
        shadow_update["state"]["reported"]["lastTransactionEvent"]["data"] = transaction_data
        
        try:
            topic = f"$aws/things/{charge_point_id}/shadow/update"
            response = self.iot.publish(
                topic=topic,
                qos=1,
                payload=json.dumps(shadow_update)
            )
            print(f"Shadow update response: {response}")
            return response
        except Exception as e:
            print(f"Error updating shadow: {e}")
            return None 