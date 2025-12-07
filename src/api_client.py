"""
Thin wrapper around the Fiindo API.
Responsibilities:
- Handle authentication via FIRST_NAME / LAST_NAME (.env)
- Provide convenience methods for all required endpoints
- Centralize error handling and simple retry logic
"""
import os
import time
import logging
from typing import Any, Dict, Optional, Set
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Base URL can be overridden for tests if needed
BASE_URL = os.getenv("FIINDO_API_BASE_URL", "https://api.test.fiindo.com/api/v1")

# NOTE:
# The original challenge description uses the header name "Auhtorization"
# (with this exact spelling), but the actual Fiindo test API expects the
# standard "Authorization" header. This client therefore uses the correct
# "Authorization" header so that it can talk to the real API.
AUTH_HEADER_NAME = "Authorization"

FIRST_NAME = os.getenv("FIRST_NAME")
LAST_NAME = os.getenv("LAST_NAME")

if not FIRST_NAME or not LAST_NAME:
    raise RuntimeError("Missing FIRST_NAME or LAST_NAME in environment / .env file.")

HEADERS = {
    AUTH_HEADER_NAME: f"Bearer {FIRST_NAME}.{LAST_NAME}",
}

# Retry / timeout configuration from environment

# How many times to retry for retry-able HTTP status codes
MAX_RETRIES_DEFAULT = int(os.getenv("FIINDO_MAX_RETRIES", "3"))

# How long to wait (in seconds) between retries
BACKOFF_SECONDS_DEFAULT = float(os.getenv("FIINDO_RETRY_BACKOFF", "30"))

# Per-request timeout in seconds
API_TIMEOUT_DEFAULT = float(os.getenv("FIINDO_API_TIMEOUT", "90"))

# Comma-separated list of HTTP status codes that should be retried
_retry_codes_raw = os.getenv("FIINDO_RETRY_STATUS_CODES", "429,500")
RETRY_STATUS_CODES_DEFAULT: Set[int] = {
    int(code.strip())
    for code in _retry_codes_raw.split(",")
    if code.strip()
}


# Speedboost configuration

# Optional: enable / disable speedboost via environment
# e.g. FIINDO_ENABLE_SPEEDBOOST=true
FIINDO_ENABLE_SPEEDBOOST = os.getenv("FIINDO_ENABLE_SPEEDBOOST", "false").lower() in {
    "1",
    "true",
    "yes",
}

# Optional override for the speedboost URL.
# If not set, it will be auto-generated from FIINDO_API_BASE_URL,
# with a final fallback to the official Fiindo speedboost endpoint.
FIINDO_SPEEDBOOST_URL = os.getenv("FIINDO_SPEEDBOOST_URL", "").strip()

