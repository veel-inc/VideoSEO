from pydantic import BaseModel, Field


class HealthResponseModel(BaseModel):
    message: str = Field(
        ..., description="Additional information about the health status."
    )
