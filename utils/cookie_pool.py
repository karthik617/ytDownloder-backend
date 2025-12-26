import os
import random
import time
import threading

COOKIE_DIR = "cookies"
COOLDOWN_SECONDS = 15 * 60   # 15 minutes
MAX_FAILURES = 2

class CookiePool:
    def __init__(self):
        self.lock = threading.Lock()
        self.cookies = {}
        self._load()

    def _load(self):
        for f in os.listdir(COOKIE_DIR):
            if f.endswith(".txt"):
                path = os.path.join(COOKIE_DIR, f)
                self.cookies[path] = {
                    "failures": 0,
                    "cooldown_until": 0
                }

    def get_cookie(self):
        now = time.time()
        with self.lock:
            available = [
                c for c, meta in self.cookies.items()
                if meta["cooldown_until"] <= now
            ]

            if not available:
                raise RuntimeError("No valid cookies available")

            return random.choice(available)

    def mark_failure(self, cookie):
        with self.lock:
            if cookie not in self.cookies:
                return

            self.cookies[cookie]["failures"] += 1

            if self.cookies[cookie]["failures"] >= MAX_FAILURES:
                self.cookies[cookie]["cooldown_until"] = time.time() + COOLDOWN_SECONDS
                self.cookies[cookie]["failures"] = 0

    def mark_success(self, cookie):
        with self.lock:
            if cookie in self.cookies:
                self.cookies[cookie]["failures"] = 0
