from typing import Optional

import requests
import time

from parser_app.parsers.config import BROWSER_EXTRA_HEADERS


def download_html(url: str, *, user_agent: str, timeout: int) -> Optional[str]:
    headers = dict(BROWSER_EXTRA_HEADERS)
    headers["User-Agent"] = user_agent

    for attempt in range(2):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            text = response.text
            if text:
                return text
        except requests.RequestException as exc:
            if attempt == 0:
                time.sleep(0.4)
                continue
            break
    return None
