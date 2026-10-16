import os
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    logging.info("Scraper worker iniciado. Aguardando tarefas...")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logging.info("Worker finalizado.")

if __name__ == "__main__":
    main()
