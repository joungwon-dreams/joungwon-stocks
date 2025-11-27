"""
Phase 4: 수익률 추적기 (Profit Tracker)

추천 후 N일 경과한 종목의 실제 수익률을 추적하고 기록합니다.
- 1주(7일), 2주(14일), 1개월(30일) 시점의 수익률 측정
- 최대 수익률 (Max Profit), 최대 손실률 (Max Drawdown) 계산
- 성과 데이터를 smart_performance 테이블에 저장
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

import sys
sys.path.insert(0, '.')
from 신규종목추천.config.settings import settings
from 신규종목추천.src.utils.database import db

logger = logging.getLogger(__name__)


class ProfitTracker:
    """
    추천 종목 수익률 추적기

    추천일로부터 일정 기간이 지난 종목들의 실제 수익률을 계산하고 저장합니다.
    """

    # 추적 기간 (일)
    TRACKING_PERIODS = [7, 14, 30]  # 1주, 2주, 1개월

    def __init__(self):
        self.today = date.today()

    async def track_all(self) -> Dict[str, Any]:
        """
        모든 추적 기간에 대해 수익률 추적 실행

        Returns:
            추적 결과 요약
        """
        logger.info("=== Phase 4: 수익률 추적 시작 ===")
        start_time = datetime.now()

        results = {
            'total_tracked': 0,
            'by_period': {},
            'top_performers': [],
            'worst_performers': [],
        }

        for days in self.TRACKING_PERIODS:
            period_result = await self.track_period(days)
            results['by_period'][f'{days}d'] = period_result
            results['total_tracked'] += period_result.get('tracked_count', 0)

        # 전체 성과 요약
        summary = await self._get_performance_summary()
        results['summary'] = summary

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== Phase 4 완료: {results['total_tracked']}건 추적 ({elapsed:.1f}초) ===")

        return results

    async def track_period(self, days: int) -> Dict[str, Any]:
        """
        특정 기간(N일 전 추천) 종목들의 수익률 추적

        Args:
            days: 추천일로부터 경과 일수

        Returns:
            해당 기간 추적 결과
        """
        target_date = self.today - timedelta(days=days)
        logger.info(f"[{days}일] {target_date} 추천 종목 수익률 추적 중...")

        # 해당일 추천 종목 조회 (아직 추적되지 않은 것만)
        query = """
        SELECT
            sr.id as recommendation_id,
            sr.stock_code,
            sr.stock_name,
            sr.recommendation_date,
            sr.close_price as rec_price,
            sr.ai_grade,
            sr.final_score
        FROM smart_recommendations sr
        LEFT JOIN smart_performance sp
            ON sr.id = sp.recommendation_id
            AND sp.days_held = $2
        WHERE sr.recommendation_date = $1
          AND sp.id IS NULL  -- 아직 해당 기간 추적 안된 것
        """

        recommendations = await db.fetch(query, target_date, days)

        if not recommendations:
            logger.info(f"[{days}일] 추적 대상 없음")
            return {'tracked_count': 0, 'date': str(target_date)}

        logger.info(f"[{days}일] {len(recommendations)}개 종목 추적 대상")

        tracked_count = 0
        for rec in recommendations:
            try:
                result = await self._track_single_stock(rec, days)
                if result:
                    tracked_count += 1
            except Exception as e:
                logger.error(f"[{days}일] {rec['stock_code']} 추적 실패: {e}")

        logger.info(f"[{days}일] {tracked_count}개 종목 추적 완료")

        return {
            'tracked_count': tracked_count,
            'date': str(target_date),
            'total_recommendations': len(recommendations)
        }

    async def _track_single_stock(self, rec: Dict, days_held: int) -> Optional[Dict]:
        """
        단일 종목 수익률 계산 및 저장

        Args:
            rec: 추천 정보
            days_held: 보유 기간 (일)

        Returns:
            성과 데이터 또는 None
        """
        stock_code = rec['stock_code']
        rec_date = rec['recommendation_date']
        rec_price = rec['rec_price']

        if not rec_price or rec_price <= 0:
            logger.warning(f"{stock_code}: 추천가 없음, 스킵")
            return None

        # 현재가 조회 (가장 최근 OHLCV)
        current_price_query = """
        SELECT close, date
        FROM daily_ohlcv
        WHERE stock_code = $1 AND date <= $2
        ORDER BY date DESC
        LIMIT 1
        """

        check_date = rec_date + timedelta(days=days_held)
        current_data = await db.fetchrow(current_price_query, stock_code, check_date)

        if not current_data:
            logger.warning(f"{stock_code}: {check_date} 가격 데이터 없음")
            return None

        check_price = current_data['close']
        actual_check_date = current_data['date']

        # 수익률 계산
        return_rate = ((check_price - rec_price) / rec_price) * 100

        # 기간 내 최고가/최저가 조회
        range_query = """
        SELECT MAX(high) as max_high, MIN(low) as min_low
        FROM daily_ohlcv
        WHERE stock_code = $1
          AND date > $2
          AND date <= $3
        """

        range_data = await db.fetchrow(range_query, stock_code, rec_date, check_date)

        max_profit = None
        max_drawdown = None

        if range_data and range_data['max_high']:
            max_profit = ((range_data['max_high'] - rec_price) / rec_price) * 100
        if range_data and range_data['min_low']:
            max_drawdown = ((range_data['min_low'] - rec_price) / rec_price) * 100

        # 상태 결정
        if return_rate >= 10:
            status = 'success'  # 10% 이상 수익
        elif return_rate >= 0:
            status = 'active'   # 소폭 수익 또는 보합
        elif return_rate >= -5:
            status = 'warning'  # 소폭 손실
        else:
            status = 'failed'   # 5% 이상 손실

        # DB 저장
        insert_query = """
        INSERT INTO smart_performance
            (recommendation_id, stock_code, rec_date, rec_price, rec_grade, rec_score,
             check_date, check_price, return_rate, max_profit, max_drawdown,
             status, days_held)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        RETURNING id
        """

        result = await db.fetchrow(
            insert_query,
            rec['recommendation_id'],
            stock_code,
            rec_date,
            rec_price,
            rec.get('ai_grade'),
            rec.get('final_score'),
            actual_check_date,
            check_price,
            round(return_rate, 2),
            round(max_profit, 2) if max_profit else None,
            round(max_drawdown, 2) if max_drawdown else None,
            status,
            days_held
        )

        logger.debug(f"{stock_code}: {return_rate:+.2f}% ({status})")

        return {
            'stock_code': stock_code,
            'return_rate': return_rate,
            'max_profit': max_profit,
            'max_drawdown': max_drawdown,
            'status': status
        }

    async def _get_performance_summary(self) -> Dict[str, Any]:
        """전체 성과 요약 통계"""

        query = """
        SELECT
            days_held,
            COUNT(*) as count,
            AVG(return_rate) as avg_return,
            MAX(return_rate) as max_return,
            MIN(return_rate) as min_return,
            COUNT(CASE WHEN return_rate > 0 THEN 1 END) as win_count,
            COUNT(CASE WHEN return_rate < 0 THEN 1 END) as loss_count,
            AVG(max_profit) as avg_max_profit,
            AVG(max_drawdown) as avg_max_drawdown
        FROM smart_performance
        GROUP BY days_held
        ORDER BY days_held
        """

        stats = await db.fetch(query)

        summary = {}
        for stat in stats:
            days = stat['days_held']
            total = stat['count']
            wins = stat['win_count'] or 0
            win_rate = (wins / total * 100) if total > 0 else 0

            summary[f'{days}d'] = {
                'total': total,
                'avg_return': float(stat['avg_return'] or 0),
                'max_return': float(stat['max_return'] or 0),
                'min_return': float(stat['min_return'] or 0),
                'win_rate': win_rate,
                'avg_max_profit': float(stat['avg_max_profit'] or 0),
                'avg_max_drawdown': float(stat['avg_max_drawdown'] or 0),
            }

        return summary

    async def get_failed_recommendations(self,
                                         threshold: float = -5.0,
                                         limit: int = 20) -> List[Dict]:
        """
        실패한 추천 종목 조회 (AI 회고 대상)

        Args:
            threshold: 손실률 기준 (기본 -5%)
            limit: 조회 개수

        Returns:
            실패 종목 리스트
        """
        query = """
        SELECT
            sp.id as performance_id,
            sp.recommendation_id,
            sp.stock_code,
            sr.stock_name,
            sp.rec_date,
            sp.rec_price,
            sp.check_date,
            sp.check_price,
            sp.return_rate,
            sp.max_drawdown,
            sp.days_held,
            sr.ai_grade,
            sr.ai_key_material,
            sr.ai_risk_factor,
            sr.ai_raw_response
        FROM smart_performance sp
        JOIN smart_recommendations sr ON sp.recommendation_id = sr.id
        WHERE sp.return_rate <= $1
          AND sp.status = 'failed'
        ORDER BY sp.return_rate ASC
        LIMIT $2
        """

        return await db.fetch(query, threshold, limit)

    async def generate_report(self) -> str:
        """성과 리포트 생성"""

        summary = await self._get_performance_summary()

        # 등급별 성과
        grade_query = """
        SELECT
            sr.ai_grade,
            COUNT(*) as count,
            AVG(sp.return_rate) as avg_return,
            COUNT(CASE WHEN sp.return_rate > 0 THEN 1 END) as wins
        FROM smart_performance sp
        JOIN smart_recommendations sr ON sp.recommendation_id = sr.id
        WHERE sp.days_held = 7
        GROUP BY sr.ai_grade
        ORDER BY sr.ai_grade
        """

        grade_stats = await db.fetch(grade_query)

        # 리포트 생성
        report = "# 신규종목추천 성과 리포트\n\n"
        report += f"**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

        report += "## 📊 기간별 성과\n\n"
        report += "| 기간 | 종목수 | 평균수익률 | 승률 | 최대이익 | 최대손실 |\n"
        report += "|:---:|:---:|:---:|:---:|:---:|:---:|\n"

        for period, stats in summary.items():
            report += f"| {period} | {stats['total']} | "
            report += f"{stats['avg_return']:+.2f}% | "
            report += f"{stats['win_rate']:.1f}% | "
            report += f"{stats['avg_max_profit']:+.2f}% | "
            report += f"{stats['avg_max_drawdown']:+.2f}% |\n"

        report += "\n## 🏷️ AI 등급별 성과 (7일 기준)\n\n"
        report += "| 등급 | 종목수 | 평균수익률 | 승률 |\n"
        report += "|:---:|:---:|:---:|:---:|\n"

        for stat in grade_stats:
            grade = stat['ai_grade'] or 'N/A'
            count = stat['count']
            avg_ret = float(stat['avg_return'] or 0)
            wins = stat['wins'] or 0
            win_rate = (wins / count * 100) if count > 0 else 0
            report += f"| {grade} | {count} | {avg_ret:+.2f}% | {win_rate:.1f}% |\n"

        return report


async def main():
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    await db.connect()

    try:
        tracker = ProfitTracker()
        results = await tracker.track_all()

        print("\n=== 수익률 추적 결과 ===")
        print(f"총 추적: {results['total_tracked']}건")

        if results.get('summary'):
            print("\n📊 기간별 요약:")
            for period, stats in results['summary'].items():
                print(f"  {period}: {stats['total']}건, "
                      f"평균 {stats['avg_return']:+.2f}%, "
                      f"승률 {stats['win_rate']:.1f}%")

        # 리포트 생성
        report = await tracker.generate_report()
        print("\n" + report)

    finally:
        await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
