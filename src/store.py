
import logging
import requests
import json
import hashlib
import os
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger("main")

class Store:
    def __init__(self):
        self.updating = False
        self.stop_event = threading.Event()
        self.last_update = datetime.now(timezone.utc)
        self.thread = None

        self.server_images_url=r"https://justtype.ru/images/"
        self.server_plugins_url=r"https://justtype.ru/plugins/"

        self.site_dir = os.path.join(os.path.dirname(__file__), "data")
        self.tmp_dir = os.path.join(os.path.dirname(__file__), "data")

    def _update_image(self, url:str, new_url:str, dir):
        response = requests.get(url)
        data = response.content

        name, ext = os.path.splitext(url.split("/")[-1])
        hash = hashlib.sha256(data).hexdigest()

        image_dir = os.path.join(dir, "images")
        os.makedirs(image_dir, exist_ok=True)

        image_path = os.path.join(image_dir, f"{hash}{ext}")

        if not os.path.exists(image_path):
            with open(image_path, "wb") as f:
                f.write(data)
            logger.info(f"Image saved: {image_path}")
        else:
            logger.info(f"Image exist: {image_path}")

        return f"{new_url}/images/{hash}{ext}"

    def _update_plugin(self, url:str, new_url:str, hash, dir):
        ext = ".zip"
        plugins_dir = os.path.join(dir, "plugins")
        os.makedirs(plugins_dir, exist_ok=True)

        plugin_path = os.path.join(plugins_dir, f"{hash}{ext}")

        if not os.path.exists(plugin_path):
            url = url.format(hash)
            response = requests.get(url)
            data = response.content
            with open(plugin_path, "wb") as f:
                f.write(data)
            logger.info(f"Plugin saved: {plugin_path}")
        else:
            logger.info(f"Plugin exist: {plugin_path}")

        return f"{new_url}/pluigns/{hash}{ext}"
    
    def _update_stable_store(self, dir):
        stable_dir = os.path.join(dir, "stable")
        os.makedirs(stable_dir, exist_ok=True)
        plugins_url= r"https://cdn.tzatzikiweeb.moe/file/steam-deck-homebrew/versions/{}.zip"
        url = r"https://plugins.deckbrew.xyz/plugins"
        new_url = r"https://justtype.ru/stable/"
        response = requests.get(url)
        data = response.json()

        for plugin in data:                
            plugin["image_url"] = self._update_image(plugin["image_url"], new_url, stable_dir)
            for version in plugin["versions"]:
                version["hash"] = self._update_plugin(plugins_url, new_url, version["hash"], stable_dir)
    
        path = os.path.join(stable_dir, "plugins.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Json saved: {path}")

    def _update_testing_store(self, dir):
        stable_dir = os.path.join(dir, "testing")
        os.makedirs(stable_dir, exist_ok=True)
        plugins_url= r"https://cdn.tzatzikiweeb.moe/file/steam-deck-homebrew/versions/{}.zip"
        url = r"https://testing.deckbrew.xyz/plugins"
        new_url = r"https://justtype.ru/testing/"
        response = requests.get(url)
        data = response.json()

        for plugin in data:                
            plugin["image_url"] = self._update_image(plugin["image_url"], new_url, stable_dir)
            for version in plugin["versions"]:
                version["hash"] = self._update_plugin(plugins_url, new_url, version["hash"], stable_dir)
    
        path = os.path.join(stable_dir, "plugins.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Json saved: {path}")

    def _update(self, dir):        
        if (not self.updating):
            self.updating = True
            #self._update_stable_store(dir)
            self._update_testing_store(dir)
            self.last_update = datetime.now(timezone.utc)
            self.updating = False
        else:
            logger.error("Update is already in process.")

    def _background_worker(self):
        while not self.stop_event.is_set():                                    
            #for _ in range(24 * 60 * 60):
            for _ in range(60):
                if self.stop_event.is_set():
                    logger.error("Thread stopped")
                    return
                time.sleep(1)
            
            self._update(self.site_dir)

    def start(self):
        if self.thread and self.thread.is_alive():
            logger.warning("Thread already running")
            return

        logger.info("Start thread")
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._background_worker, daemon=True)
        self.thread.start()

    def stop(self):
        logger.info("Stop thread")
        self.stop_event.set()
        if self.thread:
            self.thread.join()
            logger.info("Thread stopped")

    def manual_update(self):
        self._update(self.site_dir)
        

