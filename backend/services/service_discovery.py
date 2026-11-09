import logging
import os
import socket

import boto3
from botocore.exceptions import BotoCoreError, ClientError


logger = logging.getLogger(__name__)


class ServiceDiscovery:
    def __init__(self):
        self.region = os.getenv(
            "AWS_REGION",
            "us-east-2"
        )

        self.namespace_name = os.getenv(
            "CLOUD_MAP_NAMESPACE",
            "Folheia"
        )

        self.client = boto3.client(
            "servicediscovery",
            region_name=self.region
        )

    def _get_local_ip(self):
        connection = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        try:
            connection.connect(("8.8.8.8", 80))
            return connection.getsockname()[0]
        finally:
            connection.close()

    def register_instance(
        self,
        service_id: str,
        port: int,
        instance_id: str | None = None
    ):
        """
        Registra uma instância de um serviço no AWS Cloud Map.
        """

        ip = self._get_local_ip()

        if instance_id is None:
            instance_id = f"service-{socket.gethostname()}"

        logger.info("Registrando serviço no Cloud Map...")
        logger.info("Service ID: %s", service_id)
        logger.info("Instance ID: %s", instance_id)
        logger.info("IP: %s", ip)
        logger.info("Porta: %s", port)

        try:
            response = self.client.register_instance(
                ServiceId=service_id,
                InstanceId=instance_id,
                Attributes={
                    "AWS_INSTANCE_IPV4": ip,
                    "AWS_INSTANCE_PORT": str(port),
                }
            )

            logger.info(
                "Serviço registrado com sucesso. OperationId: %s",
                response["OperationId"]
            )

            return instance_id

        except (BotoCoreError, ClientError) as error:
            logger.error(
                "Erro ao registrar serviço no Cloud Map: %s",
                error
            )
            raise

    def discover_instances(self, service_name: str):
        """
        Descobre as instâncias de um serviço pelo nome
        dentro do namespace configurado.
        """

        logger.info(
            "Procurando instâncias do serviço '%s'...",
            service_name
        )

        try:
            response = self.client.discover_instances(
                NamespaceName=self.namespace_name,
                ServiceName=service_name,
                HealthStatus="HEALTHY_OR_ELSE_ALL"
            )

            instances = response.get("Instances", [])

            logger.info(
                "Encontradas %d instância(s) do serviço '%s'.",
                len(instances),
                service_name
            )

            return instances

        except (BotoCoreError, ClientError) as error:
            logger.error(
                "Erro ao descobrir serviço '%s': %s",
                service_name,
                error
            )
            return []

    def deregister_instance(
        self,
        service_id: str,
        instance_id: str
    ):
        """
        Remove uma instância de um serviço do Cloud Map.
        """

        logger.info(
            "Removendo instância '%s' do serviço '%s'...",
            instance_id,
            service_id
        )

        try:
            response = self.client.deregister_instance(
                ServiceId=service_id,
                InstanceId=instance_id
            )

            logger.info(
                "Instância removida do Cloud Map. OperationId: %s",
                response["OperationId"]
            )

        except (BotoCoreError, ClientError) as error:
            logger.error(
                "Erro ao remover instância do Cloud Map: %s",
                error
            )
            raise