from abc import ABC, abstractmethod
from typing import Dict, Any

class Handler(ABC):
    @abstractmethod
    def handle(self, charge_point_id: str, message: Any) -> Dict[str, Any]:
        """Handle a specific OCPP message type, should return a response to the charge point"""