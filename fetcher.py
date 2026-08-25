import ssl
import time
import httpx
import urllib3
from bs4 import BeautifulSoup
import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Aufgebohrte Browser-Header zur Reduzierung von 403-Sperren
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

RETRYABLE = (
    httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout,
    httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError,
)


def make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.minimum_version = ssl.TLSVersion.TLSv1
    except (AttributeError, ValueError):
        pass
    for ciphers in ("DEFAULT@SECLEVEL=1", "ALL:@SECLEVEL=1"):
        try:
            ctx.set_ciphers(ciphers)
            break
        except ssl.SSLError:
            continue
    return ctx


def make_http_client() -> httpx.Client:
    return httpx.Client(
        headers=BROWSER_HEADERS,
        follow_redirects=True,
        verify=make_ssl_context(),
        timeout=httpx.Timeout(connect=15.0, read=40.0, write=15.0, pool=15.0),
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
    )


def html_to_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    
    # Extraktion von strukturierten JSON-LD Kalenderdaten vor dem Zerlegen des DOMs
    json_ld_texts = []
    for script in soup.find_all("script", type="application/ld+json"):
        if script.string:
            json_ld_texts.append(script.string)

    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "form", "noscript"]):
        tag.decompose()
        
    main = soup.find("main") or soup.find("article") or soup
    extracted_text = main.get_text(separator=" ", strip=True)
    
    if json_ld_texts:
        extracted_text += " " + " ".join(json_ld_texts)
        
    return extracted_text


def classify_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}"
    if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.PoolTimeout)):
        return "Timeout"
    if isinstance(exc, httpx.ConnectError):
        text = str(exc)
        if "Name or service not known" in text or "nodename nor servname" in text:
            return "DNS unbekannt"
        if "SSL" in text or "HANDSHAKE" in text.upper():
            return "TLS-Handshake"
        return "Verbindung fehlgeschlagen"
    if isinstance(exc, httpx.RemoteProtocolError):
        return "Protokollfehler"
    return type(exc).__name__


def fetch_page_text(client_http: httpx.Client, url: str) -> str:
    last_exc: Exception | None = None

    for attempt in range(config.FETCH_ATTEMPTS):
        try:
            response = client_http.get(url)
            response.raise_for_status()
            return html_to_text(response.text)
        except httpx.HTTPStatusError as exc:
            raise exc
        except RETRYABLE as exc:
            last_exc = exc
            if attempt < config.FETCH_ATTEMPTS - 1:
                wait = 3 * (attempt + 1)
                print(f"  {classify_error(exc)}, Versuch "
                      f"{attempt + 2}/{config.FETCH_ATTEMPTS} in {wait}s: {url}")
                time.sleep(wait)
        except Exception as exc:
            last_exc = exc
            break

    raise last_exc if last_exc else RuntimeError("Abruf ohne Ergebnis")


def is_worth_sending(url: str, text: str) -> bool:
    if len(text) < config.MIN_TEXT_LENGTH:
        print(f"  uebersprungen (nur {len(text)} Zeichen, evtl. JS-gerendert): {url}")
        return False
    if not config.DATE_PATTERN.search(text):
        print(f"  uebersprungen (kein Datumsmuster gefunden): {url}")
        return False
    return True


def cap_hits(text: str, max_hits: int) -> tuple[str, int]:
    found = list(config.DATE_PATTERN.finditer(text))
    if len(found) <= max_hits:
        return text, len(found)
    return text[:found[max_hits].start()], max_hits


def condense_text(text: str, limit: int) -> tuple[str, int]:
    if len(text) <= limit:
        return cap_hits(text, config.MAX_HITS_PER_PAGE)

    spans: list[list[int]] = []
    for match in config.DATE_PATTERN.finditer(text):
        window_start = max(0, match.start() - config.SNIPPET_BEFORE)
        window_stop = min(len(text), match.end() + config.SNIPPET_AFTER)
        if spans and window_start <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], window_stop)
        else:
            spans.append([window_start, window_stop])

    if not spans:
        return text[:limit], 0

    separator = " [...] "
    parts: list[str] = []
    used = 0
    hits = 0
    for window_start, window_stop in spans:
        chunk = text[window_start:window_stop]
        if used + len(chunk) + len(separator) > limit:
            break
        parts.append(chunk)
        used += len(chunk) + len(separator)
        hits += len(config.DATE_PATTERN.findall(chunk))
        if hits >= config.MAX_HITS_PER_PAGE:
            break

    if not parts:
        result = text[spans[0][0]:spans[0][0] + limit]
    else:
        result = separator.join(parts)

    return cap_hits(result, config.MAX_HITS_PER_PAGE)