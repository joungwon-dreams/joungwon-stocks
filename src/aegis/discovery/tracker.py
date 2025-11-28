#!/usr/bin/env python3
"""
RecommendationTracker - Phase 9.5
신규종목 추천 검증 시스템

기능:
- 추천 종목 DB 저장
- 2주간 일일 가격 추적
- 수익률 계산 및 성과 분석
"""
import asyncio
import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

import asyncpg
from pykrx import stock as pykrx

from .finder import DiscoveryResult


@dataclass
class TrackingRecord:
    """일일 추적 기록"""
    recommendation_id: int
    tracking_date: date
    day_number: int
    open_price: int
    high_price: int
    low_price: int
    close_price: int
    volume: int
    daily_return: float
    cumulative_return: float


@dataclass
class PerformanceSummary:
    """성과 요약"""
    total_recommendations: int
    completed: int
    active: int
    success_count: int  # 목표가 도달
    failure_count: int  # 손절가 도달
    avg_return: float
    win_rate: float
    best_return: float
    worst_return: float


class RecommendationTracker:
    """
    추천 종목 추적기
    - 추천 시 DB 저장
    - 매일 가격 추적
    - 성공/실패 판정
    - 2주 후 성과 집계
    """

    TRACKING_DAYS = 14  # 2주간 추적
    SUCCESS_THRESHOLD = 5.0  # +5% 도달 시 성공
    FAILURE_THRESHOLD = -3.0  # -3% 도달 시 실패

    def __init__(self, db_config: Dict[str, Any] = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'stock_investment_db',
            'user': 'wonny'
        }
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """DB 연결"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(**self.db_config, min_size=1, max_size=5)

    async def disconnect(self):
        """DB 연결 해제"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def save_recommendations(self, results: List[DiscoveryResult]) -> List[int]:
        """
        추천 종목 DB 저장

        Args:
            results: OpportunityFinder의 추천 결과

        Returns:
            저장된 recommendation IDs
        """
        await self.connect()
        saved_ids = []

        for r in results:
            try:
                # 중복 체크 (같은 날 같은 종목)
                existing = await self.pool.fetchval("""
                    SELECT id FROM new_stock_recommendations
                    WHERE stock_code = $1 AND DATE(recommended_at) = CURRENT_DATE
                """, r.code)

                if existing:
                    print(f"   ⚠️ {r.name} 이미 추천됨 (ID: {existing})")
                    saved_ids.append(existing)
                    continue

                # 새 추천 저장
                rec_id = await self.pool.fetchval("""
                    INSERT INTO new_stock_recommendations (
                        recommended_at, stock_code, stock_name, market,
                        recommended_price, change_rate, aegis_score, scanner_score,
                        key_reasons, rsi_14, golden_cross,
                        foreigner_net, institution_net,
                        tracking_end_date
                    ) VALUES (
                        NOW(), $1, $2, $3,
                        $4, $5, $6, $7,
                        $8, $9, $10,
                        $11, $12,
                        CURRENT_DATE + INTERVAL '14 days'
                    ) RETURNING id
                """,
                    r.code, r.name, r.market,
                    r.current_price, r.change_rate, r.aegis_score, r.scanner_score,
                    json.dumps(r.key_reasons, ensure_ascii=False),
                    r.technical_score,  # RSI 대용
                    'golden' in ' '.join(r.key_reasons).lower() if r.key_reasons else False,
                    0, 0  # foreigner_net, institution_net (추후 업데이트)
                )
                saved_ids.append(rec_id)
                print(f"   ✅ {r.name} 저장됨 (ID: {rec_id})")

            except Exception as e:
                print(f"   ❌ {r.name} 저장 실패: {e}")

        return saved_ids

    async def track_daily_prices(self, target_date: str = None) -> int:
        """
        활성 추천 종목의 일일 가격 추적

        Args:
            target_date: 추적 날짜 (YYYYMMDD), None이면 오늘

        Returns:
            추적된 종목 수
        """
        await self.connect()

        if not target_date:
            target_date = datetime.now().strftime("%Y%m%d")

        tracking_date = datetime.strptime(target_date, "%Y%m%d").date()

        # 활성 추천 종목 조회
        active_recs = await self.pool.fetch("""
            SELECT id, stock_code, stock_name, recommended_price,
                   DATE(recommended_at) as rec_date
            FROM new_stock_recommendations
            WHERE tracking_status = 'active'
              AND tracking_end_date >= $1
        """, tracking_date)

        if not active_recs:
            print("   추적 대상 없음")
            return 0

        print(f"📊 {len(active_recs)}개 종목 추적 중...")
        tracked = 0

        for rec in active_recs:
            try:
                # D+몇일인지 계산
                day_number = (tracking_date - rec['rec_date']).days

                if day_number < 1:
                    continue  # 추천 당일은 스킵

                # pykrx로 가격 조회
                df = pykrx.get_market_ohlcv(target_date, target_date, rec['stock_code'])
                if df.empty:
                    continue

                row = df.iloc[0]
                close_price = int(row['종가'])
                recommended_price = rec['recommended_price']

                # 수익률 계산
                cumulative_return = ((close_price - recommended_price) / recommended_price) * 100

                # 전일 종가 조회 (일일 수익률용)
                prev_close = await self.pool.fetchval("""
                    SELECT close_price FROM new_stock_tracking
                    WHERE recommendation_id = $1
                    ORDER BY tracking_date DESC LIMIT 1
                """, rec['id'])

                if prev_close:
                    daily_return = ((close_price - prev_close) / prev_close) * 100
                else:
                    daily_return = cumulative_return  # 첫날은 추천가 대비

                # DB 저장
                await self.pool.execute("""
                    INSERT INTO new_stock_tracking (
                        recommendation_id, tracking_date, day_number,
                        open_price, high_price, low_price, close_price, volume,
                        daily_return, cumulative_return
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (recommendation_id, tracking_date) DO UPDATE
                    SET close_price = $7, cumulative_return = $10
                """,
                    rec['id'], tracking_date, day_number,
                    int(row['시가']), int(row['고가']), int(row['저가']),
                    close_price, int(row['거래량']),
                    round(daily_return, 2), round(cumulative_return, 2)
                )

                tracked += 1

                # Phase 9.5: 성공/실패 판정 (목표가 또는 손절가 도달)
                if cumulative_return >= self.SUCCESS_THRESHOLD:
                    await self._complete_tracking(rec['id'], status='success')
                    print(f"   🎯 {rec['stock_name']} 목표 달성! +{cumulative_return:.1f}%")
                elif cumulative_return <= self.FAILURE_THRESHOLD:
                    await self._complete_tracking(rec['id'], status='failure')
                    print(f"   ⛔ {rec['stock_name']} 손절 도달: {cumulative_return:.1f}%")
                # 2주 완료 체크
                elif day_number >= self.TRACKING_DAYS:
                    await self._complete_tracking(rec['id'], status='completed')

            except Exception as e:
                print(f"   ⚠️ {rec['stock_name']} 추적 실패: {e}")

        print(f"   ✅ {tracked}개 종목 추적 완료")
        return tracked

    async def _complete_tracking(self, rec_id: int, status: str = 'completed'):
        """추적 완료 처리 (status: success, failure, completed)"""
        # 최종 성과 계산
        stats = await self.pool.fetchrow("""
            SELECT
                MAX(cumulative_return) as max_return,
                MIN(cumulative_return) as min_return,
                (SELECT close_price FROM new_stock_tracking
                 WHERE recommendation_id = $1 ORDER BY day_number DESC LIMIT 1) as final_price,
                (SELECT cumulative_return FROM new_stock_tracking
                 WHERE recommendation_id = $1 ORDER BY day_number DESC LIMIT 1) as final_return,
                (SELECT day_number FROM new_stock_tracking
                 WHERE recommendation_id = $1 ORDER BY cumulative_return DESC LIMIT 1) as best_day,
                (SELECT day_number FROM new_stock_tracking
                 WHERE recommendation_id = $1 ORDER BY cumulative_return ASC LIMIT 1) as worst_day
            FROM new_stock_tracking
            WHERE recommendation_id = $1
        """, rec_id)

        # 추천 테이블 업데이트
        await self.pool.execute("""
            UPDATE new_stock_recommendations
            SET tracking_status = $2,
                final_price = $3,
                final_return = $4,
                max_return = $5,
                min_return = $6,
                best_day = $7,
                worst_day = $8
            WHERE id = $1
        """, rec_id, status, stats['final_price'], stats['final_return'],
            stats['max_return'], stats['min_return'],
            stats['best_day'], stats['worst_day'])

        status_emoji = "🎯" if status == 'success' else "⛔" if status == 'failure' else "📈"
        print(f"   {status_emoji} 추천 #{rec_id} 추적 완료 ({status}): {stats['final_return']:.1f}%")

    async def get_performance_summary(self, days: int = 14) -> PerformanceSummary:
        """
        최근 N일간 성과 요약

        Args:
            days: 조회 기간 (일)

        Returns:
            PerformanceSummary
        """
        await self.connect()

        stats = await self.pool.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN tracking_status != 'active' THEN 1 END) as completed,
                COUNT(CASE WHEN tracking_status = 'active' THEN 1 END) as active,
                COUNT(CASE WHEN tracking_status = 'success' THEN 1 END) as success,
                COUNT(CASE WHEN tracking_status = 'failure' THEN 1 END) as failure,
                AVG(final_return) FILTER (WHERE tracking_status != 'active') as avg_return,
                COUNT(CASE WHEN final_return > 0 THEN 1 END) as wins,
                MAX(max_return) as best,
                MIN(min_return) as worst
            FROM new_stock_recommendations
            WHERE recommended_at >= NOW() - INTERVAL '%s days'
        """ % days)

        total_completed = stats['completed'] or 0
        wins = stats['wins'] or 0
        win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

        return PerformanceSummary(
            total_recommendations=stats['total'] or 0,
            completed=total_completed,
            active=stats['active'] or 0,
            success_count=stats['success'] or 0,
            failure_count=stats['failure'] or 0,
            avg_return=round(stats['avg_return'] or 0, 2),
            win_rate=round(win_rate, 1),
            best_return=round(stats['best'] or 0, 2),
            worst_return=round(stats['worst'] or 0, 2)
        )

    async def get_active_recommendations(self) -> List[Dict]:
        """활성 추천 목록 조회"""
        await self.connect()

        rows = await self.pool.fetch("""
            SELECT
                r.id, r.stock_code, r.stock_name, r.market,
                r.recommended_price, r.aegis_score, r.key_reasons,
                DATE(r.recommended_at) as rec_date,
                t.close_price as current_price,
                t.cumulative_return,
                t.day_number
            FROM new_stock_recommendations r
            LEFT JOIN LATERAL (
                SELECT close_price, cumulative_return, day_number
                FROM new_stock_tracking
                WHERE recommendation_id = r.id
                ORDER BY tracking_date DESC LIMIT 1
            ) t ON true
            WHERE r.tracking_status = 'active'
            ORDER BY r.recommended_at DESC
        """)

        return [dict(row) for row in rows]

    async def get_completed_recommendations(self, limit: int = 20) -> List[Dict]:
        """완료된 추천 목록 조회"""
        await self.connect()

        rows = await self.pool.fetch("""
            SELECT
                id, stock_code, stock_name, market,
                recommended_price, final_price,
                final_return, max_return, min_return,
                best_day, worst_day,
                DATE(recommended_at) as rec_date
            FROM new_stock_recommendations
            WHERE tracking_status = 'completed'
            ORDER BY recommended_at DESC
            LIMIT $1
        """, limit)

        return [dict(row) for row in rows]


# Singleton
_tracker_instance: Optional[RecommendationTracker] = None


def get_recommendation_tracker() -> RecommendationTracker:
    """RecommendationTracker 싱글톤"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = RecommendationTracker()
    return _tracker_instance


# CLI 테스트
if __name__ == "__main__":
    async def main():
        tracker = RecommendationTracker()
        await tracker.connect()

        # 성과 요약
        summary = await tracker.get_performance_summary()
        print(f"총 추천: {summary.total_recommendations}")
        print(f"완료: {summary.completed}, 활성: {summary.active}")
        print(f"평균 수익률: {summary.avg_return}%, 승률: {summary.win_rate}%")

        await tracker.disconnect()

    asyncio.run(main())