class FiindoAPI:
    """Small helper client wrapping requests.Session for the Fiindo API."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        max_retries: int = MAX_RETRIES_DEFAULT,
        backoff_seconds: float = BACKOFF_SECONDS_DEFAULT,
        timeout_seconds: float = API_TIMEOUT_DEFAULT,
        retry_status_codes: Optional[Set[int]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.timeout_seconds = timeout_seconds
        self.retry_status_codes = (
            retry_status_codes if retry_status_codes is not None else RETRY_STATUS_CODES_DEFAULT
        )

        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # Low-level GET helper
    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Central GET request with basic error handling and retry logic.
        Returns a parsed JSON dict on success (HTTP 200),
        or None for 404 / certain recoverable errors.
        Raises an exception for unexpected failures.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        attempts = 0

        while True:
            attempts += 1
            logger.debug("GET %s (attempt %s)", url, attempts)

            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout_seconds,
                )
            except requests.Timeout:
                logger.warning(
                    "Timeout after %.1fs for %s (attempt %s/%s)",
                    self.timeout_seconds,
                    url,
                    attempts,
                    self.max_retries,
                )
                if attempts > self.max_retries:
                    logger.error("Giving up on %s after repeated timeouts.", url)
                    return None
                time.sleep(self.backoff_seconds)
                continue

            logger.debug("Response %s for %s", response.status_code, url)

            # Success path
            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as exc:
                    logger.error("Failed to decode JSON from %s: %s", url, exc)
                    raise

            # Retry-able conditions
            if response.status_code in self.retry_status_codes:
                if attempts > self.max_retries:
                    logger.error(
                        "%s errors too many times for %s – giving up.",
                        response.status_code,
                        url,
                    )
                    return None

                logger.warning(
                    "%s error for %s – retrying in %.1fs (attempt %s/%s)",
                    response.status_code,
                    url,
                    self.backoff_seconds,
                    attempts,
                    self.max_retries,
                )
                time.sleep(self.backoff_seconds)
                continue

            # Non-retry conditions
            if response.status_code == 404:
                logger.warning("404 Not Found for %s", url)
                return None

            if response.status_code == 401:
                logger.error(
                    "401 Unauthorized for %s – check FIRST_NAME / LAST_NAME", url
                )
                raise RuntimeError("Unauthorized for Fiindo API")

            # Unknown error
            logger.error(
                "Unexpected status %s from %s: %s",
                response.status_code,
                url,
                response.text,
            )
            response.raise_for_status()

    # High-level endpoint helpers
    def get_symbols(self) -> list[str]:
        """Return the list of all available symbols from /symbols."""
        data = self._get("symbols")
        return data.get("symbols", []) if data else []

    def get_general(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch /general information for a single symbol."""
        return self._get(f"general/{symbol}")

    def get_financials(self, symbol: str, statement: str) -> Optional[Dict[str, Any]]:
        """
        Fetch /financials for a given symbol and statement type.
        statement must be one of:
        - "income_statement"
        - "balance_sheet_statement"
        - "cash_flow_statement"
        """
        return self._get(f"financials/{symbol}/{statement}")

    def get_eod(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch end-of-day price data for a symbol."""
        return self._get(f"eod/{symbol}")

    def get_debug(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch debug information for a symbol from /debug/{symbol}."""
        return self._get(f"debug/{symbol}")


def enable_speedboost() -> None:
    """
    Enables Fiindo's 'speed boost' mode.
    Resolution logic for the speedboost URL:
    1) If FIINDO_SPEEDBOOST_URL is set → use that.
    2) Else auto-build: BASE_URL + '/speedboost'
    3) If auto-building fails → fallback to:
         https://api.test.fiindo.com/api/v1/speedboost
    This function NEVER stops the ETL. All errors are logged only.
    """
    if not FIINDO_ENABLE_SPEEDBOOST:
        logger.info("Speed boost disabled (FIINDO_ENABLE_SPEEDBOOST is not true).")
        return

    # 1) ENV override?
    url = None
    if FIINDO_SPEEDBOOST_URL:
        url = FIINDO_SPEEDBOOST_URL
        logger.info("Speedboost URL (from env): %s", url)
    else:
        # 2) Attempt auto-generation from BASE_URL
        try:
            auto_url = BASE_URL.rstrip("/") + "/speedboost"
            url = auto_url
            logger.info("Speedboost URL (auto-generated): %s", url)
        except Exception:
            url = None

    # 3) Final fallback
    if not url:
        url = "https://api.test.fiindo.com/api/v1/speedboost"
        logger.warning(
            "Falling back to default Speedboost URL: %s",
            url,
        )

    payload = {"first_name": FIRST_NAME, "last_name": LAST_NAME}
    try:
        logger.warning("Requesting Fiindo speed boost for this account…")
        resp = requests.post(
            url,
            json=payload,
            headers=HEADERS,
            timeout=API_TIMEOUT_DEFAULT,
        )

        if resp.status_code == 200:
            logger.warning("Speed boost successfully enabled")
        else:
            logger.warning(
                "Speedboost request failed (status %s): %s",
                resp.status_code,
                resp.text,
            )
    except Exception as exc:
        logger.warning("Speedboost request failed due to exception: %s", exc)


if __name__ == "__main__":  
    logging.basicConfig(level=logging.INFO)
    api = FiindoAPI()
    symbols = api.get_symbols()
    logger.info(
        "Got %d symbols, first example: %s",
        len(symbols),
        symbols[0] if symbols else "n/a",
    )
