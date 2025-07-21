import logging
import json
import os
from logging.handlers import RotatingFileHandler
from store import Store

dataPath = os.path.join(os.path.dirname(__file__), "data")
sitePath = os.path.join(os.path.dirname(__file__), "site")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
        handlers=[
        RotatingFileHandler(os.path.join(dataPath, "log", "log.txt"), maxBytes=10 * 1024 * 1024, backupCount=10),
        logging.StreamHandler()
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("main")

def main():
    #store.hard_reset_update()
    store.manual_update()

if __name__ == "__main__":
    with open(os.path.join(dataPath, "config.json"), 'r') as config_file:
        config = json.load(config_file)

    store = Store(config["server"], sitePath)
    main()