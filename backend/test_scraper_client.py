from dotenv import load_dotenv
from services.scraper_client import ScraperClient

load_dotenv()

client = ScraperClient()

ofertas = client.executar_scraping("9788594540188")

print(f"Ofertas encontradas: {len(ofertas)}")

for oferta in ofertas:
    print(oferta)