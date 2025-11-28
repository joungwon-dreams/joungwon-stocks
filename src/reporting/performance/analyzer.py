"""
DailyPerformanceAnalyzer - Phase 8
일일 매매 성과 분석기

핵심 기능:
- trade_history에서 당일 거래 내역 분석
- stock_assets에서 현재 자산 평가
- 실현/미실현 손익 계산
- 승률 및 AEGIS 신호 적중률 계산
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
import logging

from src.config.database import db


@dataclass
class TradeRecord:
    """개별 거래 기록"""
    trade_id: int
    stock_code: str
    stock_name: str
    trade_type: str  # BUY / SELL
    quantity: int
    price: float
    amount: float
    trade_time: datetime
    realized_pnl: Optional[float] = None


@dataclass
class StockPerformance:
    """종목별 성과"""
    stock_code: str
    stock_name: str
    quantity: int
    avg_buy_price: float
    current_price: float
    total_cost: float
    total_value: float
    unrealized_pnl: float
    unrealized_pnl_rate: float
    aegis_signal: Optional[str] = None
    aegis_score: Optional[int] = None


@dataclass
class DailySummary:
    """일일 성과 요약"""
    date: date

    # 자산 현황
    total_asset: float = 0.0
    cash_balance: float = 0.0
    stock_value: float = 0.0

    # 손익
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_rate: float = 0.0

    # 누적
    cumulative_realized_pnl: float = 0.0
    cumulative_pnl_rate: float = 0.0

    # 매매 통계
    trade_count: int = 0
    buy_count: int = 0
    sell_count: int = 0
    buy_amount: float = 0.0
    sell_amount: float = 0.0

    # 승률
    win_trades: int = 0
    lose_trades: int = 0
    win_rate: float = 0.0

    # AEGIS
    aegis_signal_count: int = 0
    aegis_accuracy: float = 0.0

    # 시장
    kospi_close: Optional[float] = None
    kospi_change_rate: Optional[float] = None
    kosdaq_close: Optional[float] = None
    kosdaq_change_rate: Optional[float] = None

    # 상세
    trades: List[TradeRecord] = field(default_factory=list)
    holdings: List[StockPerformance] = field(default_factory=list)


class DailyPerformanceAnalyzer:
    """
    일일 매매 성과 분석기

    Phase 8 Spec:
    - 당일 거래 내역 분석
    - 실현/미실현 손익 계산
    - 승률 및 AEGIS 적중률 분석
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze(self, target_date: Optional[date] = None) -> DailySummary:
        """
        특정 날짜의 성과 분석

        Args:
            target_date: 분석 대상 날짜 (기본: 오늘)

        Returns:
            DailySummary: 일일 성과 요약
        """
        if target_date is None:
            target_date = date.today()

        self.logger.info(f"Analyzing performance for {target_date}")

        summary = DailySummary(date=target_date)

        # 1. 보유종목 현황 (미실현 손익)
        holdings = await self._get_holdings()
        summary.holdings = holdings
        summary.stock_value = sum(h.total_value for h in holdings)
        summary.unrealized_pnl = sum(h.unrealized_pnl for h in holdings)

        # 2. 당일 거래 내역 (실현 손익)
        trades = await self._get_daily_trades(target_date)
        summary.trades = trades
        summary.trade_count = len(trades)
        summary.buy_count = sum(1 for t in trades if t.trade_type == 'BUY')
        summary.sell_count = sum(1 for t in trades if t.trade_type == 'SELL')
        summary.buy_amount = sum(t.amount for t in trades if t.trade_type == 'BUY')
        summary.sell_amount = sum(t.amount for t in trades if t.trade_type == 'SELL')

        # 실현 손익 계산 (매도 거래에서)
        realized_pnl = sum(t.realized_pnl or 0 for t in trades if t.trade_type == 'SELL')
        summary.realized_pnl = realized_pnl

        # 3. 승률 계산
        win_lose = await self._calculate_win_rate(target_date)
        summary.win_trades = win_lose['win']
        summary.lose_trades = win_lose['lose']
        summary.win_rate = win_lose['rate']

        # 4. 총 자산 계산
        cash = await self._get_cash_balance()
        summary.cash_balance = cash
        summary.total_asset = cash + summary.stock_value

        # 5. 일일 손익 계산 (전일 대비)
        prev_summary = await self._get_previous_summary(target_date)
        if prev_summary:
            summary.daily_pnl = summary.total_asset - prev_summary.get('total_asset', 0)
            if prev_summary.get('total_asset', 0) > 0:
                summary.daily_pnl_rate = (summary.daily_pnl / prev_summary['total_asset']) * 100

        # 6. 누적 손익
        cumulative = await self._get_cumulative_pnl()
        summary.cumulative_realized_pnl = cumulative['realized']
        summary.cumulative_pnl_rate = cumulative['rate']

        # 7. AEGIS 신호 성과
        aegis_stats = await self._get_aegis_performance(target_date)
        summary.aegis_signal_count = aegis_stats['count']
        summary.aegis_accuracy = aegis_stats['accuracy']

        # 8. 시장 지표
        market = await self._get_market_indices(target_date)
        summary.kospi_close = market.get('kospi_close')
        summary.kospi_change_rate = market.get('kospi_change')
        summary.kosdaq_close = market.get('kosdaq_close')
        summary.kosdaq_change_rate = market.get('kosdaq_change')

        return summary

    async def _get_holdings(self) -> List[StockPerformance]:
        """보유종목 현황 조회"""
        query = """
            SELECT
                sa.stock_code,
                sa.stock_name,
                sa.quantity,
                sa.avg_buy_price,
                sa.current_price,
                sa.total_cost,
                sa.total_value,
                sa.profit_loss,
                sa.profit_loss_rate,
                ash.signal_type,
                ash.signal_score
            FROM stock_assets sa
            LEFT JOIN LATERAL (
                SELECT signal_type, signal_score
                FROM aegis_signal_history
                WHERE stock_code = sa.stock_code
                ORDER BY recorded_at DESC
                LIMIT 1
            ) ash ON true
            WHERE sa.quantity > 0
            ORDER BY sa.total_value DESC
        """

        holdings = []
        try:
            rows = await db.fetch(query)
            for row in rows:
                holdings.append(StockPerformance(
                    stock_code=row['stock_code'],
                    stock_name=row['stock_name'],
                    quantity=row['quantity'],
                    avg_buy_price=float(row['avg_buy_price'] or 0),
                    current_price=float(row['current_price'] or 0),
                    total_cost=float(row['total_cost'] or 0),
                    total_value=float(row['total_value'] or 0),
                    unrealized_pnl=float(row['profit_loss'] or 0),
                    unrealized_pnl_rate=float(row['profit_loss_rate'] or 0),
                    aegis_signal=row['signal_type'],
                    aegis_score=row['signal_score'],
                ))
        except Exception as e:
            self.logger.error(f"Failed to get holdings: {e}")

        return holdings

    async def _get_daily_trades(self, target_date: date) -> List[TradeRecord]:
        """당일 거래 내역 조회"""
        query = """
            SELECT
                id,
                stock_code,
                stock_name,
                trade_type,
                quantity,
                price,
                total_amount,
                trade_date
            FROM trade_history
            WHERE DATE(trade_date) = $1
            ORDER BY trade_date DESC
        """

        trades = []
        try:
            rows = await db.fetch(query, target_date)
            for row in rows:
                trades.append(TradeRecord(
                    trade_id=row['id'],
                    stock_code=row['stock_code'],
                    stock_name=row['stock_name'] or '',
                    trade_type=row['trade_type'],
                    quantity=row['quantity'],
                    price=float(row['price'] or 0),
                    amount=float(row['total_amount'] or 0),
                    trade_time=row['trade_date'],
                    realized_pnl=None,  # 별도 계산 필요
                ))
        except Exception as e:
            self.logger.error(f"Failed to get daily trades: {e}")

        return trades

    async def _calculate_win_rate(self, target_date: date) -> Dict[str, Any]:
        """승률 계산 (매도 거래 기준) - 평단가 대비 매도가 비교"""
        # 실현 손익 계산: 매도가 > 평단가면 이익
        query = """
            SELECT
                th.stock_code,
                th.price as sell_price,
                sa.avg_buy_price
            FROM trade_history th
            LEFT JOIN stock_assets sa ON th.stock_code = sa.stock_code
            WHERE DATE(th.trade_date) = $1
              AND th.trade_type = 'SELL'
        """

        try:
            rows = await db.fetch(query, target_date)
            win = 0
            lose = 0

            for row in rows:
                sell_price = float(row['sell_price'] or 0)
                avg_price = float(row['avg_buy_price'] or 0)
                if avg_price > 0:
                    if sell_price > avg_price:
                        win += 1
                    elif sell_price < avg_price:
                        lose += 1

            total = win + lose
            rate = (win / total * 100) if total > 0 else 0.0

            return {'win': win, 'lose': lose, 'rate': round(rate, 1)}
        except Exception as e:
            self.logger.error(f"Failed to calculate win rate: {e}")
            return {'win': 0, 'lose': 0, 'rate': 0.0}

    async def _get_cash_balance(self) -> float:
        """현금 잔고 조회 (설정 테이블에서)"""
        # TODO: 실제 증권사 API 연동 시 대체
        # 현재는 고정값 또는 설정 테이블에서 조회
        query = """
            SELECT value::numeric as cash
            FROM settings
            WHERE key = 'cash_balance'
        """
        try:
            row = await db.fetchrow(query)
            if row:
                return float(row['cash'])
        except:
            pass

        return 0.0  # 기본값

    async def _get_previous_summary(self, target_date: date) -> Optional[Dict[str, Any]]:
        """전일 요약 조회"""
        prev_date = target_date - timedelta(days=1)

        query = """
            SELECT total_asset, realized_pnl, unrealized_pnl
            FROM daily_summary
            WHERE date = $1
        """

        try:
            row = await db.fetchrow(query, prev_date)
            if row:
                return {
                    'total_asset': float(row['total_asset'] or 0),
                    'realized_pnl': float(row['realized_pnl'] or 0),
                    'unrealized_pnl': float(row['unrealized_pnl'] or 0),
                }
        except Exception as e:
            self.logger.debug(f"No previous summary found: {e}")

        return None

    async def _get_cumulative_pnl(self) -> Dict[str, float]:
        """누적 실현 손익 계산 (매도 금액 - 추정 매수 비용)"""
        # 간단한 누적 손익: 현재 미실현 손익의 합
        query = """
            SELECT
                COALESCE(SUM(profit_loss), 0) as total_unrealized
            FROM stock_assets
            WHERE quantity > 0
        """

        try:
            row = await db.fetchrow(query)
            realized = float(row['total_unrealized'] or 0)

            # 초기 투자금 대비 수익률 계산 (TODO: 실제 초기 투자금 설정 필요)
            initial_investment = 10000000  # 가정: 1000만원
            rate = (realized / initial_investment * 100) if initial_investment > 0 else 0

            return {'realized': realized, 'rate': round(rate, 2)}
        except Exception as e:
            self.logger.error(f"Failed to get cumulative PnL: {e}")
            return {'realized': 0.0, 'rate': 0.0}

    async def _get_aegis_performance(self, target_date: date) -> Dict[str, Any]:
        """AEGIS 신호 성과 분석"""
        query = """
            SELECT
                COUNT(*) as signal_count,
                COUNT(*) FILTER (WHERE is_success = true) as success_count
            FROM aegis_signal_history
            WHERE DATE(recorded_at) = $1
              AND verified_at IS NOT NULL
        """

        try:
            row = await db.fetchrow(query, target_date)
            count = row['signal_count'] or 0
            success = row['success_count'] or 0

            accuracy = (success / count * 100) if count > 0 else 0.0

            return {'count': count, 'accuracy': round(accuracy, 1)}
        except Exception as e:
            self.logger.error(f"Failed to get AEGIS performance: {e}")
            return {'count': 0, 'accuracy': 0.0}

    async def _get_market_indices(self, target_date: date) -> Dict[str, Any]:
        """시장 지표 조회"""
        # pykrx 또는 캐시된 데이터에서 조회
        try:
            from pykrx import stock as pykrx_stock
            date_str = target_date.strftime('%Y%m%d')

            kospi = pykrx_stock.get_index_ohlcv_by_date(date_str, date_str, "1001")
            kosdaq = pykrx_stock.get_index_ohlcv_by_date(date_str, date_str, "2001")

            result = {}
            if not kospi.empty:
                result['kospi_close'] = float(kospi['종가'].iloc[-1])
                result['kospi_change'] = float(kospi['등락률'].iloc[-1])
            if not kosdaq.empty:
                result['kosdaq_close'] = float(kosdaq['종가'].iloc[-1])
                result['kosdaq_change'] = float(kosdaq['등락률'].iloc[-1])

            return result
        except Exception as e:
            self.logger.warning(f"Failed to get market indices: {e}")
            return {}

    async def save_summary(self, summary: DailySummary) -> bool:
        """일일 요약을 DB에 저장"""
        query = """
            INSERT INTO daily_summary (
                date, total_asset, cash_balance, stock_value,
                realized_pnl, unrealized_pnl, daily_pnl, daily_pnl_rate,
                cumulative_realized_pnl, cumulative_pnl_rate,
                trade_count, buy_count, sell_count, buy_amount, sell_amount,
                win_trades, lose_trades, win_rate,
                aegis_signal_count, aegis_accuracy,
                kospi_close, kospi_change_rate, kosdaq_close, kosdaq_change_rate
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, $23, $24
            )
            ON CONFLICT (date) DO UPDATE SET
                total_asset = EXCLUDED.total_asset,
                cash_balance = EXCLUDED.cash_balance,
                stock_value = EXCLUDED.stock_value,
                realized_pnl = EXCLUDED.realized_pnl,
                unrealized_pnl = EXCLUDED.unrealized_pnl,
                daily_pnl = EXCLUDED.daily_pnl,
                daily_pnl_rate = EXCLUDED.daily_pnl_rate,
                cumulative_realized_pnl = EXCLUDED.cumulative_realized_pnl,
                cumulative_pnl_rate = EXCLUDED.cumulative_pnl_rate,
                trade_count = EXCLUDED.trade_count,
                buy_count = EXCLUDED.buy_count,
                sell_count = EXCLUDED.sell_count,
                buy_amount = EXCLUDED.buy_amount,
                sell_amount = EXCLUDED.sell_amount,
                win_trades = EXCLUDED.win_trades,
                lose_trades = EXCLUDED.lose_trades,
                win_rate = EXCLUDED.win_rate,
                aegis_signal_count = EXCLUDED.aegis_signal_count,
                aegis_accuracy = EXCLUDED.aegis_accuracy,
                kospi_close = EXCLUDED.kospi_close,
                kospi_change_rate = EXCLUDED.kospi_change_rate,
                kosdaq_close = EXCLUDED.kosdaq_close,
                kosdaq_change_rate = EXCLUDED.kosdaq_change_rate,
                updated_at = CURRENT_TIMESTAMP
        """

        try:
            await db.execute(
                query,
                summary.date,
                summary.total_asset, summary.cash_balance, summary.stock_value,
                summary.realized_pnl, summary.unrealized_pnl,
                summary.daily_pnl, summary.daily_pnl_rate,
                summary.cumulative_realized_pnl, summary.cumulative_pnl_rate,
                summary.trade_count, summary.buy_count, summary.sell_count,
                summary.buy_amount, summary.sell_amount,
                summary.win_trades, summary.lose_trades, summary.win_rate,
                summary.aegis_signal_count, summary.aegis_accuracy,
                summary.kospi_close, summary.kospi_change_rate,
                summary.kosdaq_close, summary.kosdaq_change_rate
            )
            self.logger.info(f"Saved daily summary for {summary.date}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save summary: {e}")
            return False

    async def get_weekly_summary(self, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """주간 성과 요약 조회"""
        if end_date is None:
            end_date = date.today()
        start_date = end_date - timedelta(days=6)

        query = """
            SELECT
                date,
                total_asset,
                daily_pnl,
                daily_pnl_rate,
                realized_pnl,
                trade_count,
                win_rate
            FROM daily_summary
            WHERE date BETWEEN $1 AND $2
            ORDER BY date ASC
        """

        try:
            rows = await db.fetch(query, start_date, end_date)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get weekly summary: {e}")
            return []

    async def get_monthly_calendar(self, year: int, month: int) -> List[Dict[str, Any]]:
        """월간 캘린더 데이터 조회"""
        query = """
            SELECT
                date,
                daily_pnl,
                daily_pnl_rate,
                trade_count
            FROM daily_summary
            WHERE EXTRACT(YEAR FROM date) = $1
              AND EXTRACT(MONTH FROM date) = $2
            ORDER BY date ASC
        """

        try:
            rows = await db.fetch(query, year, month)
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Failed to get monthly calendar: {e}")
            return []


# Singleton instance
_analyzer_instance: Optional[DailyPerformanceAnalyzer] = None


def get_performance_analyzer() -> DailyPerformanceAnalyzer:
    """Get singleton DailyPerformanceAnalyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = DailyPerformanceAnalyzer()
    return _analyzer_instance
