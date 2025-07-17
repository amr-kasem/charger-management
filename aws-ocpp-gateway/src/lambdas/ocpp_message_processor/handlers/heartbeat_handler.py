from datetime import datetime, timezone

from ocpp_message_processor.handlers.handler import Handler

class HeartbeatHandler(Handler):
    def handle(self, charge_point_id, message):
        response = message.create_call_result(
            {"currentTime": datetime.now(timezone.utc).isoformat()}
        )
        return response

