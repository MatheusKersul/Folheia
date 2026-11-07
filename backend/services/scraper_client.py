#Responsável por se comunicar com o serviço scraper, que realiza o scraping de ofertas.
import logging
import requests

from services.service_discovery import ServiceDiscovery


logger = logging.getLogger(__name__)


class ScraperClient:
    def __init__(self):
        self.discovery = ServiceDiscovery()

    def executar_scraping(self, isbn: str):
        instancias = self.discovery.discover_instances(
            "scraper-amazon"
        )

        if not instancias:
            raise RuntimeError(
                "Nenhuma instância do scraper-amazon foi encontrada "
                "no Cloud Map."
            )

        ultimo_erro = None

        for instancia in instancias:
            ip = instancia.get("Attributes", {}).get(
                "AWS_INSTANCE_IPV4"
            )
            porta = instancia.get("Attributes", {}).get(
                "AWS_INSTANCE_PORT"
            )

            if not ip or not porta:
                logger.warning(
                    "Instância %s não possui IP ou porta válidos. "
                    "Ignorando.",
                    instancia.get("InstanceId")
                )
                continue

            url = f"http://{ip}:{porta}/scrape"

            logger.info(
                "Tentando scraper-amazon em %s para ISBN %s",
                url,
                isbn
            )

            try:
                response = requests.post(
                    url,
                    json={"isbn": isbn},
                    timeout=120
                )

                response.raise_for_status()

                resultado = response.json()

                logger.info(
                    "Scraper-amazon retornou %d ofertas para ISBN %s",
                    len(resultado.get("ofertas", [])),
                    isbn
                )

                return resultado.get("ofertas", [])

            except requests.RequestException as error:
                ultimo_erro = error

                logger.warning(
                    "Instância %s:%s indisponível: %s",
                    ip,
                    porta,
                    error
                )

        raise RuntimeError(
            "Nenhuma instância disponível do scraper-amazon "
            f"respondeu. Último erro: {ultimo_erro}"
        )