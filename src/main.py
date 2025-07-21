import logging
import json
import requests
import hashlib
import os
from logging.handlers import RotatingFileHandler

basePath = os.path.join(os.path.dirname(__file__), "data")

server_images_url=r"https://justtype.ru/images/"
server_plugins_url=r"https://justtype.ru/plugins/"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
        handlers=[
        RotatingFileHandler(os.path.join(basePath, "log", "log.txt"), maxBytes=10 * 1024 * 1024, backupCount=10),
        logging.StreamHandler()
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def update_image(url, veiry=False):        
    name, ext = os.path.splitext(url.split("/")[-1])

    response = requests.get(url)
    data = response.content
    sha256_hash = hashlib.sha256(data).hexdigest()        
    
    path = os.path.join(basePath, "images", sha256_hash+ext)

    with open(path, "wb") as f:
        f.write(data)
    
    logger.info("Image saved: {}".format(path))

    if (veiry):
        with open(path, "rb") as f:
            saved_data = f.read()
            sha256_after = hashlib.sha256(saved_data).hexdigest()

        if sha256_hash != sha256_after:
            logger.error("Hash does not match: {} != {} file: {}".format(sha256_hash, sha256_after, sha256_hash+ext))            
    
    return server_images_url + sha256_hash+ext


def find_all_image_urls(obj, results=None):
    if results is None:
        results = []

    for key in obj:                
        key["image_url"] = update_image(key["image_url"])      

def main():
    with open(os.path.join(basePath, "plugins_08072025.json"), 'r') as config_file:
        old = json.load(config_file)

    with open(os.path.join(basePath, "plugins.json"), 'r') as config_file:
        new = json.load(config_file)

    find_all_image_urls(old)

if __name__ == "__main__":
    main()