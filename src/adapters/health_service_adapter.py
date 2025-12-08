from src.domain.models import HealthResponseModel
from src.ports.input import HealthServicePort


class HealthServiceAdapter(HealthServicePort):
    async def is_service_running(self) -> HealthResponseModel:
        message = {"message": "Service is up and running."}
        return HealthResponseModel(**message)
