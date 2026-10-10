import urllib.error
import urllib.request

from feed import SourceError

USER_AGENT = "infra-assumption-feed/0.1 (+https://github.com/ITJHIT/infra-assumption-feed)"


def get(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SourceError(f"request failed: {url.split('?')[0]}: {exc}") from exc
