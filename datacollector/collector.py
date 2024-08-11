import os

import httpx
from urllib.parse import urljoin

import psycopg2
from fastapi import FastAPI, status
import uvicorn

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from common.basemodels import HealthCheck, DefinitionResponse, DefinitionRequest

broker = RabbitBroker(url=os.environ["AMQP_URL"])
rabbit = FastStream(broker)
postgres_connection = psycopg2.connect(os.environ["DATABASE_URL"])
cursor = postgres_connection.cursor()

app = FastAPI()


@broker.subscriber("definition_request")
async def handle(definition_request: DefinitionRequest):
    word = definition_request.word.lower().strip()
    definition = get_definition(word)

    insert_sql = '''
        INSERT INTO definition (word, definition)
        VALUES (%s, %s)
        ON CONFLICT (word) DO UPDATE SET
        (definition) = (EXCLUDED.definition);
    '''

    cursor.execute(insert_sql, (word, definition))

    return None



def get_definition(word: str) -> DefinitionResponse | None:
    word = word.lstrip("/")
    # url = urljoin("https://en.wiktionary.org/api/rest_v1/page/definition/", word)
    url = urljoin("https://api.dictionaryapi.dev/api/v2/entries/en/", word)
    response = httpx.get(url, headers={
        # "accept": "application/json; charset=utf-8;
        # profile=\"https://www.mediawiki.org/wiki/Specs/definition/0.8.0\"",
        "Api-User-Agent": "Simple Dictionary (See https://github.com/courupteddata for contact)"
    })

    match response.status_code:
        case 200:
            return DefinitionResponse(word=word,
                                      definition=response.json()[0]["meanings"][0]["definitions"][0]["definition"])
        case _:
            return None


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


def _main():
    definition = get_definition("word")
    cursor.execute("CREATE TABLE IF NOT EXISTS definition (word varchar(45) NOT NULL, "
                   "definition varchar(1000), PRIMARY KEY (word))").commit()
    print(definition)
    uvicorn.run("main:app", host="0.0.0.0")


if __name__ == "__main__":
    _main()
