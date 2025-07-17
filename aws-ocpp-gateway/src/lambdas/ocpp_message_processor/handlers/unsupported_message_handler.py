from ocpp_message_processor.handlers.handler import Handler
from ocpp.v201 import call_result
import logging

logger = logging.getLogger(__name__)

class UnsupportedMessageHandler(Handler):
    def handle(self, charge_point_id, message):
        logger.info(f"Received unsupported message: {message}")
        return message

