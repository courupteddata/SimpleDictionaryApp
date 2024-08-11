from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str = "OK"


class DefinitionRequest(BaseModel):
    word: str


class DefinitionResponse(BaseModel):
    word: str
    definition: str
