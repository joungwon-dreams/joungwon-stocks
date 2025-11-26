import aiohttp
import logging

logger = logging.getLogger(__name__)

class DaumBaseFetcher:
    BASE_URL = "https://finance.daum.net/api"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://finance.daum.net/',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://finance.daum.net'
    }

    def _get_headers(self, symbol_code=None):
        headers = self.HEADERS.copy()
        if symbol_code:
            headers['Referer'] = f'https://finance.daum.net/quotes/{symbol_code}'
        return headers
