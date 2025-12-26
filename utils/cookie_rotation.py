import yt_dlp
from utils.cookie_pool import CookiePool

CAPTCHA_ERRORS = [
    "Sign in to confirm you're not a bot",
    "This video is unavailable",
    "HTTP Error 429",
    "Too many requests",
    "captcha",
    "verify"
]

def is_bot_error(err: str) -> bool:
    err = err.lower()
    return any(x.lower() in err for x in CAPTCHA_ERRORS)


cookie_pool = CookiePool()

def download_with_cookie_rotation(url: str, ydl_opts_base: dict, download: bool):
    last_error = None

    for _ in range(len(cookie_pool.cookies)):
        cookie = cookie_pool.get_cookie()
        print("Using cookie:", cookie)
        ydl_opts = {
            **ydl_opts_base,
            "cookiefile": cookie,
            "quiet": True,
            "no_warnings": True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=download)

            cookie_pool.mark_success(cookie)
            return info

        except Exception as e:
            err = str(e)
            last_error = err

            if is_bot_error(err):
                cookie_pool.mark_failure(cookie)
                continue
            else:
                raise e

    raise RuntimeError(f"All cookies blocked: {last_error}")
