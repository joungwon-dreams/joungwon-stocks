"""
SignalTraceManager - Phase 7 (Upgraded)
신호별 수익률 실시간 추적 및 MFE/MAE 계산

핵심 기능:
- 아직 종료되지 않은 신호들의 수익률 실시간 업데이트
- min_ticks 데이터 활용 MFE/MAE 계산
- 5분/10분/30분/60분 수익률 추적
- 실패 원인 태깅 (MarketScanner/NewsSentimentAnalyzer 연동)
- market_context JSONB 저장
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from src.config.database import db


class TraceStatus(Enum):
    """신호 추적 상태"""
    PENDING = "pending"       # 추적 대기
    TRACKING = "tracking"     # 추적 중
    COMPLETED = "completed"   # 추적 완료
    EXPIRED = "expired"       # 만료 (장 마감)
    ERROR = "error"           # 오류


class FailureTag(Enum):
    """실패 원인 태그"""
    MARKET_CRASH = "market_crash"           # 시장 급락
    SECTOR_ROTATION = "sector_rotation"     # 섹터 로테이션
    FAKE_BREAKOUT = "fake_breakout"         # 가짜 돌파
    NEWS_SHOCK = "news_shock"               # 뉴스 충격
    STOP_LOSS_HIT = "stop_loss_hit"         # 손절 도달
    TIME_DECAY = "time_decay"               # 시간 소진
    LIQUIDITY_ISSUE = "liquidity_issue"     # 유동성 문제
    UNKNOWN = "unknown"                     # 원인 불명


@dataclass
class SignalTrace:
    """신호 추적 데이터"""
    signal_id: int
    ticker: str
    signal_price: float
    signal_time: datetime
    signal_type: str  # BUY / SELL / HOLD

    # 수익률 추적
    return_5m: Optional[float] = None
    return_10m: Optional[float] = None
    return_30m: Optional[float] = None
    return_60m: Optional[float] = None

    # MFE/MAE
    mfe: float = 0.0  # Max Favorable Excursion
    mae: float = 0.0  # Max Adverse Excursion

    # 현재 상태
    current_price: Optional[float] = None
    current_return: Optional[float] = None

    # 추적 메타
    trace_status: TraceStatus = TraceStatus.PENDING
    failure_tag: Optional[FailureTag] = None

    # 시장 컨텍스트 (NEW)
    market_context: Optional[Dict[str, Any]] = None

    def calculate_return(self, price: float) -> float:
        """수익률 계산"""
        if self.signal_price <= 0:
            return 0.0
        return ((price - self.signal_price) / self.signal_price) * 100


class SignalTraceManager:
    """
    신호 추적 관리자

    Phase 7 Spec (Upgraded):
    - 백그라운드 실행 또는 PDF 생성 시 동기 호출
    - min_ticks 데이터 활용 MFE/MAE 계산
    - 시간별 수익률 추적 (5m, 10m, 30m, 60m)
    - 실패 원인 자동 태깅 (MarketScanner/NewsSentimentAnalyzer 연동)
    - market_context JSONB 저장
    """

    # 추적 시간 간격 (분)
    TRACE_INTERVALS = [5, 10, 30, 60]

    # MFE/MAE 업데이트 주기 (초)
    UPDATE_INTERVAL = 60

    # 최대 추적 시간 (분) - 장중에만 추적
    MAX_TRACE_DURATION = 240  # 4시간

    # 실패 판정 임계값
    FAILURE_THRESHOLDS = {
        'market_crash': -1.0,      # KOSPI -1% 이하
        'news_shock': -0.5,        # 뉴스 감성 -0.5 이하
        'sector_drop': -1.5,       # 동일 섹터 -1.5% 이하
    }

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._running = False
        self._active_traces: Dict[int, SignalTrace] = {}

        # 외부 분석기 (Lazy Load)
        self._market_scanner = None
        self._news_analyzer = None

    def _get_market_scanner(self):
        """MarketScanner lazy load"""
        if self._market_scanner is None:
            try:
                from src.fetchers.tier1_official_libs.market_scanner import MarketScanner
                self._market_scanner = MarketScanner()
            except ImportError:
                self.logger.warning("MarketScanner not available")
        return self._market_scanner

    def _get_news_analyzer(self):
        """NewsSentimentAnalyzer lazy load"""
        if self._news_analyzer is None:
            try:
                from src.aegis.fusion.news_sentiment import NewsSentimentAnalyzer
                self._news_analyzer = NewsSentimentAnalyzer()
            except ImportError:
                self.logger.warning("NewsSentimentAnalyzer not available")
        return self._news_analyzer

    async def start(self):
        """추적 시작 (백그라운드 데몬 모드)"""
        self._running = True
        self.logger.info("SignalTraceManager started")

        while self._running:
            try:
                await self._update_cycle()
                await asyncio.sleep(self.UPDATE_INTERVAL)
            except Exception as e:
                self.logger.error(f"Trace cycle error: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        """추적 중지"""
        self._running = False
        self.logger.info("SignalTraceManager stopped")

    async def update_traces(self):
        """
        추적 업데이트 (단일 실행)
        PDF 생성 시 호출하는 동기식 메서드
        """
        self.logger.info("SignalTraceManager.update_traces() called")
        await self._update_cycle()
        return len(self._active_traces)

    async def _update_cycle(self):
        """업데이트 사이클"""
        # 1. 추적 대상 신호 로드
        await self._load_pending_signals()

        # 2. 시장 컨텍스트 수집 (한 번만)
        market_context = await self._collect_market_context()

        # 3. 각 신호 업데이트
        for signal_id, trace in list(self._active_traces.items()):
            try:
                await self._update_signal_trace(trace, market_context)
            except Exception as e:
                self.logger.error(f"Failed to update signal {signal_id}: {e}")

        # 4. DB 업데이트
        await self._save_traces()

    async def _collect_market_context(self) -> Dict[str, Any]:
        """시장 컨텍스트 수집 (MarketScanner + NewsSentimentAnalyzer)"""
        context = {
            'collected_at': datetime.now().isoformat(),
            'kospi_change': None,
            'kosdaq_change': None,
            'leading_sectors': [],
            'lagging_sectors': [],
            'market_breadth': None,
            'news_sentiment': None,
        }

        # 1. MarketScanner에서 시장 데이터 수집
        scanner = self._get_market_scanner()
        if scanner:
            try:
                # KOSPI 섹터 히트맵
                heatmap = await scanner.get_sector_heatmap("KOSPI")
                if heatmap and 'sectors' in heatmap:
                    sectors = heatmap['sectors']
                    if sectors:
                        # 상승/하락 섹터 분류
                        sorted_sectors = sorted(sectors, key=lambda x: x.get('change_pct', 0), reverse=True)
                        context['leading_sectors'] = [s['name'] for s in sorted_sectors[:3] if s.get('change_pct', 0) > 0]
                        context['lagging_sectors'] = [s['name'] for s in sorted_sectors[-3:] if s.get('change_pct', 0) < 0]

                        # 평균 변동률로 시장 분위기 추정
                        avg_change = sum(s.get('change_pct', 0) for s in sectors) / len(sectors)
                        context['kospi_change'] = round(avg_change, 2)

                # ADR (Advance-Decline Ratio)
                try:
                    adr = await scanner.get_market_breadth("KOSPI")
                    if adr:
                        context['market_breadth'] = adr
                except:
                    pass

            except Exception as e:
                self.logger.warning(f"Failed to collect market scanner data: {e}")

        # 2. NewsSentimentAnalyzer는 종목별로 호출해야 하므로 여기서는 생략
        # (개별 종목 분석 시 호출)

        return context

    async def _get_news_sentiment_for_ticker(self, ticker: str) -> Optional[float]:
        """특정 종목의 뉴스 감성 점수 조회"""
        analyzer = self._get_news_analyzer()
        if not analyzer:
            return None

        try:
            result = await analyzer.analyze(ticker)
            if result:
                return result.score
        except Exception as e:
            self.logger.debug(f"Failed to get news sentiment for {ticker}: {e}")

        return None

    async def _load_pending_signals(self):
        """추적 대기 중인 신호 로드"""
        query = """
            SELECT
                id, stock_code, stock_name, signal_type, signal_score,
                current_price as signal_price, recorded_at,
                return_5m, return_10m, return_30m, return_60m,
                mfe, mae, trace_status, market_context
            FROM aegis_signal_history
            WHERE trace_status IN ('pending', 'tracking')
              AND recorded_at > NOW() - INTERVAL '4 hours'
            ORDER BY recorded_at DESC
        """

        try:
            rows = await db.fetch(query)

            for row in rows:
                signal_id = row['id']

                if signal_id not in self._active_traces:
                    # 신호 가격이 없으면 현재가로 대체
                    signal_price = row['signal_price']
                    if not signal_price:
                        signal_price = await self._get_current_price(row['stock_code'])

                    self._active_traces[signal_id] = SignalTrace(
                        signal_id=signal_id,
                        ticker=row['stock_code'],
                        signal_price=signal_price or 0,
                        signal_time=row['recorded_at'],
                        signal_type=row['signal_type'] or 'HOLD',
                        return_5m=row['return_5m'],
                        return_10m=row['return_10m'],
                        return_30m=row['return_30m'],
                        return_60m=row['return_60m'],
                        mfe=row['mfe'] or 0,
                        mae=row['mae'] or 0,
                        trace_status=TraceStatus(row['trace_status'] or 'pending'),
                        market_context=row['market_context'] if row['market_context'] else None
                    )

            self.logger.debug(f"Loaded {len(self._active_traces)} signals to trace")

        except Exception as e:
            self.logger.error(f"Failed to load pending signals: {e}")

    async def _update_signal_trace(self, trace: SignalTrace, market_context: Dict[str, Any]):
        """개별 신호 추적 업데이트"""
        now = datetime.now()
        elapsed_minutes = (now - trace.signal_time).total_seconds() / 60

        # 추적 시간 초과 체크
        if elapsed_minutes > self.MAX_TRACE_DURATION:
            trace.trace_status = TraceStatus.EXPIRED
            return

        # min_ticks에서 최신 가격 데이터 조회
        prices = await self._get_price_history(
            trace.ticker,
            trace.signal_time,
            now
        )

        if not prices:
            return

        # 현재 가격 업데이트
        trace.current_price = prices[-1]['close'] if prices else None
        if trace.current_price:
            trace.current_return = trace.calculate_return(trace.current_price)

        # MFE/MAE 계산
        await self._calculate_mfe_mae(trace, prices)

        # 시간별 수익률 계산
        await self._calculate_interval_returns(trace, elapsed_minutes, prices)

        # 상태 업데이트
        if trace.trace_status == TraceStatus.PENDING:
            trace.trace_status = TraceStatus.TRACKING
            # 최초 추적 시작 시 시장 컨텍스트 저장
            if not trace.market_context:
                trace.market_context = {
                    'signal_time': market_context.copy(),
                }

        # 60분 수익률까지 계산 완료되면 COMPLETED
        if trace.return_60m is not None:
            trace.trace_status = TraceStatus.COMPLETED

            # 종료 시점 시장 컨텍스트 추가
            if trace.market_context:
                trace.market_context['completion_time'] = market_context.copy()

            # 실패 태깅 (손실인 경우)
            if trace.return_60m < 0:
                trace.failure_tag = await self._analyze_failure_with_context(trace, market_context)

    async def _calculate_mfe_mae(self, trace: SignalTrace, prices: List[Dict]):
        """MFE/MAE 계산"""
        if not prices or trace.signal_price <= 0:
            return

        max_price = max(p['high'] for p in prices)
        min_price = min(p['low'] for p in prices)

        # MFE: 최대 수익폭 (%)
        mfe = ((max_price - trace.signal_price) / trace.signal_price) * 100
        trace.mfe = max(trace.mfe, mfe)

        # MAE: 최대 손실폭 (%) - 음수로 표현
        mae = ((min_price - trace.signal_price) / trace.signal_price) * 100
        trace.mae = min(trace.mae, mae)

    async def _calculate_interval_returns(
        self,
        trace: SignalTrace,
        elapsed_minutes: float,
        prices: List[Dict]
    ):
        """시간별 수익률 계산"""
        if not prices or trace.signal_price <= 0:
            return

        for interval in self.TRACE_INTERVALS:
            attr_name = f"return_{interval}m"

            # 이미 계산된 경우 스킵
            if getattr(trace, attr_name) is not None:
                continue

            # 해당 시간이 경과했는지 체크
            if elapsed_minutes >= interval:
                # 해당 시점의 가격 찾기
                target_time = trace.signal_time + timedelta(minutes=interval)
                price_at_interval = self._find_price_at_time(prices, target_time)

                if price_at_interval:
                    return_pct = trace.calculate_return(price_at_interval)
                    setattr(trace, attr_name, round(return_pct, 2))

    def _find_price_at_time(self, prices: List[Dict], target_time: datetime) -> Optional[float]:
        """특정 시점의 가격 찾기"""
        for price in prices:
            if price['timestamp'] >= target_time:
                return price['close']
        return prices[-1]['close'] if prices else None

    async def _analyze_failure_with_context(
        self,
        trace: SignalTrace,
        market_context: Dict[str, Any]
    ) -> FailureTag:
        """
        컨텍스트 기반 실패 원인 분석 (업그레이드)

        판정 로직:
        - KOSPI < -1.0% → market_crash
        - 뉴스 감성 < -0.5 → news_shock
        - 동일 섹터 하락 → sector_rotation
        """
        # 1. 시장 급락 체크 (KOSPI -1% 이하)
        kospi_change = market_context.get('kospi_change')
        if kospi_change is not None and kospi_change < self.FAILURE_THRESHOLDS['market_crash']:
            return FailureTag.MARKET_CRASH

        # 2. 뉴스 충격 체크
        news_sentiment = await self._get_news_sentiment_for_ticker(trace.ticker)
        if news_sentiment is not None and news_sentiment < self.FAILURE_THRESHOLDS['news_shock']:
            return FailureTag.NEWS_SHOCK

        # 3. 섹터 로테이션 체크 (해당 종목 섹터가 lagging에 있는지)
        lagging_sectors = market_context.get('lagging_sectors', [])
        if lagging_sectors:
            # 종목의 섹터 정보 조회 (DB에서)
            stock_sector = await self._get_stock_sector(trace.ticker)
            if stock_sector and any(sector in stock_sector for sector in lagging_sectors):
                return FailureTag.SECTOR_ROTATION

        # 4. 기존 패턴 기반 분석
        # MAE가 크면 급락 의심 → fake_breakout
        if trace.mae < -5:
            return FailureTag.FAKE_BREAKOUT

        # MFE가 높았지만 손실로 끝난 경우 → time_decay
        if trace.mfe > 2 and trace.return_60m and trace.return_60m < 0:
            return FailureTag.TIME_DECAY

        # 5분 수익률은 양수였지만 이후 하락
        if trace.return_5m and trace.return_5m > 0:
            if trace.return_60m and trace.return_60m < 0:
                return FailureTag.SECTOR_ROTATION

        return FailureTag.UNKNOWN

    async def _get_stock_sector(self, ticker: str) -> Optional[str]:
        """종목의 섹터 정보 조회"""
        query = """
            SELECT sector FROM stocks WHERE stock_code = $1
        """
        try:
            row = await db.fetchrow(query, ticker)
            return row['sector'] if row else None
        except:
            return None

    async def _get_price_history(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """min_ticks에서 가격 히스토리 조회"""
        query = """
            SELECT
                timestamp, open, high, low, close, volume
            FROM min_ticks
            WHERE stock_code = $1
              AND timestamp BETWEEN $2 AND $3
            ORDER BY timestamp ASC
        """

        try:
            rows = await db.fetch(query, ticker, start_time, end_time)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get price history for {ticker}: {e}")
            return []

    async def _get_current_price(self, ticker: str) -> Optional[float]:
        """현재가 조회"""
        query = """
            SELECT close
            FROM min_ticks
            WHERE stock_code = $1
            ORDER BY timestamp DESC
            LIMIT 1
        """
        try:
            row = await db.fetchrow(query, ticker)
            return row['close'] if row else None
        except:
            return None

    async def _save_traces(self):
        """추적 결과 DB 저장"""
        for signal_id, trace in self._active_traces.items():
            await self._update_signal_in_db(trace)

        # 완료/만료된 추적 제거
        completed = [
            sid for sid, t in self._active_traces.items()
            if t.trace_status in (TraceStatus.COMPLETED, TraceStatus.EXPIRED, TraceStatus.ERROR)
        ]
        for sid in completed:
            del self._active_traces[sid]

    async def _update_signal_in_db(self, trace: SignalTrace):
        """개별 신호 DB 업데이트 (market_context 포함)"""
        query = """
            UPDATE aegis_signal_history
            SET
                return_5m = COALESCE($2, return_5m),
                return_10m = COALESCE($3, return_10m),
                return_30m = COALESCE($4, return_30m),
                return_60m = COALESCE($5, return_60m),
                mfe = $6,
                mae = $7,
                trace_status = $8,
                failure_tag = $9,
                trace_started_at = COALESCE(trace_started_at, $10),
                trace_completed_at = CASE WHEN $8 = 'completed' THEN $11 ELSE NULL END,
                market_context = COALESCE($12, market_context)
            WHERE id = $1
        """

        try:
            # market_context를 JSON 문자열로 변환
            market_context_json = None
            if trace.market_context:
                market_context_json = json.dumps(trace.market_context, ensure_ascii=False, default=str)

            await db.execute(
                query,
                trace.signal_id,
                trace.return_5m,
                trace.return_10m,
                trace.return_30m,
                trace.return_60m,
                trace.mfe,
                trace.mae,
                trace.trace_status.value,
                trace.failure_tag.value if trace.failure_tag else None,
                trace.signal_time,
                datetime.now() if trace.trace_status == TraceStatus.COMPLETED else None,
                market_context_json
            )
        except Exception as e:
            self.logger.error(f"Failed to update signal {trace.signal_id}: {e}")

    # ========== 통계 조회 메서드 ==========

    async def get_win_rate_by_hour(self, days: int = 30) -> Dict[int, Dict[str, float]]:
        """시간대별 승률 조회"""
        query = """
            SELECT
                EXTRACT(HOUR FROM created_at) as hour,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE return_60m > 0) as wins,
                AVG(return_60m) as avg_return
            FROM aegis_signal_history
            WHERE trace_status = 'completed'
              AND created_at > NOW() - $1 * INTERVAL '1 day'
            GROUP BY EXTRACT(HOUR FROM created_at)
            ORDER BY hour
        """

        try:
            rows = await db.fetch(query, days)
            result = {}
            for row in rows:
                hour = int(row['hour'])
                total = row['total']
                wins = row['wins']
                result[hour] = {
                    'total': total,
                    'wins': wins,
                    'win_rate': (wins / total * 100) if total > 0 else 0,
                    'avg_return': float(row['avg_return']) if row['avg_return'] else 0
                }
            return result
        except Exception as e:
            self.logger.error(f"Failed to get win rate by hour: {e}")
            return {}

    async def get_win_rate_by_score(self, days: int = 30) -> Dict[str, Dict[str, float]]:
        """점수대별 승률 조회"""
        query = """
            SELECT
                CASE
                    WHEN final_score >= 80 THEN '80+'
                    WHEN final_score >= 70 THEN '70-79'
                    WHEN final_score >= 60 THEN '60-69'
                    WHEN final_score >= 50 THEN '50-59'
                    ELSE '<50'
                END as score_band,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE return_60m > 0) as wins,
                AVG(return_60m) as avg_return,
                AVG(mfe) as avg_mfe,
                AVG(mae) as avg_mae
            FROM aegis_signal_history
            WHERE trace_status = 'completed'
              AND created_at > NOW() - $1 * INTERVAL '1 day'
            GROUP BY score_band
            ORDER BY score_band DESC
        """

        try:
            rows = await db.fetch(query, days)
            result = {}
            for row in rows:
                band = row['score_band']
                total = row['total']
                wins = row['wins']
                result[band] = {
                    'total': total,
                    'wins': wins,
                    'win_rate': (wins / total * 100) if total > 0 else 0,
                    'avg_return': float(row['avg_return']) if row['avg_return'] else 0,
                    'avg_mfe': float(row['avg_mfe']) if row['avg_mfe'] else 0,
                    'avg_mae': float(row['avg_mae']) if row['avg_mae'] else 0
                }
            return result
        except Exception as e:
            self.logger.error(f"Failed to get win rate by score: {e}")
            return {}

    async def get_equity_curve(self, days: int = 30) -> List[Dict[str, Any]]:
        """누적 수익 곡선 데이터"""
        query = """
            SELECT
                DATE(created_at) as date,
                SUM(return_60m) as daily_return,
                COUNT(*) as signal_count
            FROM aegis_signal_history
            WHERE trace_status = 'completed'
              AND created_at > NOW() - $1 * INTERVAL '1 day'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """

        try:
            rows = await db.fetch(query, days)

            cumulative = 0
            result = []
            for row in rows:
                daily_return = float(row['daily_return']) if row['daily_return'] else 0
                cumulative += daily_return
                result.append({
                    'date': row['date'].isoformat(),
                    'daily_return': round(daily_return, 2),
                    'cumulative_return': round(cumulative, 2),
                    'signal_count': row['signal_count']
                })
            return result
        except Exception as e:
            self.logger.error(f"Failed to get equity curve: {e}")
            return []

    async def get_failure_analysis(self, days: int = 30) -> Dict[str, int]:
        """실패 원인 분석"""
        query = """
            SELECT
                failure_tag,
                COUNT(*) as count
            FROM aegis_signal_history
            WHERE trace_status = 'completed'
              AND return_60m < 0
              AND failure_tag IS NOT NULL
              AND created_at > NOW() - $1 * INTERVAL '1 day'
            GROUP BY failure_tag
            ORDER BY count DESC
        """

        try:
            rows = await db.fetch(query, days)
            return {row['failure_tag']: row['count'] for row in rows}
        except Exception as e:
            self.logger.error(f"Failed to get failure analysis: {e}")
            return {}

    async def get_worst_trades(self, limit: int = 3, days: int = 30) -> List[Dict[str, Any]]:
        """최악의 거래 목록"""
        query = """
            SELECT
                ticker, signal_type, final_score,
                signal_price, created_at,
                return_5m, return_10m, return_30m, return_60m,
                mfe, mae, failure_tag, market_context
            FROM aegis_signal_history
            WHERE trace_status = 'completed'
              AND return_60m < 0
              AND created_at > NOW() - $1 * INTERVAL '1 day'
            ORDER BY return_60m ASC
            LIMIT $2
        """

        try:
            rows = await db.fetch(query, days, limit)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get worst trades: {e}")
            return []


# Singleton instance
_tracer_instance: Optional[SignalTraceManager] = None


def get_signal_tracer() -> SignalTraceManager:
    """Get singleton SignalTraceManager instance"""
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = SignalTraceManager()
    return _tracer_instance
