from typing import Optional

import requests


def download_html(url: str, *, user_agent: str, timeout: int) -> Optional[str]:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": user_agent},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None
