"""
Global Market Fetcher - Phase 4.5
미국 시장 데이터 수집 (yfinance 활용)

핵심 기능:
- 미국 주요 지수 (SOX, 나스닥100, S&P500) 수집
- 핵심 종목 (NVIDIA, Micron, Tesla 등) 등락률 수집
- 나스닥100 선물 실시간 데이터
- 환율 (USD/KRW) 모니터링
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf


class MarketSession(Enum):
    """시장 세션"""
    PRE_MARKET = "pre_market"       # 프리마켓 (한국시간 18:00-22:30)
    REGULAR = "regular"              # 정규장 (한국시간 22:30-05:00)
    AFTER_HOURS = "after_hours"      # 애프터마켓 (한국시간 05:00-07:00)
    CLOSED = "closed"                # 휴장


class MarketSentiment(Enum):
    """시장 심리"""
    STRONG_BULLISH = "strong_bullish"   # +2% 이상
    BULLISH = "bullish"                  # +0.5% ~ +2%
    NEUTRAL = "neutral"                  # -0.5% ~ +0.5%
    BEARISH = "bearish"                  # -2% ~ -0.5%
    STRONG_BEARISH = "strong_bearish"   # -2% 이하


@dataclass
class IndexData:
    """지수 데이터"""
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: str


@dataclass
class GlobalMarketData:
    """글로벌 시장 데이터"""
    # 주요 지수
    indices: Dict[str, IndexData]

    # 핵심 종목
    stocks: Dict[str, IndexData]

    # 환율
    usd_krw: float
    usd_krw_change: float

    # 선물
    nasdaq_futures: Optional[IndexData]

    # 분석
    overall_sentiment: MarketSentiment
    sector_sentiments: Dict[str, MarketSentiment]

    # 메타데이터
    fetched_at: str
    market_session: MarketSession


class GlobalMarketFetcher:
    """
    글로벌 시장 데이터 수집기

    Phase 4.5 Spec:
    - yfinance로 미국 주요 지수 및 핵심 종목 수집
    - 나스닥100 선물 실시간 모니터링
    - 환율(USD/KRW) 추적
    """

    # 주요 지수
    INDICES = {
        '^IXIC': '나스닥 종합',
        '^NDX': '나스닥 100',
        '^SOX': '필라델피아 반도체',
        '^GSPC': 'S&P 500',
        '^DJI': '다우 존스',
        '^VIX': 'VIX (공포지수)',
    }

    # 핵심 종목 (한국 커플링용)
    KEY_STOCKS = {
        # 반도체 (삼성전자, SK하이닉스 커플링)
        'NVDA': 'NVIDIA',
        'MU': 'Micron',
        'AMD': 'AMD',
        'INTC': 'Intel',
        'ASML': 'ASML',

        # 2차전지/EV (금양그린파워, 에코프로 커플링)
        'TSLA': 'Tesla',
        'RIVN': 'Rivian',
        'ALB': 'Albemarle (리튬)',

        # 테크 (카카오 커플링)
        'META': 'Meta',
        'GOOGL': 'Google',
        'AAPL': 'Apple',

        # 에너지/유틸리티 (한국전력, HD현대에너지솔루션 커플링)
        'FSLR': 'First Solar',
        'ENPH': 'Enphase',
        'NEE': 'NextEra Energy',
    }

    # 선물
    FUTURES = {
        'NQ=F': '나스닥100 선물',
        'ES=F': 'S&P500 선물',
    }

    # 환율
    FOREX = {
        'KRW=X': 'USD/KRW',
    }

    # 캐시 TTL
    CACHE_TTL = timedelta(minutes=5)

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cache: Optional[Tuple[GlobalMarketData, datetime]] = None
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def fetch(self, force_refresh: bool = False) -> GlobalMarketData:
        """
        글로벌 시장 데이터 수집

        Args:
            force_refresh: 캐시 무시하고 새로 조회

        Returns:
            GlobalMarketData: 시장 데이터
        """
        # 캐시 확인
        if not force_refresh and self._cache:
            cached_data, cached_at = self._cache
            if datetime.now() - cached_at < self.CACHE_TTL:
                self.logger.debug("Returning cached global market data")
                return cached_data

        self.logger.info("Fetching global market data...")

        # 병렬로 데이터 수집
        loop = asyncio.get_event_loop()

        indices_task = loop.run_in_executor(self._executor, self._fetch_indices)
        stocks_task = loop.run_in_executor(self._executor, self._fetch_stocks)
        forex_task = loop.run_in_executor(self._executor, self._fetch_forex)
        futures_task = loop.run_in_executor(self._executor, self._fetch_futures)

        indices, stocks, forex, futures = await asyncio.gather(
            indices_task, stocks_task, forex_task, futures_task
        )

        # 시장 심리 분석
        overall_sentiment = self._analyze_overall_sentiment(indices, stocks)
        sector_sentiments = self._analyze_sector_sentiments(stocks)

        # 시장 세션 판단
        market_session = self._get_market_session()

        result = GlobalMarketData(
            indices=indices,
            stocks=stocks,
            usd_krw=forex.get('usd_krw', 0.0),
            usd_krw_change=forex.get('usd_krw_change', 0.0),
            nasdaq_futures=futures.get('NQ=F'),
            overall_sentiment=overall_sentiment,
            sector_sentiments=sector_sentiments,
            fetched_at=datetime.now().isoformat(),
            market_session=market_session
        )

        # 캐시 저장
        self._cache = (result, datetime.now())

        return result

    def _fetch_indices(self) -> Dict[str, IndexData]:
        """주요 지수 조회"""
        result = {}

        try:
            tickers = yf.Tickers(' '.join(self.INDICES.keys()))

            for symbol, name in self.INDICES.items():
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker is None:
                        continue

                    info = ticker.info
                    hist = ticker.history(period='2d')

                    if hist.empty:
                        continue

                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change = current_price - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close > 0 else 0

                    result[symbol] = IndexData(
                        symbol=symbol,
                        name=name,
                        price=round(current_price, 2),
                        change=round(change, 2),
                        change_pct=round(change_pct, 2),
                        volume=int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
                        timestamp=datetime.now().isoformat()
                    )

                except Exception as e:
                    self.logger.warning(f"Failed to fetch {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to fetch indices: {e}")

        return result

    def _fetch_stocks(self) -> Dict[str, IndexData]:
        """핵심 종목 조회"""
        result = {}

        try:
            tickers = yf.Tickers(' '.join(self.KEY_STOCKS.keys()))

            for symbol, name in self.KEY_STOCKS.items():
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker is None:
                        continue

                    hist = ticker.history(period='2d')

                    if hist.empty:
                        continue

                    current_price = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                    change = current_price - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close > 0 else 0

                    result[symbol] = IndexData(
                        symbol=symbol,
                        name=name,
                        price=round(current_price, 2),
                        change=round(change, 2),
                        change_pct=round(change_pct, 2),
                        volume=int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0,
                        timestamp=datetime.now().isoformat()
                    )

                except Exception as e:
                    self.logger.warning(f"Failed to fetch {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to fetch stocks: {e}")

        return result

    def _fetch_forex(self) -> Dict[str, float]:
        """환율 조회"""
        try:
            ticker = yf.Ticker('KRW=X')
            hist = ticker.history(period='2d')

            if hist.empty:
                return {'usd_krw': 0.0, 'usd_krw_change': 0.0}

            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
            change = ((current - prev) / prev) * 100 if prev > 0 else 0

            return {
                'usd_krw': round(current, 2),
                'usd_krw_change': round(change, 2)
            }

        except Exception as e:
            self.logger.warning(f"Failed to fetch forex: {e}")
            return {'usd_krw': 0.0, 'usd_krw_change': 0.0}

    def _fetch_futures(self) -> Dict[str, IndexData]:
        """선물 조회"""
        result = {}

        try:
            for symbol, name in self.FUTURES.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='2d')

                if hist.empty:
                    continue

                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close > 0 else 0

                result[symbol] = IndexData(
                    symbol=symbol,
                    name=name,
                    price=round(current_price, 2),
                    change=round(change, 2),
                    change_pct=round(change_pct, 2),
                    volume=0,
                    timestamp=datetime.now().isoformat()
                )

        except Exception as e:
            self.logger.warning(f"Failed to fetch futures: {e}")

        return result

    def _analyze_overall_sentiment(
        self,
        indices: Dict[str, IndexData],
        stocks: Dict[str, IndexData]
    ) -> MarketSentiment:
        """전체 시장 심리 분석"""
        # 주요 지수 평균 변화율
        key_indices = ['^IXIC', '^NDX', '^GSPC']
        changes = []

        for symbol in key_indices:
            if symbol in indices:
                changes.append(indices[symbol].change_pct)

        if not changes:
            return MarketSentiment.NEUTRAL

        avg_change = sum(changes) / len(changes)

        if avg_change >= 2.0:
            return MarketSentiment.STRONG_BULLISH
        elif avg_change >= 0.5:
            return MarketSentiment.BULLISH
        elif avg_change <= -2.0:
            return MarketSentiment.STRONG_BEARISH
        elif avg_change <= -0.5:
            return MarketSentiment.BEARISH
        else:
            return MarketSentiment.NEUTRAL

    def _analyze_sector_sentiments(
        self,
        stocks: Dict[str, IndexData]
    ) -> Dict[str, MarketSentiment]:
        """섹터별 심리 분석"""
        sectors = {
            'semiconductor': ['NVDA', 'MU', 'AMD', 'INTC', 'ASML'],
            'ev_battery': ['TSLA', 'RIVN', 'ALB'],
            'tech': ['META', 'GOOGL', 'AAPL'],
            'energy': ['FSLR', 'ENPH', 'NEE'],
        }

        result = {}

        for sector, symbols in sectors.items():
            changes = []
            for symbol in symbols:
                if symbol in stocks:
                    changes.append(stocks[symbol].change_pct)

            if not changes:
                result[sector] = MarketSentiment.NEUTRAL
                continue

            avg_change = sum(changes) / len(changes)

            if avg_change >= 2.0:
                result[sector] = MarketSentiment.STRONG_BULLISH
            elif avg_change >= 0.5:
                result[sector] = MarketSentiment.BULLISH
            elif avg_change <= -2.0:
                result[sector] = MarketSentiment.STRONG_BEARISH
            elif avg_change <= -0.5:
                result[sector] = MarketSentiment.BEARISH
            else:
                result[sector] = MarketSentiment.NEUTRAL

        return result

    def _get_market_session(self) -> MarketSession:
        """현재 미국 시장 세션 판단 (한국 시간 기준)"""
        now = datetime.now()
        hour = now.hour

        # 한국 시간 기준 (EST + 14시간)
        # 프리마켓: 18:00-22:30 KST
        # 정규장: 22:30-05:00 KST
        # 애프터마켓: 05:00-07:00 KST

        if 18 <= hour < 22:
            return MarketSession.PRE_MARKET
        elif 22 <= hour or hour < 5:
            return MarketSession.REGULAR
        elif 5 <= hour < 7:
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.CLOSED

    def clear_cache(self):
        """캐시 초기화"""
        self._cache = None
        self.logger.info("Global market cache cleared")


# Singleton instance
_fetcher_instance: Optional[GlobalMarketFetcher] = None


def get_global_market_fetcher() -> GlobalMarketFetcher:
    """Get singleton GlobalMarketFetcher instance"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = GlobalMarketFetcher()
    return _fetcher_instance
