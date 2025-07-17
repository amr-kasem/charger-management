
from ocpp_message_processor.handlers.handler import Handler


class StatusNotificationHandler(Handler):
    def handle(self, charge_point_id, message):
        response = message.create_call_result({})
        return response
