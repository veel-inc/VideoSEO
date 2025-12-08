from abc import ABC, abstractmethod

class HealthServicePort(ABC):
    @abstractmethod
    async def is_service_running(self) -> dict:
        pass
