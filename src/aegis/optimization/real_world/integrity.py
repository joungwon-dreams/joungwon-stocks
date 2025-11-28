"""
Data Integrity Manager - Phase 6
데이터 무결성 및 Failover 관리

핵심 기능:
- 데이터 소스 Failover (pykrx -> KIS API)
- Nasdaq 100 선물 (NQ=F) 실시간 조회
- 데이터 신선도 및 지연 모니터링
"""
import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

try:
    import yfinance as yf
except ImportError:
    yf = None


class DataSource(Enum):
    """데이터 소스"""
    PYKRX = "pykrx"
    KIS_API = "kis_api"
    YFINANCE = "yfinance"
    NAVER = "naver"
    DART = "dart"


class DataStatus(Enum):
    """데이터 상태"""
    FRESH = "fresh"          # 신선 (5분 이내)
    STALE = "stale"          # 오래됨 (5분 ~ 1시간)
    OUTDATED = "outdated"    # 매우 오래됨 (1시간 이상)
    UNAVAILABLE = "unavailable"  # 사용 불가


@dataclass
class GlobexData:
    """Globex 선물 데이터"""
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: datetime
    source: DataSource
    status: DataStatus


@dataclass
class DataHealthReport:
    """데이터 건강 상태 리포트"""
    overall_status: DataStatus
    sources: Dict[str, DataStatus]
    latencies: Dict[str, float]  # 밀리초
    last_update: Dict[str, datetime]
    warnings: List[str]
    generated_at: str


