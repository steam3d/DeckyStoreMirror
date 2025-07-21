
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

        self.site_dir = os.path.join(os.path.dirname(__file__), "data")
        self.tmp_dir = os.path.join(os.path.dirname(__file__), "tmp")

        self.server = r"https://justtype.ru/"
        self.decky_stable = r"https://plugins.deckbrew.xyz/plugins"
        self.decky_testing = r"https://testing.deckbrew.xyz/plugins"
        self.decky_plugins= r"https://cdn.tzatzikiweeb.moe/file/steam-deck-homebrew/versions/{}.zip"

    
    def _update_file(self, url:str, new_url:str, dir):
        name, ext = os.path.splitext(url.split("/")[-1])
                
        content_dir = os.path.join(dir, "content")
        os.makedirs(content_dir, exist_ok=True)

        if ext == ".zip" and os.path.exists(os.path.join(content_dir, f"{name}{ext}")):
            return f"{new_url}/content/{name}{ext}"
        
        data = requests.get(url).content
        hash = hashlib.sha256(data).hexdigest()
        file_path = os.path.join(content_dir, f"{hash}{ext}")

        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(data)
            logger.info(f"File saved: {file_path}")
        else:
            logger.info(f"File exist: {file_path}")

        return f"{new_url}/content/{hash}{ext}"        
    
    def _update_image(self, url:str, new_url:str, dir):
        data = requests.get(url).content        

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
            data = requests.get(url.format(hash)).content

            with open(plugin_path, "wb") as f:
                f.write(data)
            logger.info(f"Plugin saved: {plugin_path}")
        else:
            logger.info(f"Plugin exist: {plugin_path}")

        return f"{new_url}/plugins/{hash}{ext}"

    def _update_store(self, url, base_dir, tag):
        logger.info(f"Start update {tag}")

        dir = os.path.join(base_dir, tag)
        os.makedirs(dir, exist_ok=True)        
        new_url = f"{self.server}/{tag}"
        data = requests.get(url).json()        

        for plugin in data:                
            plugin["image_url"] = self._update_file(plugin["image_url"], new_url, dir)
            for version in plugin["versions"]:
                version["artifact"] = self._update_file(self.decky_plugins.format(version["hash"]), new_url, dir)
    
        path = os.path.join(dir, "plugins.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Json saved: {path}")
        
        logger.info(f"End update {tag}")

    def _update(self, dir):        
        if (not self.updating):
            self.updating = True
            self._update_store(self.decky_stable, dir, "stable")   
            self._update_store(self.decky_testing, dir, "testing")
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
        

