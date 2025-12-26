import os
import random
import time
import threading
import base64

COOKIE_DIR = os.environ.get("COOKIE_DIR", "cookies")
COOLDOWN_SECONDS = 15 * 60   # 15 minutes
MAX_FAILURES = 2

class CookiePool:
    def __init__(self):
        self.lock = threading.Lock()
        self.cookies = {}
        self._load()
        self._validate_cookies()  # ADD THIS

    def _load(self):
        try:
            os.makedirs(COOKIE_DIR, mode=0o755, exist_ok=True)
            
            # Test write permission
            test_file = os.path.join(COOKIE_DIR, ".test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            print(f"✓ Cookie directory is writable: {COOKIE_DIR}")
            
        except Exception as e:
            print(f"✗ Cannot write to cookie directory: {e}")
            raise

        for i in range(1, 3):
            env_key = f"YT_COOKIE_{i}"
            if env_key in os.environ:
                try:
                    decoded = base64.b64decode(os.environ[env_key])
                    print(f"{env_key}: {len(decoded)} bytes")
                    
                    # Check if it starts with cookie header
                    text = decoded.decode('utf-8', errors='ignore')
                    if text.startswith('# Netscape HTTP Cookie File'):
                        print(f"  ✓ Valid cookie format")
                    else:
                        print(f"  ✗ Invalid format, starts with: {text[:50]}")
                except Exception as e:
                    print(f"{env_key}: ERROR - {e}")
                path = f"{COOKIE_DIR}/yt_{i}.txt"
                with open(path, "wb") as f:
                    f.write(base64.b64decode(os.environ[env_key]))

        for f in os.listdir(COOKIE_DIR):
            if f.endswith(".txt"):
                path = os.path.join(COOKIE_DIR, f)
                self.cookies[path] = {
                    "failures": 0,
                    "cooldown_until": 0
                }

    def _validate_cookies(self):
        """Validate that all cookies are readable and valid"""
        print("\n=== Validating Cookies ===")
        
        for cookie_path in list(self.cookies.keys()):
            # Check file exists
            if not os.path.exists(cookie_path):
                print(f"✗ Cookie does not exist: {cookie_path}")
                del self.cookies[cookie_path]
                continue
            
            # Check file size
            size = os.path.getsize(cookie_path)
            if size == 0:
                print(f"✗ Cookie is empty (0 bytes): {cookie_path}")
                del self.cookies[cookie_path]
                continue
            
            # Check readable
            if not os.access(cookie_path, os.R_OK):
                print(f"✗ Cookie not readable: {cookie_path}")
                print(f"  Permissions: {oct(os.stat(cookie_path).st_mode)[-3:]}")
                del self.cookies[cookie_path]
                continue
            
            # Check content format (basic validation)
            try:
                with open(cookie_path, 'r') as f:
                    first_line = f.readline()
                    if not first_line.startswith('# Netscape HTTP Cookie File'):
                        print(f"⚠ Cookie may not be in Netscape format: {cookie_path}")
                    else:
                        print(f"✓ Cookie valid: {cookie_path} ({size} bytes)")
            except Exception as e:
                print(f"✗ Error reading cookie: {cookie_path} - {e}")
                del self.cookies[cookie_path]
        
        if not self.cookies:
            raise RuntimeError("No valid cookies available after validation!")
        
        print(f"Valid cookies: {len(self.cookies)}\n")

    def get_cookie(self):
        now = time.time()
        with self.lock:
            available = [
                c for c, meta in self.cookies.items()
                if meta["cooldown_until"] <= now
            ]
            print(f"Available cookies: {len(available)} / {len(self.cookies)}")
            
            if not available:
                # Show cooldown status
                for cookie, meta in self.cookies.items():
                    remaining = meta["cooldown_until"] - now
                    if remaining > 0:
                        print(f"  {os.path.basename(cookie)}: cooldown for {remaining:.0f}s more")
                raise RuntimeError("No valid cookies available")

            selected = random.choice(available)
            print(f"Selected cookie: {os.path.basename(selected)}")
            return selected

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
