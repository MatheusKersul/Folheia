import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from scrappers.scraper_amazon import executar_scraping_amazon
from services.service_discovery import ServiceDiscovery


load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


app = FastAPI(
    title="Folheia - Scraper Amazon",
    description="Serviço de scraping da Amazon",
    version="1.0.0",
)


PORT = int(os.getenv("SCRAPER_PORT", "8003"))
SERVICE_ID = os.getenv("CLOUD_MAP_SERVICE_ID")

discovery = ServiceDiscovery()


class ScrapeRequest(BaseModel):
    isbn: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scrape")
def scrape(request: ScrapeRequest):
    logging.info(
        "Recebida solicitação de scraping para ISBN: %s",
        request.isbn
    )

    try:
        dados = executar_scraping_amazon(request.isbn)

        return {
            "isbn": request.isbn,
            "ofertas": dados
        }

    except Exception as error:
        logging.error(
            "Erro ao executar scraping para ISBN %s: %s",
            request.isbn,
            error,
            exc_info=True
        )

        raise HTTPException(
            status_code=500,
            detail="Erro ao executar scraping."
        )


if __name__ == "__main__":
    if not SERVICE_ID:
        raise RuntimeError(
            "CLOUD_MAP_SERVICE_ID não está configurado."
        )

    instance_id = discovery.register_instance(
        service_id=SERVICE_ID,
        port=PORT
    )

    logging.info(
        "Scraper Amazon iniciado na porta %s",
        PORT
    )

    logging.info(
        "Instância registrada no Cloud Map: %s",
        instance_id
    )

    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=PORT
        )

    finally:
        discovery.deregister_instance(
            service_id=SERVICE_ID,
            instance_id=instance_id
        )

        logging.info(
            "Scraper Amazon encerrado e removido do Cloud Map."
        )