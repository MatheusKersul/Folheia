import logging

from services.service_discovery import ServiceDiscovery


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


discovery = ServiceDiscovery()


print("Testando acesso ao Cloud Map...")


instancias = discovery.discover_instances(
    "scraper-amazon"
)


print(f"\nInstâncias encontradas: {len(instancias)}")


for instancia in instancias:
    print("\nInstância:")

    print(
        f"  ID: {instancia.get('InstanceId')}"
    )

    print(
        f"  IP: {instancia.get('Attributes', {}).get('AWS_INSTANCE_IPV4')}"
    )

    print(
        f"  Porta: {instancia.get('Attributes', {}).get('AWS_INSTANCE_PORT')}"
    )

    print(
        f"  Status: {instancia.get('HealthStatus')}"
    )