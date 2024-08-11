import os

import psycopg2
from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse
import uvicorn

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from common.basemodels import HealthCheck, DefinitionResponse, DefinitionRequest

broker = RabbitBroker(url=os.environ["AMQP_URL"])
rabbit = FastStream(broker)
postgres_connection = psycopg2.connect(os.environ["DATABASE_URL"])

app = FastAPI()


@app.get(
    "/health",
    tags=["healthcheck"],
    summary="Perform a Health Check",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=HealthCheck,
)
def get_health() -> HealthCheck:
    return HealthCheck(status="OK")


@app.get(
    "/definition/",
    summary="Perform a definition look up",
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
    response_model=DefinitionResponse,
)
async def get_word(word: str) -> DefinitionResponse:
    word = word.lower().strip()
    found_definition = None
    with postgres_connection:
        with postgres_connection.cursor() as cursor:
            cursor.execute("select definition from definition where word=%s", (word,))
            found_definition = cursor.fetchone()
            print(found_definition)

    if not found_definition:
        await broker.publish(DefinitionRequest(word=word), "definition_request")
        return DefinitionResponse(word=word, definition="Please wait, definition still needs to be collected")
    return DefinitionResponse(word=word, definition=found_definition)


@app.get(
    "/",
    summary="get ui",
    response_description="Return UI",
    status_code=status.HTTP_200_OK,
    response_class=HTMLResponse
)
async def get_ui():
    return """
    <form action="/definition/" method="GET">
         <input name="word">
         <input type="submit" value="Submit!">
     </form>
    """


def _main():
    with postgres_connection:
        with postgres_connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS definition (word varchar(45) NOT NULL, "
                           "definition varchar(1000), PRIMARY KEY (word))")
    uvicorn.run("analyzer:app", host="0.0.0.0")


if __name__ == "__main__":
    _main()
