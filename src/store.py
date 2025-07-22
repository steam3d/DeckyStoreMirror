
import logging
import requests
import json
import hashlib
import os
import threading
import time
import shutil
import tempfile
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("main")

class Store:
    def __init__(self, server, site_dir):
        #self.tmp_dir = os.path.join(os.path.dirname(__file__), "tmp") #For Windows testing
        self.stop_event = threading.Event()
        self.last_update = datetime.now(timezone.utc)
        self.next_update = datetime.now(timezone.utc)
        self.thread = None
        self.lock = threading.Lock()

        self.site_dir = site_dir
        self.server = server
        self.decky_stable = r"https://plugins.deckbrew.xyz/plugins"
        self.decky_testing = r"https://testing.deckbrew.xyz/plugins"
        self.decky_plugins= r"https://cdn.tzatzikiweeb.moe/file/steam-deck-homebrew/versions/{}.zip"


    def _update_file(self, url:str, new_url:str, dir):
        name, ext = os.path.splitext(url.split("/")[-1])

        content_dir = os.path.join(dir, "content")
        os.makedirs(content_dir, exist_ok=True)

        tmp_path = os.path.join(content_dir, f"{name}{ext}")
        if ext == ".zip" and os.path.exists(tmp_path):
            logger.info(f"File exist: {tmp_path}")
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
            self._update_store(self.decky_stable, dir, "stable")
            self._update_store(self.decky_testing, dir, "testing")
            self.last_update = datetime.now(timezone.utc)
            self.next_update = datetime.now(timezone.utc) + timedelta(hours=24)

    def _background_worker(self):
        self.hard_reset_update()

        while not self.stop_event.is_set():
            now = datetime.now(timezone.utc)

            if now >= self.next_update:
                logger.info("Starting scheduled update")
                self.manual_update()
                logger.info(f"Next update scheduled at {self.next_update}")

            if self.stop_event.wait(timeout=1):
                logger.info("Thread stopped")
                return

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
        if not self.lock.acquire(blocking=False):
            logger.warning("Update is already in progress — skipping manual_update")
            return
        try:
            self._update(self.site_dir)
        finally:
            self.lock.release()

    def hard_reset_update(self):
        if not self.lock.acquire(blocking=False):
            logger.warning("Update is already in progress — skipping hard_reset_update")
            return
        try:
            #with tempfile.TemporaryDirectory(dir=self.tmp_dir) as tmpdir:
            with tempfile.TemporaryDirectory(dir='/tmp') as tmpdir:
                self._update(tmpdir)
                self._delete_files(self.site_dir)
                self._copy_files(tmpdir, self.site_dir)
        finally:
            self.lock.release()

    def _delete_files(self, dir):
        if not os.path.exists(dir):
            return

        for filename in os.listdir(dir):
            file_path = os.path.join(dir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

    def _copy_files(self, src, dst):
        for item in os.listdir(src):
            src_path = os.path.join(src, item)
            dst_path = os.path.join(dst, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

