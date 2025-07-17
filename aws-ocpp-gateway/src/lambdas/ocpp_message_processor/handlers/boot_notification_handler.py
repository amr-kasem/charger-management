import json
import boto3
from datetime import datetime
from ocpp.v201.enums import RegistrationStatusEnumType
from ocpp_message_processor.handlers.handler import Handler


class BootNotificationHandler(Handler):
    
    def __init__(self, iot_client: boto3.client):
        self.iot = iot_client
    
    def update_charge_point_shadow(self, charge_point_id, message):
        iot_request = {
            "topic": f"$aws/things/{charge_point_id}/shadow/update",
            "qos": 1,
            "payload": json.dumps({"state": {"reported": message}}),
        }
        print(f"{iot_request=}")

        iot_response = self.iot.publish(**iot_request)
        print(f"{iot_response=}")

        return iot_response

    
    def handle(self, charge_point_id, message):
        self.update_charge_point_shadow(charge_point_id, message.payload)

        response = message.create_call_result(
            {
                "currentTime": datetime.utcnow().isoformat(),
                "interval": 10,  # set default interval period in seconds
                "status": RegistrationStatusEnumType.accepted,
            }
        )
        return response