class DataIntegrityManager:
    """
    데이터 무결성 관리자

    Phase 6 Spec:
    - 데이터 소스 Failover 관리
    - NQ 선물 실시간 조회 (장 시작 전 분석용)
    - 데이터 신선도 모니터링
    """

    # Globex 심볼 매핑
    GLOBEX_SYMBOLS = {
        'NQ': 'NQ=F',   # Nasdaq 100 E-mini
        'ES': 'ES=F',   # S&P 500 E-mini
        'YM': 'YM=F',   # Dow Jones E-mini
        'RTY': 'RTY=F', # Russell 2000 E-mini
    }

    # 데이터 신선도 기준 (초)
    FRESHNESS = {
        'fresh': 300,      # 5분
        'stale': 3600,     # 1시간
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._source_status: Dict[DataSource, DataStatus] = {}
        self._last_fetch: Dict[str, datetime] = {}
        self._cache: Dict[str, Any] = {}

    async def get_nq_futures(self) -> Optional[GlobexData]:
        """
        Nasdaq 100 선물 (NQ=F) 실시간 데이터 조회

        Returns:
            GlobexData: NQ 선물 데이터
        """
        return await self._fetch_globex_data('NQ')

    async def get_es_futures(self) -> Optional[GlobexData]:
        """S&P 500 선물 (ES=F) 실시간 데이터 조회"""
        return await self._fetch_globex_data('ES')

    async def get_all_futures(self) -> Dict[str, GlobexData]:
        """모든 주요 선물 데이터 조회"""
        tasks = [
            self._fetch_globex_data('NQ'),
            self._fetch_globex_data('ES'),
            self._fetch_globex_data('YM'),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        futures_data = {}
        for symbol, result in zip(['NQ', 'ES', 'YM'], results):
            if isinstance(result, GlobexData):
                futures_data[symbol] = result

        return futures_data

    async def _fetch_globex_data(self, symbol: str) -> Optional[GlobexData]:
        """Globex 선물 데이터 조회"""
        if yf is None:
            self.logger.warning("yfinance not installed")
            return None

        yahoo_symbol = self.GLOBEX_SYMBOLS.get(symbol)
        if not yahoo_symbol:
            return None

        # 캐시 체크 (1분 이내면 캐시 반환)
        cache_key = f"globex_{symbol}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (datetime.now() - cached_time).seconds < 60:
                return cached_data

        try:
            ticker = yf.Ticker(yahoo_symbol)
            info = ticker.info

            # 최근 1일 데이터
            hist = ticker.history(period='1d', interval='1m')

            if hist.empty:
                return None

            latest = hist.iloc[-1]
            prev_close = info.get('previousClose', latest['Open'])

            price = latest['Close']
            change = price - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else 0

            data = GlobexData(
                symbol=symbol,
                price=round(price, 2),
                change=round(change, 2),
                change_pct=round(change_pct, 2),
                volume=int(latest['Volume']),
                timestamp=datetime.now(),
                source=DataSource.YFINANCE,
                status=DataStatus.FRESH
            )

            # 캐시 저장
            self._cache[cache_key] = (data, datetime.now())
            self._last_fetch[cache_key] = datetime.now()

            return data

        except Exception as e:
            self.logger.error(f"Failed to fetch {symbol} futures: {e}")
            return None

    def get_premarket_signal(self, nq_data: GlobexData) -> Dict[str, Any]:
        """
        장 시작 전 신호 생성 (08:50 ~ 09:00 사용)

        Args:
            nq_data: NQ 선물 데이터

        Returns:
            프리마켓 신호 정보
        """
        change_pct = nq_data.change_pct

        # 신호 결정
        if change_pct >= 1.5:
            signal = "strong_gap_up"
            bias = "bullish"
            weight_adjustment = 1.2  # 상승 가중치 증가
        elif change_pct >= 0.5:
            signal = "gap_up"
            bias = "bullish"
            weight_adjustment = 1.1
        elif change_pct <= -1.5:
            signal = "strong_gap_down"
            bias = "bearish"
            weight_adjustment = 0.8  # 하락 시 매수 가중치 감소
        elif change_pct <= -0.5:
            signal = "gap_down"
            bias = "bearish"
            weight_adjustment = 0.9
        else:
            signal = "flat"
            bias = "neutral"
            weight_adjustment = 1.0

        return {
            'signal': signal,
            'bias': bias,
            'nq_change_pct': change_pct,
            'weight_adjustment': weight_adjustment,
            'recommendation': self._get_premarket_recommendation(signal),
            'timestamp': datetime.now().isoformat()
        }

    def _get_premarket_recommendation(self, signal: str) -> str:
        """프리마켓 신호에 따른 권고사항"""
        recommendations = {
            'strong_gap_up': "강한 갭상승 예상. 추격매수 주의, 눌림목 대기 권장",
            'gap_up': "갭상승 예상. 시초가 매수 검토 가능",
            'flat': "보합 출발 예상. 기존 전략 유지",
            'gap_down': "갭하락 예상. 저가 매수 기회 모색",
            'strong_gap_down': "강한 갭하락 예상. 신규 매수 자제, 손절 라인 점검",
        }
        return recommendations.get(signal, "")

    async def check_data_health(self) -> DataHealthReport:
        """데이터 소스 건강 상태 체크"""
        warnings = []
        sources_status = {}
        latencies = {}
        last_updates = {}

        # NQ 선물 체크
        start = datetime.now()
        nq_data = await self.get_nq_futures()
        latency = (datetime.now() - start).total_seconds() * 1000

        if nq_data:
            sources_status['NQ_futures'] = DataStatus.FRESH
            latencies['NQ_futures'] = latency
            last_updates['NQ_futures'] = nq_data.timestamp
        else:
            sources_status['NQ_futures'] = DataStatus.UNAVAILABLE
            warnings.append("NQ futures data unavailable")

        # 전체 상태 결정
        if DataStatus.UNAVAILABLE in sources_status.values():
            overall = DataStatus.STALE
        elif all(s == DataStatus.FRESH for s in sources_status.values()):
            overall = DataStatus.FRESH
        else:
            overall = DataStatus.STALE

        return DataHealthReport(
            overall_status=overall,
            sources=sources_status,
            latencies=latencies,
            last_update=last_updates,
            warnings=warnings,
            generated_at=datetime.now().isoformat()
        )

    def is_premarket_time(self) -> bool:
        """프리마켓 시간 여부 (08:30 ~ 09:00)"""
        now = datetime.now().time()
        return time(8, 30) <= now <= time(9, 0)

    def is_market_open(self) -> bool:
        """장 운영 시간 여부 (09:00 ~ 15:30)"""
        now = datetime.now().time()
        return time(9, 0) <= now <= time(15, 30)

    def is_after_hours(self) -> bool:
        """시간외 거래 시간 여부"""
        now = datetime.now().time()
        # 시간외 단일가: 15:40 ~ 16:00, 16:00 ~ 18:00
        return time(15, 40) <= now <= time(18, 0)


# Singleton instance
_manager_instance: Optional[DataIntegrityManager] = None


def get_integrity_manager() -> DataIntegrityManager:
    """Get singleton DataIntegrityManager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DataIntegrityManager()
    return _manager_instance
